"""Segmented radio-card control (e.g. keyboard backlight: Low / High / Off)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QRadioButton,
                             QWidget)


class _SegmentCard(QRadioButton):
    """A single selectable card; styled as a radio with a label via QSS."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "segment")


class SegmentedControl(QWidget):
    """Row of mutually-exclusive cards. Emits `changed(index)` on selection."""

    changed = pyqtSignal(int)

    def __init__(self, options: list[str], selected: int = 0, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._group = QButtonGroup(self)
        for i, text in enumerate(options):
            card = _SegmentCard(text)
            card.setChecked(i == selected)
            self._group.addButton(card, i)
            layout.addWidget(card)
        layout.addStretch(1)
        self._group.idClicked.connect(self.changed.emit)

    def selected_index(self) -> int:
        return self._group.checkedId()
