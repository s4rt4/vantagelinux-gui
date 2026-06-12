"""Navigation: the collapsible left icon rail and the secondary nav column."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QButtonGroup, QLabel, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget)

from ..theme import C, icon_pixmap


class NavItem(QPushButton):
    """A checkable nav row: tinted icon + label, accent bar when selected."""

    def __init__(self, key: str, icon: str, text: str, compact: bool = False, parent=None):
        super().__init__(parent)
        self.key = key
        self._icon = icon
        self.setText("  " + text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "navItem")
        self.setIconSize(QSize(22, 22))
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setFixedHeight(48 if not compact else 44)
        self.toggled.connect(self._sync_icon)
        self._sync_icon(False)

    def _sync_icon(self, checked: bool) -> None:
        color = C.TEXT if checked else C.TEXT_DIM
        self.setIcon(QIcon(icon_pixmap(self._icon, color, 22)))

    def enterEvent(self, event):  # noqa: N802
        if not self.isChecked():
            self.setIcon(QIcon(icon_pixmap(self._icon, C.TEXT, 22)))
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._sync_icon(self.isChecked())
        super().leaveEvent(event)


class _NavList(QWidget):
    """Shared vertical, mutually-exclusive list of NavItems."""

    selected = pyqtSignal(str)

    def __init__(self, items, compact=False, parent=None):
        super().__init__(parent)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._items: dict[str, NavItem] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        for i, (key, icon, text) in enumerate(items):
            item = NavItem(key, icon, text, compact=compact)
            self._group.addButton(item, i)
            self._items[key] = item
            self._layout.addWidget(item)
            item.clicked.connect(lambda _=False, k=key: self.selected.emit(k))

    def select(self, key: str) -> None:
        if key in self._items:
            self._items[key].setChecked(True)
            self.selected.emit(key)


# Primary navigation entries (icon name, label) in Vantage order.
MAIN_NAV = [
    ("home", "home", "Home"),
    ("gaming", "gaming-settings", "Gaming settings"),
    ("device", "device-settings", "Device settings"),
    ("update", "system-update", "System update"),
    ("diagnostics", "device-diagnostics", "Device diagnostics"),
    ("security", "security", "Security"),
    ("utilities", "utilities", "Utilities"),
]
SUPPORT_NAV = ("support", "about", "App info")


class NavRail(QWidget):
    """The left rail. Collapses to icons-only (72px) or expands to show labels."""

    selected = pyqtSignal(str)
    COLLAPSED = 72
    EXPANDED = 240

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navRail")
        self._expanded = False
        self.setFixedWidth(self.COLLAPSED)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 16)
        root.setSpacing(12)

        # logo (full-color SVG; "Vantage" wordmark shown only when expanded)
        self._logo = QLabel()
        self._logo.setPixmap(icon_pixmap("logo", color=None, size=40))
        self._wordmark = QLabel("  Vantage")
        self._wordmark.setProperty("class", "wordmark")
        self._wordmark.setVisible(False)
        from PyQt6.QtWidgets import QHBoxLayout
        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(4, 0, 0, 8)
        logo_row.addWidget(self._logo)
        logo_row.addWidget(self._wordmark)
        logo_row.addStretch(1)
        root.addLayout(logo_row)

        self._main = _NavList(MAIN_NAV)
        self._main.selected.connect(self._on_select)
        root.addWidget(self._main)
        root.addStretch(1)

        self._support = _NavList([SUPPORT_NAV])
        self._support.selected.connect(self._on_select)
        root.addWidget(self._support)

        self._apply_labels()

    def _on_select(self, key: str) -> None:
        # keep the two lists mutually exclusive (support sits in its own group)
        if key == "support":
            self._main._group.setExclusive(False)
            for item in self._main._items.values():
                item.setChecked(False)
            self._main._group.setExclusive(True)
        else:
            for item in self._support._items.values():
                item.setChecked(False)
        self.selected.emit(key)

    def select(self, key: str) -> None:
        target = self._support if key == "support" else self._main
        target.select(key)

    def toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.setFixedWidth(self.EXPANDED if expanded else self.COLLAPSED)
        self._wordmark.setVisible(expanded)
        self._apply_labels()

    def _apply_labels(self) -> None:
        # In collapsed mode hide text by making the button tooltip-only.
        for nav in (self._main, self._support):
            for key, item in nav._items.items():
                full = self._label_for(key)
                if self._expanded:
                    item.setText("  " + full)
                    item.setToolTip("")
                else:
                    item.setText("")
                    item.setToolTip(full)

    @staticmethod
    def _label_for(key: str) -> str:
        for k, _icon, text in MAIN_NAV + [SUPPORT_NAV]:
            if k == key:
                return text
        return key


class SubNav(_NavList):
    """Secondary nav column used inside Device settings (Power/Display/...)."""

    def __init__(self, items, parent=None):
        super().__init__(items, compact=True, parent=parent)
        self.setProperty("class", "subnav")
