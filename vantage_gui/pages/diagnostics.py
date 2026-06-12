"""Device diagnostics — secondary nav column (Hardware scan / System insights /
Thermal monitor / History / Advanced), mirroring the real Vantage layout.

Thermal monitor is wired to live sensors (hwmon + nvidia-smi via backend.thermals);
the other sub-pages are faithful static shells for now — we will decide later which
become real on Linux, which get replaced, and which are dropped.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QStackedWidget,
                             QVBoxLayout, QWidget)

from .. import backend
from ..theme import C
from ..widgets.battery_ring import BatteryRing
from ..widgets.cards import Card, Pill
from ..widgets.icon import SvgIcon
from ..widgets.nav import SubNav
from ..widgets.segmented import SegmentedControl

SUB_NAV = [
    ("hardware", "target", "Hardware scan"),
    ("insights", "refresh-cw", "System insights"),
    ("thermal", "thermometer", "Thermal monitor"),
    ("history", "history", "History"),
    ("advanced", "wrench", "Advanced"),
]


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "muted")
    lbl.setWordWrap(True)
    return lbl


def _title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "cardTitle")
    return lbl


def _hrule() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setProperty("class", "rule")
    line.setFixedHeight(1)
    return line


def _primary_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("class", "primaryPill")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _kv_row(label: str, value: str, pill=None) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 6, 0, 6)
    lbl = QLabel(label)
    lbl.setProperty("class", "rowTitle")
    lbl.setFixedWidth(260)
    lbl.setWordWrap(True)
    val = QLabel(value)
    val.setProperty("class", "muted")
    val.setWordWrap(True)
    row.addWidget(lbl)
    row.addWidget(val, 1)
    if pill is not None:
        row.addWidget(Pill(pill[0], pill[1]), 0, Qt.AlignmentFlag.AlignTop)
    return w


class DiagnosticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._unit_f = False              # False = °C, True = °F
        self._rings: list[tuple[BatteryRing, int]] = []
        self._avg = None
        self._avg_c = 0.0

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        left = QWidget()
        left.setFixedWidth(300)
        left_col = QVBoxLayout(left)
        left_col.setContentsMargins(40, 28, 20, 28)
        left_col.setSpacing(20)
        heading = QLabel("Device diagnostics")
        heading.setProperty("class", "pageTitle")
        left_col.addWidget(heading)
        self.nav = SubNav(SUB_NAV)
        left_col.addWidget(self.nav)
        left_col.addStretch(1)
        root.addWidget(left)

        self.stack = QStackedWidget()
        self._pages = {
            "hardware": self._hardware_page(),
            "insights": self._insights_page(),
            "thermal": self._thermal_page(),
            "history": self._history_page(),
            "advanced": self._advanced_page(),
        }
        self._order = [k for k, _i, _t in SUB_NAV]
        for key in self._order:
            self.stack.addWidget(self._scrollable(self._pages[key]))
        root.addWidget(self.stack, 1)

        self.nav.selected.connect(self._show)
        self.nav.select("thermal")

    # ------------------------------------------------------------- helpers
    def _scrollable(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        return scroll

    def _show(self, key: str) -> None:
        self.stack.setCurrentIndex(self._order.index(key))

    def _shell(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        host = QWidget()
        outer = QHBoxLayout(host)
        outer.setContentsMargins(8, 28, 48, 40)
        column = QWidget()
        column.setMaximumWidth(1000)
        col = QVBoxLayout(column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(18)
        h = QLabel(title)
        h.setProperty("class", "pageHeading")
        col.addWidget(h)
        outer.addWidget(column, 1)
        outer.addStretch(0)
        return host, col

    # --------------------------------------------------------- thermal monitor
    @staticmethod
    def _fmt(c: float, as_f: bool, decimals: int = 0) -> str:
        val = c * 9 / 5 + 32 if as_f else c
        unit = "°F" if as_f else "°C"
        return f"{val:.{decimals}f}{unit}"

    def _thermal_page(self) -> QWidget:
        avg, sensors = backend.thermals()
        self._avg_c = avg
        host, col = self._shell("Thermal monitor")

        # --- System overview (avg + °C/°F unit toggle) ---
        overview = Card()
        head = QHBoxLayout()
        hcol = QVBoxLayout()
        hcol.setSpacing(4)
        hcol.addWidget(_title("System overview"))
        hcol.addWidget(_muted("Monitor your hardware components in real-time."))
        head.addLayout(hcol, 1)
        unit_box = QHBoxLayout()
        unit_box.setSpacing(10)
        ulabel = QLabel("Temperature unit")
        ulabel.setProperty("class", "muted")
        unit_box.addWidget(ulabel)
        unit = SegmentedControl(["°C", "°F"], 0)
        unit.changed.connect(self._set_unit)
        unit_box.addWidget(unit)
        head.addLayout(unit_box, 0)
        overview.body.addLayout(head)

        avg_box = QWidget()
        avg_box.setProperty("class", "innerBox")
        ar = QHBoxLayout(avg_box)
        ar.setContentsMargins(20, 16, 20, 16)
        ar.addWidget(SvgIcon("thermometer", C.ACCENT, 30))
        ac = QVBoxLayout()
        ac.setSpacing(2)
        ac.addWidget(_muted("Average Temperature"))
        self._avg = QLabel(self._fmt(avg, False, 1))
        self._avg.setProperty("class", "bigStat")
        ac.addWidget(self._avg)
        ar.addLayout(ac)
        ar.addStretch(1)
        overview.body.addWidget(avg_box)
        col.addWidget(overview)

        # --- Hardware monitoring (per-component rings) ---
        mon = Card()
        mhead = QHBoxLayout()
        mhead.addWidget(_title("Hardware monitoring"), 1)
        refresh = QLabel("Refresh")
        refresh.setProperty("class", "link")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.mousePressEvent = lambda _e: self._refresh_thermals()
        mhead.addWidget(SvgIcon("refresh-cw", C.ACCENT, 16))
        mhead.addWidget(refresh)
        mon.body.addLayout(mhead)
        mon.body.addWidget(_hrule())

        # group consecutive sensors by their `group` label
        groups: list[tuple[str, str, list]] = []
        for s in sensors:
            if not groups or groups[-1][0] != s.group:
                groups.append((s.group, s.icon, []))
            groups[-1][2].append(s)
        subtitle = {
            "Processor CPU": "Monitor CPU temperature",
            "GPU": "Check GPU temperature",
            "Disk": "Monitor disk temperature",
        }
        for i, (group, icon, items) in enumerate(groups):
            if i:
                mon.body.addWidget(_hrule())
            ghead = QHBoxLayout()
            ghead.setSpacing(12)
            ghead.addWidget(SvgIcon(icon, C.TEXT, 26), 0, Qt.AlignmentFlag.AlignVCenter)
            gcol = QVBoxLayout()
            gcol.setSpacing(0)
            gt = QLabel(group)
            gt.setProperty("class", "rowTitle")
            gcol.addWidget(gt)
            gcol.addWidget(_muted(subtitle.get(group, "Monitor temperature")))
            ghead.addLayout(gcol, 1)
            mon.body.addLayout(ghead)

            cards = QGridLayout()
            cards.setHorizontalSpacing(16)
            for cidx, s in enumerate(items):
                cards.addWidget(self._sensor_card(s), 0, cidx)
                cards.setColumnStretch(cidx, 1)
            if len(items) == 1:
                cards.setColumnStretch(1, 1)  # keep a single card left-anchored width
            mon.body.addLayout(cards)
        col.addWidget(mon)
        col.addStretch(1)
        return host

    def _sensor_card(self, sensor) -> QWidget:
        box = QWidget()
        box.setProperty("class", "innerBox")
        v = QVBoxLayout(box)
        v.setContentsMargins(16, 24, 16, 20)
        v.setSpacing(14)
        ring = BatteryRing(min(sensor.temp_c, 100), C.ACCENT, 150,
                           center_text=self._fmt(sensor.temp_c, self._unit_f))
        self._rings.append([ring, sensor.temp_c])
        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(ring)
        wrap.addStretch(1)
        v.addLayout(wrap)
        name = QLabel(sensor.name)
        name.setProperty("class", "muted")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        v.addWidget(name)
        return box

    def _set_unit(self, index: int) -> None:
        self._unit_f = index == 1
        if self._avg is not None:
            self._avg.setText(self._fmt(self._avg_c, self._unit_f, 1))
        for ring, temp_c in self._rings:
            ring.set_center_text(self._fmt(temp_c, self._unit_f))

    def _refresh_thermals(self) -> None:
        """Re-read live sensors and update the avg label + each ring in place."""
        avg, sensors = backend.thermals()
        self._avg_c = avg
        if self._avg is not None:
            self._avg.setText(self._fmt(avg, self._unit_f, 1))
        for (entry, sensor) in zip(self._rings, sensors):
            ring = entry[0]
            entry[1] = sensor.temp_c
            ring.set_percent(min(sensor.temp_c, 100))
            ring.set_center_text(self._fmt(sensor.temp_c, self._unit_f))

    # ------------------------------------------------------- other sub-pages
    def _scan_shell(self, title: str, desc_widget: QWidget,
                    button: str) -> QWidget:
        """A header card with an action button, used by Hardware scan / insights."""
        host, col = self._shell(title)
        card = Card()
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(_primary_btn(button))
        card.body.addLayout(row)
        card.body.addWidget(_hrule())
        card.body.addWidget(desc_widget)
        col.addWidget(card)
        col.addStretch(1)
        return host, col, card

    def _hardware_page(self) -> QWidget:
        host, col = self._shell("Hardware scan")
        # Quick scan / Manual tests tabs
        tabs = SegmentedControl(["Quick scan", "Manual tests"], 0)
        col.addWidget(tabs)

        action = Card()
        ar = QHBoxLayout()
        lbl = QLabel("Quick scan")
        lbl.setProperty("class", "rowTitle")
        ar.addWidget(lbl)
        ar.addStretch(1)
        custom = QPushButton("Custom")
        custom.setProperty("class", "ghostPill")
        custom.setCursor(Qt.CursorShape.PointingHandCursor)
        ar.addWidget(custom)
        ar.addWidget(_primary_btn("Scan"))
        action.body.addLayout(ar)
        col.addWidget(action)

        comp = Card(title="Hardware components")
        comp.body.addWidget(_hrule())
        self._comp_box = QVBoxLayout()
        self._comp_box.setSpacing(0)
        comp.body.addLayout(self._comp_box)
        self._populate_components()
        col.addWidget(comp)
        col.addStretch(1)

        # the Scan button re-enumerates components
        for btn in action.findChildren(QPushButton):
            if btn.text() == "Scan":
                btn.clicked.connect(self._populate_components)
        return host

    def _populate_components(self) -> None:
        while self._comp_box.count():
            item = self._comp_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for c in backend.hardware_components():
            row = QWidget()
            r = QHBoxLayout(row)
            r.setContentsMargins(0, 8, 0, 8)
            grp = QLabel(c.group)
            grp.setProperty("class", "rowTitle")
            grp.setFixedWidth(120)
            nm = QLabel(c.name)
            nm.setProperty("class", "muted")
            nm.setWordWrap(True)
            r.addWidget(grp)
            r.addWidget(nm, 1)
            r.addWidget(Pill(c.status, "good"), 0, Qt.AlignmentFlag.AlignTop)
            self._comp_box.addWidget(row)

    def _insights_page(self) -> QWidget:
        host, col = self._shell("System insights")
        action = Card()
        ar = QHBoxLayout()
        ar.addWidget(_muted("Check system services and logs for problems."), 1)
        btn = _primary_btn("Run check")
        btn.clicked.connect(self._run_insights)
        ar.addWidget(btn)
        action.body.addLayout(ar)
        col.addWidget(action)

        card = Card(title="System health")
        self._insights_box = QVBoxLayout()
        self._insights_box.setSpacing(0)
        card.body.addLayout(self._insights_box)
        col.addWidget(card)
        col.addStretch(1)
        self._run_insights()
        return host

    def _run_insights(self) -> None:
        while self._insights_box.count():
            item = self._insights_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        h = backend.system_health()
        n = len(h.failed_services or [])
        self._insights_box.addWidget(_kv_row(
            "Failed services", str(n),
            ("Good", "good") if n == 0 else ("Issues", "bad")))
        if h.failed_services:
            self._insights_box.addWidget(_muted("   " + ", ".join(h.failed_services)))
        self._insights_box.addWidget(_kv_row(
            "Errors logged this boot", str(h.error_count),
            ("Good", "good") if h.error_count == 0 else ("High", "high")))

    def _history_page(self) -> QWidget:
        host, col = self._shell("History")

        boots = Card(title="Boot history")
        for label, when in backend.boot_history():
            boots.body.addWidget(_kv_row(label, when))
        col.addWidget(boots)

        pkgs = Card(title="Recently updated packages")
        ph = backend.package_history()
        if ph:
            for name, when in ph:
                pkgs.body.addWidget(_kv_row(name, when))
        else:
            pkgs.body.addWidget(_muted("No package history available."))
        col.addWidget(pkgs)
        col.addStretch(1)
        return host

    def _advanced_page(self) -> QWidget:
        host, col = self._shell("Advanced")
        card = Card()
        card.body.addWidget(_muted("Advanced diagnostic tools and bootable test "
                                   "options will be available here."))
        col.addWidget(card)
        col.addStretch(1)
        return host
