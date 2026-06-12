"""Icon helpers: a static SVG icon label and a clickable icon button."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QLabel, QPushButton

from ..theme import C, icon_pixmap


class SvgIcon(QLabel):
    """A non-interactive tinted SVG icon."""

    def __init__(self, name: str, color: str = C.TEXT_DIM, size: int = 24, parent=None):
        super().__init__(parent)
        self._name = name
        self._size = size
        self.setFixedSize(size, size)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self.setPixmap(icon_pixmap(self._name, color, self._size))


class IconButton(QPushButton):
    """A flat, square icon button that tints on hover (topbar bell/account)."""

    def __init__(self, name: str, color: str = C.TEXT_DIM,
                 hover: str = C.TEXT, size: int = 22, box: int = 40, parent=None):
        super().__init__(parent)
        self._name = name
        self._color = color
        self._hover = hover
        self._size = size
        self.setFixedSize(box, box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(size, size))
        self.setFlat(True)
        self.setProperty("class", "iconBtn")
        self._refresh(color)

    def _refresh(self, color: str) -> None:
        self.setIcon(QIcon(icon_pixmap(self._name, color, self._size)))

    def set_name(self, name: str) -> None:
        """Swap the icon glyph (e.g. toggle open/close states)."""
        self._name = name
        self._refresh(self._color)

    def enterEvent(self, event):  # noqa: N802 (Qt naming)
        self._refresh(self._hover)
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._refresh(self._color)
        super().leaveEvent(event)
