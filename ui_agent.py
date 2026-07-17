import cv2
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QObject, QEvent, QPoint, Signal, QThread
from PySide6.QtGui import QIcon, QImage, QPixmap, QColor
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

# ─── Custom Label with textChanged signal ────────────────────────────────────
class ValueLabel(QLabel):
    """QLabel que emite signal textChanged."""
    textChanged = Signal(str)
    
    def setText(self, text: str):
        super().setText(text)
        self.textChanged.emit(text)


# ─── Touch scroll filter ───────────────────────────────────────────────────────
class TouchScrollFilter(QObject):
    """Install on a QAbstractScrollArea to enable finger-drag scrolling."""

    def __init__(self, scroll_area: QAbstractScrollArea, parent=None):
        super().__init__(parent)
        self._area = scroll_area
        self._last_pos: QPoint | None = None
        vp = scroll_area.viewport()
        vp.setAttribute(Qt.WA_AcceptTouchEvents, True)
        vp.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        t = event.type()
        if t == QEvent.TouchBegin:
            pts = event.points()
            if pts:
                self._last_pos = pts[0].position().toPoint()
            event.accept()
            return True
        if t == QEvent.TouchUpdate:
            pts = event.points()
            if pts and self._last_pos is not None:
                cur = pts[0].position().toPoint()
                delta = cur - self._last_pos
                self._last_pos = cur
                vsb = self._area.verticalScrollBar()
                if vsb:
                    vsb.setValue(vsb.value() - delta.y())
            event.accept()
            return True
        if t == QEvent.TouchEnd:
            self._last_pos = None
            event.accept()
            return True
        return False

# ─── Design tokens ─────────────────────────────────────────────────────────────
BG_DARK      = "#0D0F14"
BG_CARD      = "#161A24"
BG_CARD2     = "#1E2333"
ACCENT       = "#4F8EF7"
ACCENT2      = "#7B5CF0"
TEXT_PRIMARY = "#F0F2FF"
TEXT_MUTED   = "#8890AA"
DANGER       = "#E05C5C"
SUCCESS      = "#4DD9AC"
BORDER       = "#2A2F45"

STYLE_LABEL_TITLE = f"color: {TEXT_PRIMARY}; font-size: 17px; font-weight: 600; background: transparent; border: none;"
STYLE_LABEL_MUTED = f"color: {TEXT_MUTED}; font-size: 14px; background: transparent; border: none;"

SLIDER_QSS = f"""
QSlider::groove:horizontal {{
    height: 10px;
    background: {BORDER};
    border-radius: 5px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ACCENT2}, stop:1 {ACCENT});
    border-radius: 5px;
}}
QSlider::handle:horizontal {{
    background: {TEXT_PRIMARY};
    border: 3px solid {ACCENT};
    width: 38px;
    height: 38px;
    margin: -14px 0;
    border-radius: 19px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT};
    border-color: white;
}}
"""

LIST_QSS = f"""
QListWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    border: none;
    border-radius: 12px;
    padding: 4px;
}}
QListWidget::item {{
    border: none;
    border-radius: 0px;
    padding: 0px;
    margin: 4px;
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QListWidget::item:selected {{
    background-color: transparent;
    color: white;
    border: 2px solid {ACCENT};
    border-radius: 8px;
}}
QListWidget::item:hover {{
    background-color: transparent;
    border: 2px solid {ACCENT2};
    border-radius: 8px;
}}
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 40px;
    border-radius: 14px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 12px;
    min-height: 60px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::handle:vertical:pressed {{ background: {ACCENT2}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

SCROLLAREA_QSS = f"""
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 40px;
    border-radius: 14px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 12px;
    min-height: 60px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::handle:vertical:pressed {{ background: {ACCENT2}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
"""


def _btn_primary(text, parent=None):
    btn = QPushButton(text, parent)
    btn.setMinimumHeight(62)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {ACCENT2}, stop:1 {ACCENT});
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 17px;
            font-weight: 600;
            padding: 0 24px;
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #5030A0, stop:1 #3060C0);
        }}
        QPushButton:disabled {{
            background: {BORDER};
            color: {TEXT_MUTED};
        }}
    """)
    return btn


def _btn_secondary(text, parent=None):
    btn = QPushButton(text, parent)
    btn.setMinimumHeight(56)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {BG_CARD2};
            color: {TEXT_PRIMARY};
            border: 1.5px solid {BORDER};
            border-radius: 14px;
            font-size: 17px;
            font-weight: 500;
            padding: 0 20px;
        }}
        QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        QPushButton:pressed {{ background: {BG_CARD}; }}
    """)
    return btn


def _btn_danger(text, parent=None):
    btn = QPushButton(text, parent)
    btn.setMinimumHeight(62)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: rgba(224,92,92,0.15);
            color: {DANGER};
            border: 1.5px solid {DANGER};
            border-radius: 14px;
            font-size: 17px;
            font-weight: 600;
            padding: 0 24px;
        }}
        QPushButton:hover {{ background: rgba(224,92,92,0.30); }}
        QPushButton:pressed {{ background: rgba(224,92,92,0.45); }}
    """)
    return btn


def _section_card(title, parent):
    frame = QFrame(parent)
    frame.setStyleSheet(f"""
        QFrame {{
            background: {BG_CARD2};
            border: 1.5px solid {BORDER};
            border-radius: 16px;
        }}
    """)
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(20, 14, 20, 20)
    outer.setSpacing(12)

    title_lbl = QLabel(title.upper(), frame)
    title_lbl.setStyleSheet(f"""
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        background: transparent;
        border: none;
    """)
    outer.addWidget(title_lbl)

    sep = QFrame(frame)
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet(f"background: {BORDER}; border: none; max-height: 1px;")
    outer.addWidget(sep)

    return frame, outer


