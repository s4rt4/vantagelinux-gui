"""Home dashboard: device card, battery ring, warranty, support tiles, promo."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from .. import backend
from ..theme import C, icon_pixmap
from ..widgets.battery_ring import BatteryRing
from ..widgets.cards import Card, CopyRow, RevealRow
from ..widgets.icon import SvgIcon
from .common import Page


def _link(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "link")
    lbl.setCursor(Qt.CursorShape.PointingHandCursor)
    return lbl


class HomePage(Page):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        info = backend.device_info()
        batt = backend.battery()

        # title row with a primary "Check for updates" pill on the right
        title_row = QHBoxLayout()
        heading = QLabel("Home")
        heading.setProperty("class", "pageTitle")
        update_btn = QPushButton("  Check for updates")
        update_btn.setProperty("class", "primaryPill")
        update_btn.setIcon(QIcon(icon_pixmap("system-update", "#0a2a3f", 16)))
        update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        title_row.addWidget(heading)
        title_row.addStretch(1)
        title_row.addWidget(update_btn)
        self.content.addLayout(title_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.addWidget(self._device_card(info), 0, 0, 1, 2)
        grid.addWidget(self._battery_card(batt), 0, 2)
        grid.addWidget(self._warranty_card(info), 0, 3)
        grid.addWidget(self._support_card(), 1, 0, 1, 2)
        grid.addWidget(self._promo_card(), 1, 2, 1, 2)
        for col in range(4):
            grid.setColumnStretch(col, 1)
        self.content.addLayout(grid)
        self.content.addStretch(1)

    # ------------------------------------------------------------------ cards
    def _device_card(self, info: backend.DeviceInfo) -> Card:
        card = Card(title=info.name, menu=True)
        row = QHBoxLayout()
        row.setSpacing(18)

        illo = SvgIcon("laptop-illustrations", color=None, size=120)
        row.addWidget(illo, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(8)
        rows = [
            RevealRow("Serial number", info.serial_number, backend.reveal_serial),
            CopyRow("Product number", info.product_number),
            CopyRow("Bios version", info.bios_version),
        ]
        for r in rows:
            col.addWidget(r)
        copy_all = QHBoxLayout()
        copy_all.addStretch(1)
        link = _link("Copy all")
        link.mousePressEvent = lambda _e: self._copy_all(rows, link)
        copy_all.addWidget(link)
        copy_all.addWidget(SvgIcon("copy", C.ACCENT, 15))
        col.addLayout(copy_all)
        row.addLayout(col, 1)

        card.body.addLayout(row)
        return card

    @staticmethod
    def _copy_all(rows, link=None) -> None:
        from PyQt6.QtWidgets import QApplication
        text = "\n".join(f"{lbl}: {val}" for lbl, val in (r.pair() for r in rows))
        QApplication.clipboard().setText(text)
        if link is not None:
            link.setText("Copied!")

    def _battery_card(self, batt: backend.Battery) -> Card:
        card = Card(title="Battery", menu=True)
        self._batt_ring = BatteryRing(batt.percent, C.ACCENT_FILL, 130)
        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(self._batt_ring)
        wrap.addStretch(1)
        self._batt_status = QLabel("")
        self._batt_status.setProperty("class", "rowTitle")
        self._batt_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._batt_caption = QLabel("")
        self._batt_caption.setProperty("class", "muted")
        self._batt_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.body.addLayout(wrap)
        card.body.addWidget(self._batt_status)
        card.body.addWidget(self._batt_caption)

        self._refresh_battery()
        timer = QTimer(self)
        timer.timeout.connect(self._refresh_battery)
        timer.start(5000)  # keep the dashboard battery live
        return card

    def _refresh_battery(self) -> None:
        batt = backend.battery()
        self._batt_ring.set_percent(batt.percent)
        self._batt_ring.set_center_text(f"{batt.percent}%")
        charging = batt.adapter == "Plugged in"
        self._batt_status.setText("Charging" if charging else "On battery")
        self._batt_caption.setText("Conservation mode on" if batt.conservation_on
                                   else "Conservation mode off")

    def _warranty_card(self, info: backend.DeviceInfo) -> Card:
        card = Card(title="Warranty", menu=True)
        ring = BatteryRing(100, C.RED, 130)
        ring.set_percent(100)
        # repurpose the ring as a status disc with centered "Expired"
        ring.setVisible(False)  # the donut % isn't meaningful here
        disc = _StatusDisc("security", "Expired", C.RED)
        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(disc)
        wrap.addStretch(1)
        caption = QHBoxLayout()
        caption.addStretch(1)
        exp = QLabel("Expired · ")
        exp.setProperty("class", "muted")
        caption.addWidget(exp)
        caption.addWidget(_link("Upgrade now"))
        caption.addStretch(1)
        card.body.addLayout(wrap)
        card.body.addLayout(caption)
        return card

    def _support_card(self) -> Card:
        card = Card(title="Support services", menu=True)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        tiles = [
            ("circle-question-mark", "Troubleshoot & diagnose"),
            ("circle-question-mark", "How to's"),
            ("briefcase-business", "Service request"),
            ("user", "Contact us"),
        ]
        for i, (icon, text) in enumerate(tiles):
            grid.addWidget(_DarkTile(icon, text), i // 2, i % 2)
        card.body.addLayout(grid)
        return card

    def _promo_card(self) -> Card:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(18)
        art = QLabel()
        art.setFixedSize(150, 120)
        art.setProperty("class", "promoArt")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setText("Premium\nCare")
        row.addWidget(art)

        col = QVBoxLayout()
        col.setSpacing(8)
        head = QLabel("10% Off on Premium Care!")
        head.setProperty("class", "cardTitle")
        sub = QLabel("Upgrade your warranty and enjoy\ncomplete peace of mind.")
        sub.setProperty("class", "muted")
        col.addWidget(head)
        col.addWidget(sub)
        learn = QHBoxLayout()
        learn.addWidget(SvgIcon("briefcase-business", C.ACCENT, 16))
        learn.addWidget(_link("Learn more"))
        learn.addStretch(1)
        col.addLayout(learn)
        col.addStretch(1)
        row.addLayout(col, 1)
        card.body.addLayout(row)
        return card


class _StatusDisc(QWidget):
    """A ringed icon disc used for the warranty status (icon + label below)."""

    def __init__(self, icon: str, label: str, color: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge = SvgIcon(icon, color, 40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel(label)
        text.setStyleSheet(f"color:{color}; font-weight:600;")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge)
        layout.addWidget(text)


class _DarkTile(QPushButton):
    """A near-black support tile: centered icon over a label."""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(78)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        ic = SvgIcon(icon, C.ACCENT, 22)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setProperty("class", "tileLabel")
        layout.addWidget(ic, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(lbl)
