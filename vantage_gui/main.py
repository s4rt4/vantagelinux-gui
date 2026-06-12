"""Application entry point: build the QApplication, load fonts + QSS, show window."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from .theme import FONT_STACK, ROOT, icon_pixmap
from .window import VantageWindow


def _load_stylesheet() -> str:
    qss = ROOT / "vantage_gui" / "style" / "vantage.qss"
    return qss.read_text() if qss.exists() else ""


def _ensure_desktop_integration() -> None:
    """Register a user-level icon + .desktop so Wayland shows our dock icon.

    On Wayland the dock icon comes from the .desktop entry matched by the app
    id (set via setDesktopFileName), not from setWindowIcon. When running from
    source (not `make install`-ed), nothing is registered, so we self-register
    into ~/.local/share once. Skips if a system-wide install already exists.
    """
    try:
        data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        if not Path("/usr/share/icons/hicolor/scalable/apps/vantage.svg").exists():
            icon_dir = data / "icons/hicolor/scalable/apps"
            icon_dir.mkdir(parents=True, exist_ok=True)
            dst = icon_dir / "vantage.svg"
            src = ROOT / "assets/icons/logo.svg"
            if src.exists() and not dst.exists():
                shutil.copyfile(src, dst)
        if not Path("/usr/share/applications/vantage.desktop").exists():
            app_dir = data / "applications"
            app_dir.mkdir(parents=True, exist_ok=True)
            desktop = app_dir / "vantage.desktop"
            if not desktop.exists():
                desktop.write_text(
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Lenovo Vantage\n"
                    f"Exec=python3 {ROOT / 'vantage.py'} %f\n"
                    "Icon=vantage\n"
                    "Terminal=false\n"
                    "StartupWMClass=vantage\n"
                    "Categories=System;Settings;HardwareSettings;\n")
    except OSError:
        pass


def main() -> int:
    _ensure_desktop_integration()

    app = QApplication(sys.argv)
    app.setApplicationName("Lenovo Vantage")
    # Wayland matches this app id to vantage.desktop to resolve the dock icon
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
