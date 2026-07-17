import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from camera_agent import CameraAgent
from photo_agent import PhotoAgent
from print_agent import PrintAgent
from ui_agent import PhotoBoothUI


def apply_dark_palette(app: QApplication) -> None:
    """Force a dark palette on all native widgets (fixes Windows 10 contrast issues)."""
    palette = QPalette()

    # Base colors
    dark_bg      = QColor(30, 30, 30)
    mid_bg       = QColor(50, 50, 50)
    light_bg     = QColor(70, 70, 70)
    text_color   = QColor(230, 230, 230)
    bright_text  = QColor(255, 255, 255)
    highlight    = QColor(90, 130, 200)
    disabled_txt = QColor(130, 130, 130)
    link_color   = QColor(100, 160, 255)

    palette.setColor(QPalette.Window,          dark_bg)
    palette.setColor(QPalette.WindowText,      text_color)
    palette.setColor(QPalette.Base,            mid_bg)
    palette.setColor(QPalette.AlternateBase,   light_bg)
    palette.setColor(QPalette.ToolTipBase,     dark_bg)
    palette.setColor(QPalette.ToolTipText,     text_color)
    palette.setColor(QPalette.Text,            text_color)
    palette.setColor(QPalette.Button,          mid_bg)
    palette.setColor(QPalette.ButtonText,      bright_text)
    palette.setColor(QPalette.BrightText,      bright_text)
    palette.setColor(QPalette.Highlight,       highlight)
    palette.setColor(QPalette.HighlightedText, bright_text)
    palette.setColor(QPalette.Link,            link_color)

    # Disabled state
    palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled_txt)
    palette.setColor(QPalette.Disabled, QPalette.Text,       disabled_txt)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_txt)
    palette.setColor(QPalette.Disabled, QPalette.Highlight,  QColor(60, 60, 60))

    app.setPalette(palette)

    # Stylesheet global : force les widgets natifs à adopter les bonnes couleurs
    # (QSlider, QComboBox, QSpinBox héritent tous de ces règles sur Windows 10)
    app.setStyleSheet("""
        QWidget {
            color: #E6E6E6;
            background-color: #1E1E1E;
            font-size: 16px;
        }

        /* --- Sliders --- */
        QSlider::groove:horizontal {
            height: 8px;
            background: #505050;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #C0C0C0;
            border: 2px solid #909090;
            width: 28px;
            height: 28px;
            margin: -10px 0;
            border-radius: 14px;
        }
        QSlider::handle:horizontal:hover {
            background: #FFFFFF;
        }
        QSlider::sub-page:horizontal {
            background: #5A82C8;
            border-radius: 4px;
        }

        /* --- ComboBox (sélection du fond, imprimante) --- */
        QComboBox {
            background-color: #323232;
            color: #E6E6E6;
            border: 1px solid #606060;
            border-radius: 8px;
            padding: 8px 12px;
            min-height: 40px;
        }
        QComboBox:hover { border-color: #8888AA; }
        QComboBox::drop-down {
            border: none;
            width: 32px;
        }
        QComboBox::down-arrow {
            width: 14px;
            height: 14px;
            image: none;
            border-left: 6px solid transparent;
            border-right: 6px solid transparent;
            border-top: 8px solid #C0C0C0;
            margin-right: 8px;
        }
        QComboBox QAbstractItemView {
            background-color: #2A2A2A;
            color: #E6E6E6;
            selection-background-color: #5A82C8;
            selection-color: #FFFFFF;
            border: 1px solid #606060;
        }

        /* --- SpinBox (index caméra) --- */
        QSpinBox {
            background-color: #323232;
            color: #E6E6E6;
            border: 1px solid #606060;
            border-radius: 8px;
            padding: 8px 12px;
            min-height: 40px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #484848;
            border: none;
            width: 28px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #606060;
        }
        QSpinBox::up-arrow {
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-bottom: 7px solid #C0C0C0;
        }
        QSpinBox::down-arrow {
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 7px solid #C0C0C0;
        }

        /* --- ScrollBar (dans la galerie / paramètres) --- */
        QScrollBar:vertical {
            background: #2A2A2A;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #606060;
            border-radius: 6px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover { background: #808080; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

        /* --- ListWidget (galerie) --- */
        QListWidget {
            background-color: #242424;
            color: #E6E6E6;
            border: 1px solid #505050;
            border-radius: 10px;
        }
        QListWidget::item:selected {
            background-color: #5A82C8;
            color: #FFFFFF;
        }
        QListWidget::item:hover {
            background-color: #3A3A3A;
        }
    """)


def main():
    try:
        camera_agent = CameraAgent(camera_index=0)
        photo_agent = PhotoAgent()
        print_agent = PrintAgent()

        app = QApplication(sys.argv)
        apply_dark_palette(app)

        window = PhotoBoothUI(camera_agent, photo_agent, print_agent)
        window.show()
        sys.exit(app.exec())
    except Exception as error:
        print(f"Erreur lors du démarrage : {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