def _spinbox_row(label_text: str, min_val: int, max_val: int, init_val: int, parent: QWidget):
    """Returns (container_widget, value_label) for a tactile +/- stepper row."""
    BTN_QSS = f"""
        QPushButton {{
            background: {BG_CARD};
            color: {TEXT_PRIMARY};
            border: 1.5px solid {BORDER};
            border-radius: 16px;
            font-size: 26px;
            font-weight: 700;
            min-width: 56px;
            min-height: 56px;
            max-width: 56px;
            max-height: 56px;
        }}
        QPushButton:hover {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
        QPushButton:pressed {{ background: {ACCENT2}; border-color: {ACCENT2}; }}
    """
    VAL_QSS = f"""
        color: {TEXT_PRIMARY};
        font-size: 22px;
        font-weight: 700;
        background: {BG_DARK};
        border: 1.5px solid {BORDER};
        border-radius: 12px;
        padding: 6px 20px;
        min-width: 70px;
    """

    container = QWidget(parent)
    container.setStyleSheet("background: transparent;")
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    lbl = QLabel(label_text, container)
    lbl.setStyleSheet(STYLE_LABEL_TITLE + "; padding-left: 10px;")
    lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    btn_minus = QPushButton("\u2212", container)
    btn_minus.setStyleSheet(BTN_QSS)
    btn_minus.setFocusPolicy(Qt.NoFocus)

    val_lbl = ValueLabel(str(init_val), container)
    val_lbl.setAlignment(Qt.AlignCenter)
    val_lbl.setStyleSheet(VAL_QSS)

    btn_plus = QPushButton("+", container)
    btn_plus.setStyleSheet(BTN_QSS)
    btn_plus.setFocusPolicy(Qt.NoFocus)

    def _dec():
        v = int(val_lbl.text())
        if v > min_val:
            val_lbl.setText(str(v - 1))

    def _inc():
        v = int(val_lbl.text())
        if v < max_val:
            val_lbl.setText(str(v + 1))

    btn_minus.clicked.connect(_dec)
    btn_plus.clicked.connect(_inc)

    row.addWidget(lbl)
    row.addWidget(btn_minus)
    row.addWidget(val_lbl)
    row.addWidget(btn_plus)

    return container, val_lbl


def _choice_button_row(label_text: str, choices: list, init_idx: int, parent: QWidget):
    """Returns (container_widget, value_label) for a tactile +/- selector row."""
    BTN_QSS = f"""
        QPushButton {{
            background: {BG_CARD};
            color: {TEXT_PRIMARY};
            border: 1.5px solid {BORDER};
            border-radius: 16px;
            font-size: 26px;
            font-weight: 700;
            min-width: 56px;
            min-height: 56px;
            max-width: 56px;
            max-height: 56px;
        }}
        QPushButton:hover {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
        QPushButton:pressed {{ background: {ACCENT2}; border-color: {ACCENT2}; }}
    """
    VAL_QSS = f"""
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 600;
        background: {BG_DARK};
        border: 1.5px solid {BORDER};
        border-radius: 12px;
        padding: 8px 16px;
        min-width: 120px;
    """

    container = QWidget(parent)
    container.setStyleSheet("background: transparent;")
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    lbl = QLabel(label_text, container)
    lbl.setStyleSheet(STYLE_LABEL_TITLE + "; padding-left: 10px;")
    lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    btn_minus = QPushButton("\u2212", container)
    btn_minus.setStyleSheet(BTN_QSS)
    btn_minus.setFocusPolicy(Qt.NoFocus)

    val_lbl = ValueLabel(choices[init_idx] if 0 <= init_idx < len(choices) else "", container)
    val_lbl.setAlignment(Qt.AlignCenter)
    val_lbl.setStyleSheet(VAL_QSS)
    val_lbl.setProperty("_choices", choices)
    val_lbl.setProperty("_current_idx", init_idx)

    btn_plus = QPushButton("+", container)
    btn_plus.setStyleSheet(BTN_QSS)
    btn_plus.setFocusPolicy(Qt.NoFocus)

    def _prev():
        idx = val_lbl.property("_current_idx")
        choices_list = val_lbl.property("_choices")
        if choices_list:
            idx = (idx - 1) % len(choices_list)
            val_lbl.setProperty("_current_idx", idx)
            val_lbl.setText(choices_list[idx])

    def _next():
        idx = val_lbl.property("_current_idx")
        choices_list = val_lbl.property("_choices")
        if choices_list:
            idx = (idx + 1) % len(choices_list)
            val_lbl.setProperty("_current_idx", idx)
            val_lbl.setText(choices_list[idx])

    btn_minus.clicked.connect(_prev)
    btn_plus.clicked.connect(_next)

    row.addWidget(lbl)
    row.addWidget(btn_minus)
    row.addWidget(val_lbl)
    row.addWidget(btn_plus)

    return container, val_lbl


class OverlayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.preview_label = QLabel("Chargement de la camera...", self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            f"background: {BG_DARK}; color: {TEXT_MUTED}; font-size: 22px;"
        )

        self.controls_widget = QWidget(self)
        self.controls_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.controls_widget.setStyleSheet("background: transparent;")

        self.controls_layout = QVBoxLayout(self.controls_widget)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(0)
        self.controls_layout.addStretch()

        self.panel_container = QWidget(self.controls_widget)
        self.panel_container.setVisible(False)
        self.panel_container.setStyleSheet(f"""
            QWidget {{
                background: {BG_CARD};
                border-radius: 24px;
                border: 1.5px solid {BORDER};
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.panel_container.setGraphicsEffect(shadow)

        self.panel_scroll = QScrollArea(self.panel_container)
        self.panel_scroll.setWidgetResizable(True)
        self.panel_scroll.setStyleSheet(SCROLLAREA_QSS)
        self.panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._panel_touch = TouchScrollFilter(self.panel_scroll, self.panel_scroll)

        self.panel_body = QWidget()
        self.panel_body.setStyleSheet("background: transparent;")
        self.panel_scroll.setWidget(self.panel_body)

        self.panel_content_layout = QVBoxLayout(self.panel_body)
        self.panel_content_layout.setContentsMargins(24, 20, 24, 24)
        self.panel_content_layout.setSpacing(16)

        self.countdown_label = QLabel("", self)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet(
            "color: white; font-size: 150px; font-weight: 900;"
            "background: rgba(0,0,0,0.50); border-radius: 24px;"
        )
        self.countdown_label.setVisible(False)

    def resizeEvent(self, event):
        self.preview_label.setGeometry(self.rect())
        self.controls_widget.setGeometry(self.rect())
        self.countdown_label.setGeometry(self.rect())

        panel_w = int(self.width() * 0.92)
        panel_h = min(self.height() - 160, 900)
        self.panel_container.setFixedWidth(panel_w)
        self.panel_container.setFixedHeight(panel_h)
        self.panel_container.move(
            (self.width() - panel_w) // 2,
            (self.height() - panel_h) // 2,
        )
        self.panel_scroll.setGeometry(self.panel_container.rect())
        self.countdown_label.raise_()
        self.panel_container.raise_()
        super().resizeEvent(event)


class CaptureWorker(QThread):
    """Déclenche la vraie prise de vue reflex hors du thread UI.

    La capture (shutter + transfert du fichier pleine résolution) bloque plusieurs
    secondes : l'exécuter ici évite de figer l'interface et le live view.
    """

    captured = Signal(object)  # frame BGR numpy pleine résolution
    failed = Signal(str)

    def __init__(self, camera_agent, parent=None):
        super().__init__(parent)
        self.camera_agent = camera_agent

    def run(self):
        try:
            frame = self.camera_agent.capture_full_frame()
            self.captured.emit(frame)
        except Exception as error:
            self.failed.emit(str(error))


class PhotoBoothUI(QMainWindow):
    def __init__(self, camera_agent, photo_agent, print_agent):
        super().__init__()
        self.camera_agent = camera_agent
        self.photo_agent = photo_agent
        self.print_agent = print_agent
        self.last_frame = None
        self.last_saved_photo = None
        self.selected_gallery_photo = None
        self._capture_worker = None

        self.setWindowTitle("PhotoBooth")
        self.setStyleSheet(f"QMainWindow {{ background: {BG_DARK}; }}")
        self._build_ui()
        self.showFullScreen()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self.timer.start(33)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._countdown_tick)
        self.countdown_seconds = 0

    def _build_ui(self):
        self.overlay = OverlayWidget(self)
        self.preview_label = self.overlay.preview_label
        self.countdown_label = self.overlay.countdown_label

        self.background_folder = Path(__file__).resolve().parent / "backgrounds"
        self.background_folder.mkdir(parents=True, exist_ok=True)
        self.selected_background_path = None
        self.selected_overlay_path = None
        self.corner_radius = 25
        self.photo_scale = 110
        self.countdown_duration = 5

        self.status_label = QLabel("Pret", self)
        self.status_label.setStyleSheet(
            f"color: {SUCCESS}; font-size: 15px; padding: 6px 16px;"
            f"background: rgba(77,217,172,0.10); border-radius: 10px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(40)
        self.status_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.settings_button = QToolButton(self.overlay.controls_widget)
        self.settings_button.setText("\u2699")
        self.settings_button.setFixedSize(64, 64)
        self.settings_button.setStyleSheet(f"""
            QToolButton {{
                font-size: 26px;
                background: rgba(22,26,36,0.85);
                color: {TEXT_PRIMARY};
                border: 1.5px solid {BORDER};
                border-radius: 32px;
            }}
            QToolButton:hover {{
                background: {BG_CARD2};
                border-color: {ACCENT};
                color: {ACCENT};
            }}
        """)
        self.settings_button.clicked.connect(self.toggle_settings)

        self.capture_button = QPushButton(self.overlay.controls_widget)
        self.capture_button.setFixedSize(160, 160)
        camera_icon_path = Path(__file__).resolve().parent / "camera.png"
        if camera_icon_path.exists():
            self.capture_button.setIcon(QIcon(str(camera_icon_path)))
            self.capture_button.setIconSize(QSize(72, 72))
        else:
            self.capture_button.setText("O")
        self.capture_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {ACCENT2}, stop:1 {ACCENT});
                border: 4px solid rgba(255,255,255,0.18);
                border-radius: 80px;
                font-size: 48px;
                color: white;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #8A70FF, stop:1 #60A0FF);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #5030A0, stop:1 #3060C0);
            }}
            QPushButton:disabled {{ background: {BORDER}; }}
        """)
        self.capture_button.clicked.connect(self.start_capture_countdown)

        self.gallery_button = _btn_secondary("Galerie", self.overlay.controls_widget)
        self.gallery_button.setMinimumHeight(70)
        self.gallery_button.clicked.connect(self.toggle_gallery)

        self.print_button = _btn_secondary("Imprimer", self.overlay.controls_widget)
        self.print_button.setMinimumHeight(70)
        self.print_button.clicked.connect(self.print_last_photo)

        top_bar = QWidget(self.overlay.controls_widget)
        top_bar.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(24, 16, 24, 0)
        top_layout.addStretch()
        top_layout.addWidget(self.settings_button)

        self.overlay.controls_layout.insertWidget(0, top_bar)
        self.overlay.controls_layout.insertWidget(1, self.status_label)

        bottom_bg = QWidget(self.overlay.controls_widget)
        bottom_bg.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 transparent, stop:1 rgba(13,15,20,0.92));"
        )
        bottom_layout = QHBoxLayout(bottom_bg)
        bottom_layout.setContentsMargins(32, 20, 32, 48)
        bottom_layout.setSpacing(16)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.gallery_button)
        bottom_layout.addSpacing(24)
        bottom_layout.addWidget(self.capture_button)
        bottom_layout.addSpacing(24)
        bottom_layout.addWidget(self.print_button)
        bottom_layout.addStretch()
        self.overlay.controls_layout.addWidget(bottom_bg)

        self.gallery_widget = QWidget(self.overlay.panel_container)
        self.gallery_widget.setStyleSheet("background: transparent;")
        self.gallery_widget.setVisible(False)
        self._build_gallery()

        self.settings_widget = QWidget(self.overlay.panel_container)
        self.settings_widget.setStyleSheet("background: transparent;")
        self.settings_widget.setVisible(False)
        self._build_settings()

        panel_header = QWidget(self.overlay.panel_container)
        panel_header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(panel_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.panel_back_button = _btn_secondary("Retour", panel_header)
        self.panel_back_button.setMinimumHeight(48)
        self.panel_back_button.setMaximumWidth(150)
        self.panel_back_button.clicked.connect(self.hide_panel)
        self.panel_back_button.setVisible(False)

        self.panel_title_label = QLabel("", panel_header)
        self.panel_title_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {TEXT_PRIMARY}; background: transparent;"
        )
        self.panel_title_label.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.panel_back_button)
        header_layout.addStretch()
        header_layout.addWidget(self.panel_title_label)
        header_layout.addStretch()

        panel_layout = self.overlay.panel_content_layout
        panel_layout.addWidget(panel_header)
        panel_layout.addWidget(self.gallery_widget)
        panel_layout.addWidget(self.settings_widget)

        # --- Review panel (shown after a photo is taken) ---
        self.review_widget = QWidget(self.overlay.controls_widget)
        self.review_widget.setVisible(False)
        self.review_widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(20,20,24,0.95);
                border: 1.5px solid {BORDER};
                border-radius: 18px;
            }}
        """)
        review_layout = QHBoxLayout(self.review_widget)
        review_layout.setContentsMargins(20, 20, 20, 20)
        review_layout.setSpacing(20)

        # Large preview on the left
        self.review_image_label = QLabel("Apercu", self.review_widget)
        self.review_image_label.setAlignment(Qt.AlignCenter)
        self.review_image_label.setStyleSheet(f"background: {BG_DARK}; color: {TEXT_MUTED}; border-radius: 12px;")
        review_layout.addWidget(self.review_image_label, stretch=3)

        # Controls on the right
        controls_col = QWidget(self.review_widget)
        controls_col.setStyleSheet("background: transparent;")
        controls_layout = QVBoxLayout(controls_col)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)

        # Copies selector (1..3)
        copies_row, self.copies_value_label = _spinbox_row("Copies", 1, 3, 1, controls_col)
        controls_layout.addWidget(copies_row)

        # Print button
        self.review_print_button = _btn_primary("Imprimer", controls_col)
        self.review_print_button.clicked.connect(self._print_review_photo)
        controls_layout.addWidget(self.review_print_button)

        # Cancel button
        self.review_cancel_button = _btn_secondary("Annuler", controls_col)
        self.review_cancel_button.clicked.connect(self._hide_review)
        controls_layout.addWidget(self.review_cancel_button)

        controls_layout.addStretch()
        review_layout.addWidget(controls_col, stretch=1)

        # Place review widget above preview and center it
        self.review_widget.setFixedSize(int(self.width() * 0.84), int(self.height() * 0.72))
        self.review_widget.move((self.width() - self.review_widget.width()) // 2, (self.height() - self.review_widget.height()) // 2)
        self.review_widget.raise_()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.overlay)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def _build_gallery(self):
        """Galerie: 2/3 mosaïque à gauche  |  1/3 aperçu à droite"""
        gallery_layout = QHBoxLayout(self.gallery_widget)
        gallery_layout.setContentsMargins(0, 0, 0, 0)
        gallery_layout.setSpacing(16)

        # ── LEFT: Mosaïque large ──────────────────────────────────────────────
        self.gallery_list = QListWidget(self.gallery_widget)
        self.gallery_list.setViewMode(QListWidget.IconMode)
        self.gallery_list.setIconSize(QSize(200, 200))
        self.gallery_list.setResizeMode(QListWidget.Adjust)
        self.gallery_list.setMovement(QListWidget.Static)
        self.gallery_list.setSpacing(16)
        self.gallery_list.setUniformItemSizes(True)
        self.gallery_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gallery_list.setMinimumHeight(300)
        self.gallery_list.setStyleSheet(LIST_QSS)
        self.gallery_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.gallery_list.setWordWrap(True)
        self.gallery_list.currentItemChanged.connect(self._on_gallery_selection)
        self._gallery_touch = TouchScrollFilter(self.gallery_list, self.gallery_list)

        # ── RIGHT: Aperçu compact ─────────────────────────────────────────────
        right_panel = QWidget(self.gallery_widget)
        right_panel.setStyleSheet("background: transparent;")
        right_panel.setMinimumWidth(250)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        self.gallery_preview_label = QLabel("Selectionnez\nune photo", self.gallery_widget)
        self.gallery_preview_label.setAlignment(Qt.AlignCenter)
        self.gallery_preview_label.setStyleSheet(
            f"background: {BG_DARK}; color: {TEXT_MUTED}; font-size: 15px;"
            f"border-radius: 16px; border: 1.5px solid {BORDER}; padding: 12px;"
        )
        self.gallery_preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gallery_preview_label.setMinimumHeight(180)

        self.print_selected_button = _btn_primary("Imprimer", self.gallery_widget)
        self.print_selected_button.setEnabled(False)
        self.print_selected_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.print_selected_button.clicked.connect(self.print_selected_photo)

        # Copies selector for gallery print (1..3)
        copies_row, self.gallery_copies_value_label = _spinbox_row("Copies", 1, 3, 1, right_panel)
        right_layout.addWidget(copies_row)

        right_layout.addWidget(self.gallery_preview_label, stretch=1)
        right_layout.addWidget(self.print_selected_button)

        gallery_layout.addWidget(self.gallery_list, stretch=2)
        gallery_layout.addWidget(right_panel, stretch=1)

    def _build_settings(self):
        settings_layout = QVBoxLayout(self.settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(14)

        # ── Card: Camera ──
        cam_card, cam_layout = _section_card("Camera", self.settings_widget)
        cam_row, self.camera_value_label = _spinbox_row(
            "Index camera", 0, 10, self.camera_agent.camera_index, cam_card
        )
        self.output_format_label = QLabel("Format photo : 1280 x 720", cam_card)
        self.output_format_label.setStyleSheet(STYLE_LABEL_MUTED)
        cam_layout.addWidget(cam_row)
        cam_layout.addWidget(self.output_format_label)
        settings_layout.addWidget(cam_card)

        # ── Card: Imprimante ──
        print_card, print_layout = _section_card("Imprimante", self.settings_widget)
        printers = self.print_agent.get_installed_printers()
        if not printers:
            printers = ["Aucune imprimante"]
        current_printer = self.print_agent.printer_name or self.print_agent.get_default_printer()
        if current_printer not in printers:
            current_printer = printers[0] if printers else "Aucune imprimante"
        printer_idx = printers.index(current_printer) if current_printer in printers else 0
        self.printer_row, self.printer_value_label = _choice_button_row(
            "Imprimante :", printers, printer_idx, print_card
        )
        self.printer_choices = printers
        print_layout.addWidget(self.printer_row)
        
        # ── Orientation impression ──
        orientations = ["Portrait", "Paysage"]
        orientation_idx = 0
        if self.print_agent.orientation == "Paysage":
            orientation_idx = 1
        self.orientation_row, self.orientation_value_label = _choice_button_row(
            "Orientation :", orientations, orientation_idx, print_card
        )
        print_layout.addWidget(self.orientation_row)
        settings_layout.addWidget(print_card)

        # ── Card: Image de fond ──
        bg_card, bg_layout = _section_card("Image de fond", self.settings_widget)
        self.background_files = []
        self.background_display_names = []
        self._load_background_choices()
        bg_idx = 0
        if self.selected_background_path:
            for i, fpath in enumerate(self.background_files):
                if fpath == self.selected_background_path:
                    bg_idx = i
                    break
        self.background_row, self.background_value_label = _choice_button_row(
            "Fond :", self.background_display_names, bg_idx, bg_card
        )
        self.add_background_button = _btn_secondary("+ Ajouter un fond", bg_card)
        self.add_background_button.clicked.connect(self.browse_background_image)
        self.background_preview = QLabel("Apercu du fond", bg_card)
        self.background_preview.setAlignment(Qt.AlignCenter)
        self.background_preview.setStyleSheet(
            f"background: {BG_DARK}; color: {TEXT_MUTED}; font-size: 15px;"
            f"border-radius: 12px; border: 1.5px solid {BORDER}; padding: 12px;"
        )
        self.background_preview.setMinimumHeight(130)
        self.background_value_label.textChanged.connect(self.update_background_preview)
        self.update_background_preview()

        # --- Top overlay selection (applies above the photo) ---
        ov_idx = 0
        self.overlay_row, self.overlay_value_label = _choice_button_row(
            "Superposition :", self.overlay_display_names, ov_idx, bg_card
        )
        self.overlay_preview = QLabel("Apercu de la superposition", bg_card)
        self.overlay_preview.setAlignment(Qt.AlignCenter)
        self.overlay_preview.setStyleSheet(
            f"background: {BG_DARK}; color: {TEXT_MUTED}; font-size: 15px;"
            f"border-radius: 12px; border: 1.5px solid {BORDER}; padding: 12px;"
        )
        self.overlay_preview.setMinimumHeight(100)
        self.overlay_value_label.textChanged.connect(self.update_overlay_preview)
        self.update_overlay_preview()
        self.overlay_instruction = QLabel(
            "Utilise une superposition identique au fond, sans arrière-plan, de la même taille que le fond.",
            bg_card,
        )
        self.overlay_instruction.setWordWrap(True)
        self.overlay_instruction.setStyleSheet(
            f"{STYLE_LABEL_MUTED}; padding-top: 6px;"
        )
        bg_layout.addWidget(self.background_row)
        bg_layout.addWidget(self.add_background_button)
        bg_layout.addWidget(self.background_preview)
        bg_layout.addWidget(self.overlay_row)
        bg_layout.addWidget(self.overlay_preview)
        bg_layout.addWidget(self.overlay_instruction)
        settings_layout.addWidget(bg_card)

        # ── Card: Ajustements photo ──
        adj_card, adj_layout = _section_card("Ajustements photo", self.settings_widget)
        self.scale_label = QLabel(f"Zoom photo : {self.photo_scale}%", adj_card)
        self.scale_label.setStyleSheet(STYLE_LABEL_TITLE)
        self.scale_slider = QSlider(Qt.Horizontal, adj_card)
        self.scale_slider.setMinimum(60)
        self.scale_slider.setMaximum(140)
        self.scale_slider.setValue(self.photo_scale)
        self.scale_slider.setMinimumHeight(52)
        self.scale_slider.setStyleSheet(SLIDER_QSS)
        self.scale_slider.valueChanged.connect(self.update_scale_label)
        self.corner_label = QLabel("Arrondi photo : 20", adj_card)
        self.corner_label.setStyleSheet(STYLE_LABEL_TITLE)
        self.corner_slider = QSlider(Qt.Horizontal, adj_card)
        self.corner_slider.setMinimum(0)
        self.corner_slider.setMaximum(100)
        self.corner_slider.setValue(20)
        self.corner_slider.setMinimumHeight(52)
        self.corner_slider.setStyleSheet(SLIDER_QSS)
        self.corner_slider.valueChanged.connect(self.update_corner_label)
        adj_layout.addWidget(self.scale_label)
        adj_layout.addWidget(self.scale_slider)
        adj_layout.addSpacing(8)
        adj_layout.addWidget(self.corner_label)
        adj_layout.addWidget(self.corner_slider)
        settings_layout.addWidget(adj_card)

        # ── Card: Decompte ──
        cnt_card, cnt_layout = _section_card("Decompte", self.settings_widget)
        self.countdown_label_setting = QLabel(
            f"Duree du decompte : {self.countdown_duration}s", cnt_card
        )
        self.countdown_label_setting.setStyleSheet(STYLE_LABEL_TITLE)
        self.countdown_slider = QSlider(Qt.Horizontal, cnt_card)
        self.countdown_slider.setMinimum(1)
        self.countdown_slider.setMaximum(10)
        self.countdown_slider.setValue(self.countdown_duration)
        self.countdown_slider.setMinimumHeight(52)
        self.countdown_slider.setStyleSheet(SLIDER_QSS)
        self.countdown_slider.valueChanged.connect(self.update_countdown_label)
        cnt_layout.addWidget(self.countdown_label_setting)
        cnt_layout.addWidget(self.countdown_slider)
        settings_layout.addWidget(cnt_card)

        apply_btn = _btn_primary("Appliquer les parametres", self.settings_widget)
        apply_btn.clicked.connect(self.apply_settings)
        settings_layout.addWidget(apply_btn)

        quit_btn = _btn_danger("Quitter l'application", self.settings_widget)
        quit_btn.clicked.connect(self.close)
        settings_layout.addWidget(quit_btn)

        settings_layout.addStretch()

    def toggle_gallery(self):
        gallery_visible = not self.gallery_widget.isVisible()
        self.settings_widget.hide()
        self.gallery_widget.setVisible(gallery_visible)
        self.overlay.panel_container.setVisible(gallery_visible)
        self.panel_title_label.setText("Galerie")
        self.panel_back_button.setVisible(gallery_visible)
        if gallery_visible:
            self.load_gallery_photos()
            self.set_status("Galerie ouverte.")
        else:
            self.set_status("Galerie fermee.")

    def toggle_settings(self):
        settings_visible = not self.settings_widget.isVisible()
        self.gallery_widget.hide()
        self.settings_widget.setVisible(settings_visible)
        self.overlay.panel_container.setVisible(settings_visible)
        self.panel_title_label.setText("Parametres")
        self.panel_back_button.setVisible(settings_visible)
        if settings_visible:
            self.camera_value_label.setText(str(self.camera_agent.camera_index))
            self._load_background_choices()
            self.printer_choices = self.print_agent.get_installed_printers()
            if not self.printer_choices:
                self.printer_choices = ["Aucune imprimante"]
            current_printer = self.print_agent.printer_name or self.print_agent.get_default_printer()
            if current_printer not in self.printer_choices:
                current_printer = self.printer_choices[0] if self.printer_choices else "Aucune imprimante"
            printer_idx = self.printer_choices.index(current_printer) if current_printer in self.printer_choices else 0
            self.printer_value_label.setProperty("_choices", self.printer_choices)
            self.printer_value_label.setProperty("_current_idx", printer_idx)
            self.printer_value_label.setText(self.printer_choices[printer_idx])
            bg_idx = 0
            if self.selected_background_path:
                for i, fpath in enumerate(self.background_files):
                    if fpath == self.selected_background_path:
                        bg_idx = i
                        break
            ov_idx = 0
            if self.selected_overlay_path:
                for i, fpath in enumerate(self.overlay_files):
                    if fpath == self.selected_overlay_path:
                        ov_idx = i
                        break
            self.background_value_label.setProperty("_choices", self.background_display_names)
            self.background_value_label.setProperty("_current_idx", bg_idx)
            self.background_value_label.setText(self.background_display_names[bg_idx] if bg_idx < len(self.background_display_names) else "")
            # Overlay selection
            self.overlay_value_label.setProperty("_choices", self.overlay_display_names)
            self.overlay_value_label.setProperty("_current_idx", ov_idx)
            self.overlay_value_label.setText(self.overlay_display_names[ov_idx] if ov_idx < len(self.overlay_display_names) else "")
            self.update_corner_label(self.corner_slider.value())
            self.update_scale_label(self.scale_slider.value())
            self.set_status("Parametres ouverts.")
        else:
            self.set_status("Parametres fermes.")

    def hide_panel(self):
        self.gallery_widget.hide()
        self.settings_widget.hide()
        self.overlay.panel_container.hide()
        self.panel_back_button.setVisible(False)
        self.panel_title_label.setText("")
        self.set_status("Retour a l'interface principale.")

    def load_gallery_photos(self):
        self.gallery_list.clear()
        photos_folder = Path(__file__).resolve().parent / "photos"
        photo_paths = sorted(
            [*photos_folder.glob("*.jpg"), *photos_folder.glob("*.png")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for photo_path in photo_paths:
            pixmap = QPixmap(str(photo_path)).scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(photo_path.name)
            item.setIcon(pixmap)
            item.setData(Qt.UserRole, str(photo_path))
            self.gallery_list.addItem(item)
        self.gallery_preview_label.setText("Selectionnez\nune photo")
        self.gallery_preview_label.setPixmap(QPixmap())
        self.print_selected_button.setEnabled(False)
        self.selected_gallery_photo = None

    def _on_gallery_selection(self, current, previous=None):
        if current is None:
            self.gallery_preview_label.setText("Selectionnez\nune photo")
            self.gallery_preview_label.setPixmap(QPixmap())
            self.print_selected_button.setEnabled(False)
            self.selected_gallery_photo = None
            return
        path = current.data(Qt.UserRole)
        h = max(self.gallery_preview_label.height(), 300)
        w = max(self.gallery_preview_label.width(), 300)
        pixmap = QPixmap(path).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.gallery_preview_label.setPixmap(pixmap)
        self.selected_gallery_photo = path
        self.print_selected_button.setEnabled(True)
        # enable copies selector
        try:
            self.gallery_copies_value_label.setText(self.gallery_copies_value_label.text())
        except Exception:
            pass
        self.set_status(f"Photo : {Path(path).name}")

    def print_selected_photo(self):
        if not self.selected_gallery_photo:
            self.set_status("Aucune photo selectionnee.", error=True)
            return
        try:
            try:
                copies = int(self.gallery_copies_value_label.text())
            except Exception:
                copies = 1
            copies = max(1, min(3, copies))
            for i in range(copies):
                self.print_agent.print_photo(self.selected_gallery_photo)
            self.set_status(f"Impression envoyee : {Path(self.selected_gallery_photo).name} ({copies}x)")
        except Exception as error:
            self.set_status(f"Impossible d'imprimer : {error}", error=True)

    def _show_review(self, photo_path: str):
        """Display the large integrated review panel for the recently taken photo."""
        if not photo_path:
            return
        # Resize review widget to occupy most of the window
        rw = int(self.width() * 0.88)
        rh = int(self.height() * 0.82)
        self.review_widget.setFixedSize(rw, rh)
        self.review_widget.move((self.width() - rw) // 2, (self.height() - rh) // 2)

        pixmap = QPixmap(photo_path)
        # Allocate about 72% of review widget width to image area
        img_w = int(self.review_widget.width() * 0.72)
        img_h = int(self.review_widget.height() * 0.9)
        pm = pixmap.scaled(img_w, img_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.review_image_label.setPixmap(pm)
        self.review_image_label.setText("")
        self.review_widget.setVisible(True)
        self.review_widget.raise_()
        # Disable main controls while reviewing
        self.capture_button.setEnabled(False)
        self.gallery_button.setEnabled(False)
        self.settings_button.setEnabled(False)

    def _hide_review(self):
        self.review_widget.setVisible(False)
        self.review_image_label.setPixmap(QPixmap())
        self.review_image_label.setText("Apercu")
        self.capture_button.setEnabled(True)
        self.gallery_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self.set_status("Apercu ferme.")

    def resizeEvent(self, event):
        # Reposition and resize review widget when main window resizes
        try:
            if hasattr(self, 'review_widget') and self.review_widget.isVisible():
                rw = int(self.width() * 0.88)
                rh = int(self.height() * 0.82)
                self.review_widget.setFixedSize(rw, rh)
                self.review_widget.move((self.width() - rw) // 2, (self.height() - rh) // 2)
                # rescale displayed image
                if self.last_saved_photo:
                    pixmap = QPixmap(self.last_saved_photo)
                    img_w = int(self.review_widget.width() * 0.72)
                    img_h = int(self.review_widget.height() * 0.9)
                    pm = pixmap.scaled(img_w, img_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.review_image_label.setPixmap(pm)
        except Exception:
            pass
        super().resizeEvent(event)

    def _print_review_photo(self):
        """Print the reviewed photo the selected number of times (max 3)."""
        if not self.last_saved_photo:
            self.set_status("Aucune photo a imprimer.", error=True)
            return
        try:
            copies = int(self.copies_value_label.text())
        except Exception:
            copies = 1
        copies = max(1, min(3, copies))
        self.review_print_button.setEnabled(False)
        try:
            for i in range(copies):
                self.print_agent.print_photo(self.last_saved_photo)
            self.set_status(f"Impression envoyee ({copies}x).")
            self._hide_review()
        except Exception as error:
            self.set_status(f"Erreur impression : {error}", error=True)
        finally:
            self.review_print_button.setEnabled(True)

    def update_corner_label(self, value):
        self.corner_label.setText(f"Arrondi photo : {value}")
        self.corner_radius = value

    def update_scale_label(self, value):
        self.scale_label.setText(f"Zoom photo : {value}%")
        self.photo_scale = value

    def update_countdown_label(self, value):
        self.countdown_label_setting.setText(f"Duree du decompte : {value}s")
        self.countdown_duration = value

    def update_output_format_label(self):
        width, height = 1280, 720
        if self.last_frame is not None:
            height, width = self.last_frame.shape[:2]
        elif hasattr(self.camera_agent, 'capture') and self.camera_agent.capture is not None:
            try:
                width = int(self.camera_agent.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.camera_agent.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            except Exception:
                pass
        self.output_format_label.setText(f"Format photo : {width} x {height}")

    def _load_background_choices(self):
        """Charge les fichiers de fond dans les listes display/files."""
        self.background_files = [""]
        self.background_display_names = ["Aucun fond"]
        for file_path in sorted(self.background_folder.glob("*.png")) + sorted(self.background_folder.glob("*.jpg")):
            self.background_files.append(str(file_path))
            self.background_display_names.append(file_path.name)

        # Overlay choices come from the same folder by default
        self.overlay_files = list(self.background_files)
        self.overlay_display_names = list(self.background_display_names)

    def load_backgrounds(self):
        """Legacy function for compatibility. Reloads backgrounds."""
        self._load_background_choices()

    def browse_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fond", str(Path.home()), "Images (*.png *.jpg *.jpeg)",
        )
        if not file_path:
            return
        target_path = self.background_folder / Path(file_path).name
        if Path(file_path).resolve() != target_path.resolve():
            try:
                import shutil
                shutil.copy(file_path, str(target_path))
            except Exception as error:
                self.set_status(f"Impossible d'ajouter le fond : {error}", error=True)
                return
        self.load_backgrounds()
        self.set_status(f"Fond ajoute : {Path(file_path).name}")

    def update_background_preview(self):
        """Update background preview based on current selection in label."""
        current_text = self.background_value_label.text()
        idx = self.background_display_names.index(current_text) if current_text in self.background_display_names else 0
        selected = self.background_files[idx] if idx < len(self.background_files) else None
        self.selected_background_path = selected if selected else None
        if selected:
            pixmap = QPixmap(selected).scaled(360, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.background_preview.setPixmap(pixmap)
            self.background_preview.setText("")
        else:
            self.background_preview.setPixmap(QPixmap())
            self.background_preview.setText("Apercu du fond")

    def update_overlay_preview(self):
        """Update overlay preview based on current selection in label."""
        current_text = self.overlay_value_label.text()
        idx = self.overlay_display_names.index(current_text) if current_text in self.overlay_display_names else 0
        selected = self.overlay_files[idx] if idx < len(self.overlay_files) else None
        self.selected_overlay_path = selected if selected else None
        if selected:
            pixmap = QPixmap(selected).scaled(360, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.overlay_preview.setPixmap(pixmap)
            self.overlay_preview.setText("")
        else:
            self.overlay_preview.setPixmap(QPixmap())
            self.overlay_preview.setText("Apercu de la superposition")

    def apply_settings(self):
        camera_index = int(self.camera_value_label.text())
        printer_name = self.printer_value_label.text()
        orientation = self.orientation_value_label.text()
        if camera_index != self.camera_agent.camera_index:
            try:
                self.camera_agent.set_camera_index(camera_index)
                self.set_status(f"Camera changee sur index {camera_index}")
            except Exception as error:
                self.set_status(f"Impossible de changer la camera : {error}", error=True)
        if printer_name and printer_name != "Aucune imprimante":
            self.print_agent.printer_name = printer_name
            self.set_status(f"Imprimante : {printer_name}")
        self.print_agent.orientation = orientation
        self.corner_radius = self.corner_slider.value()
        self.photo_scale = self.scale_slider.value()
        self.countdown_duration = self.countdown_slider.value()
        # Ensure selected background/overlay reflect current UI choices
        try:
            self.update_background_preview()
        except Exception:
            pass
        try:
            self.update_overlay_preview()
        except Exception:
            pass
        self.settings_widget.hide()
        self.overlay.panel_container.hide()

    def update_preview(self):
        try:
            frame = self.camera_agent.get_frame()
            self.last_frame = frame
            self._display_frame(frame)
        except Exception as error:
            self.overlay.preview_label.setText(f"Erreur camera : {error}")
            self.timer.stop()
            self.set_status(f"Erreur camera : {error}", error=True)

    def _display_frame(self, frame):
        rendered_image = self.photo_agent.render_photo_image(
            frame,
            background_path=self.selected_background_path,
            overlay_path=self.selected_overlay_path,
            corner_radius=self.corner_radius,
            scale_percent=self.photo_scale,
        )
        if rendered_image.mode != "RGB":
            rendered_image = rendered_image.convert("RGB")

        width, height = rendered_image.size
        data = rendered_image.tobytes("raw", "RGB")
        q_image = QImage(data, width, height, width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image).scaled(
            self.preview_label.width(),
            self.preview_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(pixmap)

    def _set_main_controls_enabled(self, enabled: bool):
        self.capture_button.setEnabled(enabled)
        self.gallery_button.setEnabled(enabled)
        self.settings_button.setEnabled(enabled)

    def capture_photo(self):
        # Déclenche une vraie prise de vue reflex en arrière-plan : la photo finale
        # provient du fichier pleine résolution de digiCamControl, pas du live view.
        if self._capture_worker is not None and self._capture_worker.isRunning():
            return
        self._set_main_controls_enabled(False)
        self.set_status("Capture en cours...")
        self._capture_worker = CaptureWorker(self.camera_agent, self)
        self._capture_worker.captured.connect(self._on_capture_ready)
        self._capture_worker.failed.connect(self._on_capture_failed)
        self._capture_worker.start()

    def _on_capture_ready(self, frame):
        try:
            self.last_saved_photo = self.photo_agent.save_photo(
                frame,
                background_path=self.selected_background_path,
                overlay_path=self.selected_overlay_path,
                corner_radius=self.corner_radius,
                scale_percent=self.photo_scale,
            )
            self.set_status(f"Photo enregistree : {self.last_saved_photo}")
            # _show_review garde les contrôles principaux désactivés pendant l'aperçu
            self._show_review(self.last_saved_photo)
        except Exception as error:
            self._set_main_controls_enabled(True)
            self.set_status(f"Impossible d'enregistrer : {error}", error=True)

    def _on_capture_failed(self, message):
        self._set_main_controls_enabled(True)
        self.set_status(f"Erreur capture : {message}", error=True)

    def print_last_photo(self):
        if not self.last_saved_photo:
            self.set_status("Aucune photo a imprimer.", error=True)
            return
        try:
            self.print_agent.print_photo(self.last_saved_photo)
            self.set_status("Impression envoyee.")
        except Exception as error:
            self.set_status(f"Impossible d'imprimer : {error}", error=True)

    def start_capture_countdown(self, checked=False):
        if self.countdown_timer.isActive():
            return
        self.countdown_seconds = self.countdown_duration
        self.capture_button.setEnabled(False)
        self.gallery_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.countdown_label.setText(str(self.countdown_seconds))
        self.countdown_label.setVisible(True)
        self.set_status(f"Photo dans {self.countdown_seconds}s...")
        self.countdown_timer.start(1000)

    def _countdown_tick(self):
        self.countdown_seconds -= 1
        if self.countdown_seconds > 0:
            self.countdown_label.setText(str(self.countdown_seconds))
            self.set_status(f"Photo dans {self.countdown_seconds}s...")
            return
        self.countdown_timer.stop()
        self.countdown_label.setVisible(False)
        self.capture_button.setEnabled(True)
        self.gallery_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self.capture_photo()

    def set_status(self, text, error=False):
        if error:
            color, bg = DANGER, "rgba(224,92,92,0.12)"
        else:
            color, bg = SUCCESS, "rgba(77,217,172,0.10)"
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 15px; padding: 6px 16px;"
            f"background: {bg}; border-radius: 10px;"
        )
        self.status_label.setText(text)

    def closeEvent(self, event):
        if self._capture_worker is not None and self._capture_worker.isRunning():
            self._capture_worker.wait(3000)
        self.camera_agent.release()
        event.accept()
