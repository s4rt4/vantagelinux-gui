"""Reusable surface widgets: rounded Card, status Pill, and a copyable row."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget)

from ..theme import C
from .icon import IconButton, SvgIcon
from .toggle import ToggleSwitch


class Card(QFrame):
    """A rounded dark panel. Optionally shows a title row with a `...` menu.

    Use `.body` as the parent/layout target for content, or call
    `add(widget)` to append into the built-in vertical body layout.
    """

    def __init__(self, title: str | None = None, menu: bool = False, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        if title is not None:
            header = QHBoxLayout()
            header.setContentsMargins(0, 0, 0, 0)
            label = QLabel(title)
            label.setProperty("class", "cardTitle")
            header.addWidget(label)
            header.addStretch(1)
            if menu:
                header.addWidget(_DotsMenu())
            outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(12)
        outer.addLayout(self.body)

    def add(self, widget: QWidget, **kw) -> None:
        self.body.addWidget(widget, **kw)


class _DotsMenu(QLabel):
    """Static three-dot overflow affordance (visual only in the mockup)."""

    def __init__(self, parent=None):
        super().__init__("•••", parent)
        self.setProperty("class", "dots")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class Pill(QLabel):
    """Small rounded status badge: Good (green) / High (orange) / Expired (red)."""

    TONES = {"good": C.GREEN, "high": C.ORANGE, "bad": C.RED}

    def __init__(self, text: str, tone: str = "good", parent=None):
        super().__init__(text, parent)
        color = self.TONES.get(tone, C.GREEN)
        self.setProperty("class", "pill")
        self.setStyleSheet(
            f"background:{color}33; color:{color}; border-radius:11px;"
            f"padding:3px 12px; font-weight:600;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


def _to_clipboard(text: str) -> None:
    from PyQt6.QtWidgets import QApplication
    QApplication.clipboard().setText(text)


class CopyRow(QWidget):
    """A label/value row whose trailing icon copies the value to the clipboard."""

    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = value
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        lbl = QLabel(label)
        lbl.setProperty("class", "rowLabel")
        lbl.setFixedWidth(140)
        val = QLabel(value)
        val.setProperty("class", "rowValue")

        self._btn = IconButton("copy", color=C.TEXT_DIM, size=15, box=24)
        self._btn.setToolTip("Copy")
        self._btn.clicked.connect(self._copy)
        row.addWidget(lbl)
        row.addWidget(val, 1)
        row.addWidget(self._btn)

    def _copy(self) -> None:
        _to_clipboard(self._value)
        self._btn.setToolTip("Copied!")

    def pair(self) -> tuple[str, str]:
        return self._label, self._value


class RevealRow(QWidget):
    """Like CopyRow, but a hidden value (e.g. serial) revealed on demand.

    `fetch` is a no-arg callable returning the real value (str) or None. It may
    block briefly (e.g. a pkexec/dmidecode call), so it runs on click only.
    """

    def __init__(self, label: str, value: str, fetch, parent=None):
        super().__init__(parent)
        self._fetch = fetch
        self._label = label
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        lbl = QLabel(label)
        lbl.setProperty("class", "rowLabel")
        lbl.setFixedWidth(140)
        self._val = QLabel(value)
        self._val.setProperty("class", "rowValue")
        row.addWidget(lbl)
        row.addWidget(self._val, 1)

        self._reveal = QLabel("Reveal")
        self._reveal.setProperty("class", "link")
        self._reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reveal.mousePressEvent = lambda _e: self._on_reveal()
        self._copy = IconButton("copy", color=C.TEXT_DIM, size=15, box=24)
        self._copy.setToolTip("Copy")
        self._copy.clicked.connect(self._on_copy)
        self._copy.setVisible(False)
        hidden = value in ("—", "", None)
        self._reveal.setVisible(hidden)
        self._copy.setVisible(not hidden)
        row.addWidget(self._reveal)
        row.addWidget(self._copy)

    def _on_reveal(self) -> None:
        self._reveal.setText("…")
        val = self._fetch()
        if val:
            self._val.setText(val)
            self._reveal.setVisible(False)
            self._copy.setVisible(True)
        else:
            self._reveal.setText("Unavailable")

    def _on_copy(self) -> None:
        _to_clipboard(self._val.text())
        self._copy.setToolTip("Copied!")

    def pair(self) -> tuple[str, str]:
        return self._label, self._val.text()


class ToggleRow(QWidget):
    """A title + optional description on the left, a ToggleSwitch on the right."""

    def __init__(self, title: str, desc: str = "", checked: bool = False,
                 on_toggle=None, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "rowTitle")
        left.addWidget(title_lbl)
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setProperty("class", "muted")
            desc_lbl.setWordWrap(True)
            left.addWidget(desc_lbl)
        row.addLayout(left, 1)

        self.toggle = ToggleSwitch(checked)
        if on_toggle is not None:
            self.toggle.toggled.connect(on_toggle)
        row.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignTop)
