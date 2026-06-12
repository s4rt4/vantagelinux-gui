"""Shared page scaffolding: a scrollable page with a large light-weight title."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea,
                             QVBoxLayout, QWidget)


class Page(QWidget):
    """Base page: optional title + a vertical content column inside a scroll area.

    Subclasses add widgets via `self.content.addWidget(...)`.
    """

    def __init__(self, title: str | None = None, max_width: int = 980, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        host_layout = QHBoxLayout(host)
        host_layout.setContentsMargins(48, 28, 48, 40)

        column = QWidget()
        column.setMaximumWidth(max_width)
        self.content = QVBoxLayout(column)
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(20)

        if title is not None:
            heading = QLabel(title)
            heading.setProperty("class", "pageTitle")
            self.content.addWidget(heading)

        host_layout.addWidget(column, 1)
        host_layout.addStretch(0)


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("class", "sectionTitle")
    return label
