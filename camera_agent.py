import io
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import requests
from PIL import Image

DIGICAM_BASE = "http://localhost:5513"

# Déclenchement reflex : le shutter + le transfert du fichier pleine résolution
# depuis la caméra vers le dossier de session peuvent prendre plusieurs secondes.
CAPTURE_TRIGGER_TIMEOUT = 20  # s, requête ?slc=capture
CAPTURE_WAIT_TIMEOUT = 25     # s, attente que lastcaptured change de valeur
FILE_READ_TIMEOUT = 5         # s, attente que le fichier soit entièrement écrit sur disque
POLL_INTERVAL = 0.1           # s, granularité du poll lastcaptured (localhost, sans risque)
MAX_OUTPUT_LONG_EDGE = 2600   # px, définition max de la photo finale
#                               24MP (6000px) est inutile pour une impression 10x15
#                               (~1800px @ 300dpi) et ralentit compose/encodage côté UI ;
#                               2600px reste >400dpi. Voir _downscale().


class CameraAgent:
    """Pilote le Canon EOS via l'API HTTP de digiCamControl."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.aspect_ratio = (16, 9)  # ratio de cadrage du live view et des photos
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_connection()
        self._configure_capture_output()
        self._start_live_view()

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def _check_connection(self):
        try:
            r = requests.get(f"{DIGICAM_BASE}/", timeout=3)
            r.raise_for_status()
        except Exception:
            raise RuntimeError(
                "Impossible de joindre digiCamControl sur le port 5513.\n"
                "Vérifiez que le logiciel est ouvert et que le webserver est activé."
            )

    def _slc(self, cmd: str, param1: str = "", param2: str = "", timeout: int = 3) -> str:
        """Envoie une single line command (slc) au webserver et retourne la réponse."""
        r = requests.get(
            f"{DIGICAM_BASE}/",
            params={"slc": cmd, "param1": param1, "param2": param2},
            timeout=timeout,
        )
        return r.text.strip()

    def _configure_capture_output(self):
        """Force digiCamControl à produire un JPEG plein format ENREGISTRÉ SUR LE PC.

        Le Canon 2000D est souvent réglé en RAW seul (.CR2 ~25MB) : comme ?slc=capture
        bloque jusqu'à la fin du transfert USB, la taille du fichier détermine la
        latence — un JPEG Fine (~8MB, toujours 24MP) la divise par ~3-5. Best-effort :
        si un réglage échoue, le fallback rawpy décode le RAW de toute façon.
        """
        # Transfert vers le PC (sinon le fichier reste sur la carte SD)
        try:
            values = [v.strip() for v in self._slc("list", "transfer").splitlines() if v.strip()]
            pc = next((v for v in values if "pc" in v.lower()), None)
            if pc:
                self._slc("set", "transfer", pc)
        except Exception:
            pass
        # Compression JPEG (Fine de préférence), jamais RAW
        try:
            values = [v.strip() for v in self._slc("list", "compressionsetting").splitlines() if v.strip()]
            jpeg_vals = [v for v in values if "jpeg" in v.lower() and "raw" not in v.lower()]
            jpeg = next((v for v in jpeg_vals if "fine" in v.lower()), None) or (jpeg_vals[0] if jpeg_vals else None)
            if jpeg:
                self._slc("set", "compressionsetting", jpeg)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Live view
    # ------------------------------------------------------------------

    def _start_live_view(self):
        # Démarrer le live view dans digiCamControl (ouvre la fenêtre interne)
        try:
            requests.get(f"{DIGICAM_BASE}/?CMD=LiveViewWnd_Show", timeout=5)
            time.sleep(1.5)  # laisser le temps à la caméra d'initialiser le flux
            # Minimiser la fenêtre live view de digiCamControl
            requests.get(f"{DIGICAM_BASE}/?CMD=All_Minimize", timeout=3)
        except Exception:
            pass

        self._running = True
        self._thread = threading.Thread(target=self._live_view_loop, daemon=True)
        self._thread.start()

        # Attendre la première frame valide (max 8 s)
        deadline = time.time() + 8
        while time.time() < deadline:
            with self._lock:
                if self._latest_frame is not None:
                    return
            time.sleep(0.05)
        raise RuntimeError(
            "Pas de live view reçu depuis digiCamControl après 8 secondes.\n"
            "Vérifiez que le Canon est allumé et détecté dans digiCamControl."
        )

    def _live_view_loop(self):
        session = requests.Session()
        while self._running:
            try:
                r = session.get(f"{DIGICAM_BASE}/liveview.jpg", timeout=2)
                if r.status_code == 200 and len(r.content) > 1000:  # ignorer les frames blanches/vides
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    with self._lock:
                        self._latest_frame = frame
            except Exception:
                pass
            time.sleep(0.033)  # ~30 fps max

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_frame(self) -> np.ndarray:
        """Retourne la dernière frame live view (rognée au ratio courant)."""
        with self._lock:
            if self._latest_frame is None:
                raise RuntimeError("Pas de frame disponible depuis le live view.")
            frame = self._latest_frame.copy()
        return self._crop_to_ratio(frame)

    def _get_last_captured(self) -> str:
        """Retourne le chemin du dernier fichier capturé connu de digiCamControl."""
        r = requests.get(f"{DIGICAM_BASE}/?slc=get&param1=lastcaptured", timeout=3)
        return r.text.strip()

    def capture_photo(self) -> str:
        """Déclenche une vraie prise de vue reflex et retourne le chemin du fichier
        pleine résolution enregistré par digiCamControl.

        On mémorise le dernier fichier capturé AVANT de déclencher, puis on attend
        que cette valeur change : sinon la 2e capture renverrait immédiatement le
        chemin de la photo précédente (avant que la nouvelle soit téléchargée).
        """
        try:
            baseline = self._get_last_captured()
            requests.get(f"{DIGICAM_BASE}/?slc=capture", timeout=CAPTURE_TRIGGER_TIMEOUT)
            deadline = time.time() + CAPTURE_WAIT_TIMEOUT
            while time.time() < deadline:
                path = self._get_last_captured()
                if path and path != "-" and path != baseline:
                    return path
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            raise RuntimeError(f"Erreur lors du déclenchement : {e}")
        raise RuntimeError(
            "digiCamControl n'a retourné aucune nouvelle photo après le déclenchement.\n"
            "Vérifiez que la caméra est prête et que l'autofocus accroche."
        )

    def _wait_until_file_stable(self, path: str) -> None:
        """Attend que la taille du fichier se stabilise avant de le décoder.

        lastcaptured peut changer avant la fin du transfert, et cv2.imread sur un
        JPEG tronqué renvoie parfois une image partiellement décodée (bande grise)
        au lieu d'échouer : on ne se fie donc pas au succès de imread mais à la
        stabilité de la taille sur disque.
        """
        deadline = time.time() + FILE_READ_TIMEOUT
        last_size = -1
        while time.time() < deadline:
            try:
                size = Path(path).stat().st_size
            except OSError:
                size = -1
            if size > 0 and size == last_size:
                return
            last_size = size
            time.sleep(0.2)

    def _read_image_unicode(self, path: str) -> Optional[np.ndarray]:
        """Lit une image en frame BGR en gérant les chemins non-ASCII.

        cv2.imread échoue silencieusement (renvoie None) sur les chemins Unicode
        sous Windows : on lit les octets via open() (qui gère l'Unicode) puis on
        décode avec cv2.imdecode.
        """
        try:
            with open(path, "rb") as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
        except OSError:
            return None
        if data.size == 0:
            return None
        frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return frame

    def _decode_raw(self, source) -> Optional[np.ndarray]:
        """Décode un RAW (Canon .CR2/.CR3, Nikon .NEF, etc.) en frame BGR.

        `source` est un chemin OU un objet fichier (BytesIO) : rawpy accepte les deux.
        Le Canon 2000D enregistre en RAW : ni cv2 ni PIL ne savent le décoder. On
        extrait d'abord le JPEG pleine résolution EMBARQUÉ dans le RAW — c'est le
        rendu couleur du boîtier, identique à la photo « bouton » de digiCamControl.
        À défaut, on démosaïque le RAW complet (couleurs LibRaw, un peu plus lent).
        """
        try:
            import rawpy
        except ImportError:
            return None
        try:
            with rawpy.imread(source) as raw:
                # 1) JPEG pleine résolution embarqué (rapide, couleurs boîtier)
                try:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        arr = np.frombuffer(thumb.data, dtype=np.uint8)
                        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            return frame
                except Exception:
                    pass
                # 2) Démosaïquage complet du RAW
                rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
                return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def _decode_bytes(self, content: bytes) -> Optional[np.ndarray]:
        """Décode des octets image (JPEG via cv2, sinon RAW via rawpy) en frame BGR."""
        arr = np.frombuffer(content, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is not None:
            return frame
        return self._decode_raw(io.BytesIO(content))

    def _download_capture(self, path: str) -> Optional[np.ndarray]:
        """Télécharge le fichier capturé en bytes via le webserver (/image/<nom>).

        Évite les problèmes de chemin disque, de permissions et d'Unicode : on ne
        touche jamais au système de fichiers, digiCamControl sert les octets.
        """
        basename = path.replace("\\", "/").rsplit("/", 1)[-1]
        if not basename:
            return None
        try:
            r = requests.get(f"{DIGICAM_BASE}/image/{basename}", timeout=15)
        except Exception:
            return None
        if r.status_code != 200 or len(r.content) < 1000:
            return None
        return self._decode_bytes(r.content)

    def _load_capture_as_frame(self, path: str) -> np.ndarray:
        """Charge le fichier capturé (pleine résolution) en frame BGR OpenCV."""
        # 1) Téléchargement HTTP direct (le plus robuste : ni chemin ni permissions)
        frame = self._download_capture(path)

        # 2) Repli lecture disque : JPEG (cv2 unicode-safe puis PIL) puis RAW rawpy
        if frame is None:
            self._wait_until_file_stable(path)
            frame = self._read_image_unicode(path)
        if frame is None:
            try:
                img = Image.open(path).convert("RGB")
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception:
                frame = None
        if frame is None:
            frame = self._decode_raw(path)

        if frame is None:
            p = Path(path)
            exists = p.exists()
            size = p.stat().st_size if exists else 0
            raw_ext = p.suffix.lower() in {".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng"}
            hint = (
                "Fichier RAW : installez le décodeur avec « pip install rawpy »."
                if raw_ext
                else "Vérifiez que digiCamControl transfère bien le fichier sur le PC."
            )
            raise RuntimeError(
                "Impossible de lire la photo capturée.\n"
                f"Fichier : {path}\n"
                f"existe={exists}, taille={size} o, extension={p.suffix or '?'}\n"
                f"{hint}"
            )
        return frame

    def _downscale(self, frame: np.ndarray) -> np.ndarray:
        """Réduit la définition à MAX_OUTPUT_LONG_EDGE px sur le grand côté.

        Accélère fortement compose/encodage/aperçu côté UI (thread principal). INTER_AREA
        est l'interpolation adaptée à la réduction. No-op si déjà assez petit.
        """
        h, w = frame.shape[:2]
        long_edge = max(h, w)
        if long_edge <= MAX_OUTPUT_LONG_EDGE:
            return frame
        scale = MAX_OUTPUT_LONG_EDGE / long_edge
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

    def capture_full_frame(self) -> np.ndarray:
        """Déclenche le reflex et retourne la photo (rognée 16:9, redimensionnée pour
        l'impression) — même cadrage que le live view pour rester fidèle à l'aperçu."""
        path = self.capture_photo()
        frame = self._load_capture_as_frame(path)
        return self._downscale(self._crop_to_ratio(frame))

    def set_camera_index(self, camera_index: int):
        self.camera_index = camera_index

    def set_aspect_ratio(self, ratio: tuple):
        """Définit le ratio de cadrage, ex: (16, 9) ou (4, 3)."""
        self.aspect_ratio = ratio

    def release(self):
        self._running = False
        try:
            requests.get(f"{DIGICAM_BASE}/?CMD=LiveViewWnd_Hide", timeout=3)
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    # ------------------------------------------------------------------
    # Crop au ratio courant (16:9 / 4:3)
    # ------------------------------------------------------------------

    def _crop_to_ratio(self, frame: np.ndarray) -> np.ndarray:
        rw, rh = self.aspect_ratio
        h, w = frame.shape[:2]
        target_w = w
        target_h = int(w * rh / rw)
        if target_h > h:
            target_h = h
            target_w = int(h * rw / rh)
        x = (w - target_w) // 2
        y = (h - target_h) // 2
        return frame[y:y + target_h, x:x + target_w]
