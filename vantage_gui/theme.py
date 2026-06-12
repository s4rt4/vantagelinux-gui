"""Design tokens + shared asset helpers for the Vantage mockup.

Colors are lifted from the real Lenovo Vantage Windows screenshots in
`assets/vantage screenshot/`. Note: the selection/active accent is Windows
BLUE, not red — red (`LENOVO_RED`) is reserved for the "L" logo only.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = ASSETS / "icons"
SHOTS = ASSETS / "vantage screenshot"


class C:
    """Color palette (hex strings)."""

    WINDOW = "#0a0a0a"        # app background, near black
    RAIL = "#1b1b1b"          # left icon rail
    CARD = "#1f1f1f"          # primary card surface
    CARD_HOVER = "#272727"
    TILE = "#141414"          # nested dark tiles (support services)
    SUBNAV_ACTIVE = "#2d2d2d"  # selected nav row background
    BORDER = "#2e2e2e"

    TEXT = "#f3f3f3"          # primary text
    TEXT_DIM = "#a0a0a0"      # secondary text
    TEXT_FAINT = "#6e6e6e"

    ACCENT = "#4cc2ff"        # link / active-text blue
    ACCENT_FILL = "#0078d4"   # filled blue (buttons, toggles on)
    ACCENT_SOFT = "#1b3a4d"   # translucent blue selection backdrop

    LENOVO_RED = "#e1251b"    # logo only

    GREEN = "#3fb950"         # "Good" pill
    ORANGE = "#d29922"        # "High" pill
    RED = "#f85149"           # "Expired" pill


# Preferred UI font stack — Segoe UI if present (matches Windows Vantage),
# otherwise fall back to common Linux sans fonts.
FONT_STACK = ["Segoe UI", "Selawik", "Cantarell", "Noto Sans", "DejaVu Sans", "sans-serif"]


def icon_pixmap(name: str, color: str | None = None, size: int = 24) -> QPixmap:
    """Render a Lucide-style SVG from assets/icons as a colored QPixmap.

    The Lucide icons use `stroke="currentColor"`; we substitute `color` for
    `currentColor` so a single SVG can be tinted per state (dim vs. accent).
    Pass color=None to render the SVG as-authored (used for the full-color logo).
    """
    path = ICONS / f"{name}.svg"
    data = path.read_bytes()
    if color is not None:
        data = data.replace(b"currentColor", color.encode())
    renderer = QSvgRenderer(QByteArray(data))

    dpr = 2  # render at 2x for crispness on hi-dpi
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm
