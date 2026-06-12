"""Application entry point: build the QApplication, load fonts + QSS, show window."""
from __future__ import annotations

import sys

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from .theme import FONT_STACK, ROOT, icon_pixmap
from .window import VantageWindow


def _load_stylesheet() -> str:
    qss = ROOT / "vantage_gui" / "style" / "vantage.qss"
    return qss.read_text() if qss.exists() else ""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Lenovo Vantage")
    # associate with the installed vantage.desktop so the dock/taskbar shows our icon
    app.setDesktopFileName("vantage")
    app.setWindowIcon(QIcon(icon_pixmap("logo", color=None, size=64)))

    # apply the preferred font stack (Segoe UI first, with Linux fallbacks)
    font = QFont()
    font.setFamilies(FONT_STACK)
    font.setPointSize(10)
    app.setFont(font)

    app.setStyleSheet(_load_stylesheet())

    window = VantageWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
