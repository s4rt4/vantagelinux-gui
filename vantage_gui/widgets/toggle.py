"""An iOS/Fluent-style animated toggle switch, matching Vantage toggles."""
from __future__ import annotations

from PyQt6.QtCore import (QEasingCurve, QPropertyAnimation, QRectF, Qt,
                          pyqtProperty, pyqtSignal)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QAbstractButton

from ..theme import C


class ToggleSwitch(QAbstractButton):
    """Checkable pill switch. `toggled(bool)` fires on user interaction."""

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._w, self._h, self._pad = 44, 24, 3
        self.setFixedSize(self._w, self._h)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._animate)

    # animated knob position, 0.0 (off) .. 1.0 (on)
    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = pyqtProperty(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, _event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        radius = self._h / 2
        track_on = QColor(C.ACCENT_FILL)
        track_off = QColor("#3a3a3a")
        track = QColor(track_on)
        # interpolate track color by offset for a smooth on/off blend
        track.setRed(int(track_off.red() + (track_on.red() - track_off.red()) * self._offset))
        track.setGreen(int(track_off.green() + (track_on.green() - track_off.green()) * self._offset))
        track.setBlue(int(track_off.blue() + (track_on.blue() - track_off.blue()) * self._offset))
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, self._w, self._h), radius, radius)

        knob_d = self._h - self._pad * 2
        travel = self._w - knob_d - self._pad * 2
        x = self._pad + travel * self._offset
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, self._pad, knob_d, knob_d))
        p.end()
