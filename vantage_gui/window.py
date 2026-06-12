"""The main window: left rail + top bar + a stack of primary pages."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow, QMenu, QStackedWidget,
                             QVBoxLayout, QWidget)

from .theme import C, icon_pixmap
from .widgets.icon import IconButton
from .widgets.nav import NavRail
from .pages.home import HomePage
from .pages.device_settings import DeviceSettingsPage
from .pages.diagnostics import DiagnosticsPage
from .pages.misc import (AppInfoPage, GamingPage, SecurityPage,
                         SystemUpdatePage, UtilitiesPage)


class VantageWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lenovo Vantage")
        self.setWindowIcon(QIcon(icon_pixmap("logo", color=None, size=64)))
        self.resize(1180, 720)
        self.setMinimumSize(960, 600)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.rail = NavRail()
        self.rail.selected.connect(self._navigate)
        root.addWidget(self.rail)

        right = QWidget()
        right.setObjectName("contentArea")
        right_col = QVBoxLayout(right)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)
        right_col.addWidget(self._topbar())

        self.stack = QStackedWidget()
        self.pages = {
            "home": HomePage(),
            "gaming": GamingPage(),
            "device": DeviceSettingsPage(),
            "update": SystemUpdatePage(),
            "diagnostics": DiagnosticsPage(),
            "security": SecurityPage(),
            "utilities": UtilitiesPage(),
            "support": AppInfoPage(),
        }
        self._order = list(self.pages.keys())
        for page in self.pages.values():
            self.stack.addWidget(page)
        right_col.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        self.rail.select("home")

    def _topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topbar")
        bar.setFixedHeight(56)
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 8, 16, 8)
        row.setSpacing(8)

        self._toggle = IconButton("panel-right-open", C.TEXT, C.ACCENT, size=22)
        self._toggle.clicked.connect(self._toggle_rail)
        row.addWidget(self._toggle)
        row.addStretch(1)
        row.addWidget(IconButton("bell", C.TEXT_DIM, C.TEXT, size=21))
        account = IconButton("user", C.TEXT_DIM, C.TEXT, size=21)
        account.clicked.connect(lambda: self._account_menu(account))
        row.addWidget(account)
        return bar

    def _toggle_rail(self) -> None:
        self.rail.toggle()
        # show a "close" glyph while expanded, an "open" glyph while collapsed
        self._toggle.set_name(
            "panel-right-close" if self.rail._expanded else "panel-right-open")

    def _navigate(self, key: str) -> None:
        self.stack.setCurrentIndex(self._order.index(key))

    def _account_menu(self, anchor) -> None:
        menu = QMenu(self)
        menu.addSection("Good night, User!")
        menu.addAction("Preference settings")
        menu.addAction("About Lenovo Vantage")
        menu.addAction("Launch tutorial")
        menu.addSeparator()
        menu.addAction("Sign in")
        pos = anchor.mapToGlobal(anchor.rect().bottomRight())
        menu.exec(pos)
