"""A horizontal gradient meter bar (battery health, temperature)."""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import QWidget


class MeterBar(QWidget):
    """Rounded bar filled to `value` (0..1) with a multi-stop gradient.

    `stops` is a list of (position 0..1, hex color). The unfilled remainder is
    drawn as a faint track.
    """

    def __init__(self, value: float, stops, height: int = 12, parent=None):
        super().__init__(parent)
        self._value = max(0.0, min(1.0, value))
        self._stops = stops
        self._h = height
        self.setFixedHeight(height)
        self.setMinimumWidth(120)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self._h
        radius = h / 2

        # faint full-width track
        p.setBrush(QColor("#2a2a2a"))
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # gradient fill clipped to value fraction
        grad = QLinearGradient(0, 0, w, 0)
        for pos, color in self._stops:
            grad.setColorAt(pos, QColor(color))
        fill_w = max(h, w * self._value)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(0, 0, fill_w, h), radius, radius)
        p.end()
