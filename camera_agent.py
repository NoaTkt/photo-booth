import io
import threading
import time
from typing import Optional

import cv2
import numpy as np
import requests
from PIL import Image

DIGICAM_BASE = "http://localhost:5513"


class CameraAgent:
    """Pilote le Canon EOS via l'API HTTP de digiCamControl."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_connection()
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
        """Retourne la dernière frame live view (rognée 16:9)."""
        with self._lock:
            if self._latest_frame is None:
                raise RuntimeError("Pas de frame disponible depuis le live view.")
            frame = self._latest_frame.copy()
        return self._crop_16_9(frame)

    def capture_photo(self) -> Optional[str]:
        """Déclenche une prise de vue et retourne le chemin du fichier capturé."""
        try:
            # Déclencher
            requests.get(f"{DIGICAM_BASE}/?slc=capture", timeout=15)
            # Attendre que la photo soit disponible (max 10 s)
            deadline = time.time() + 10
            while time.time() < deadline:
                r = requests.get(
                    f"{DIGICAM_BASE}/?slc=get&param1=lastcaptured", timeout=3
                )
                path = r.text.strip()
                if path and path != "-":
                    return path
                time.sleep(0.3)
        except Exception as e:
            raise RuntimeError(f"Erreur lors du déclenchement : {e}")
        return None

    def set_camera_index(self, camera_index: int):
        self.camera_index = camera_index

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
    # Crop 16:9
    # ------------------------------------------------------------------

    def _crop_16_9(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        target_w = w
        target_h = int(w * 9 / 16)
        if target_h > h:
            target_h = h
            target_w = int(h * 16 / 9)
        x = (w - target_w) // 2
        y = (h - target_h) // 2
        return frame[y:y + target_h, x:x + target_w]
