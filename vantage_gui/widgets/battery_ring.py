"""Circular battery/percentage ring, as seen on the Vantage Home dashboard."""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..theme import C


class BatteryRing(QWidget):
    """A donut progress ring with a centered percentage label."""

    def __init__(self, percent: int = 71, ring: str = C.ACCENT_FILL,
                 diameter: int = 130, center_text: str | None = None, parent=None):
        super().__init__(parent)
        self._percent = percent
        self._ring = ring
        self._d = diameter
        self._center_text = center_text  # overrides the "NN%" label when set
        self.setFixedSize(diameter, diameter)

    def set_percent(self, percent: int) -> None:
        self._percent = max(0, min(100, percent))
        self.update()

    def set_center_text(self, text: str) -> None:
        self._center_text = text
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        thickness = 9
        margin = thickness / 2 + 1
        rect = QRectF(margin, margin, self._d - margin * 2, self._d - margin * 2)

        # track
        p.setPen(QPen(QColor("#33ffffff"), thickness, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 0, 360 * 16)

        # progress (starts at top, clockwise)
        p.setPen(QPen(QColor(self._ring), thickness, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        span = int(-self._percent / 100 * 360 * 16)
        p.drawArc(rect, 90 * 16, span)

        # centered percentage
        p.setPen(QColor(C.TEXT))
        font = QFont(self.font())
        text = self._center_text if self._center_text is not None else f"{self._percent}%"
        font.setPointSize(16 if self._center_text else 20)
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        p.end()
