"""The remaining primary pages, kept lighter than Home / Device settings."""
from __future__ import annotations

from PyQt6.QtCore import (Qt, QObject, QRunnable, QThreadPool, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QButtonGroup, QColorDialog, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                             QVBoxLayout, QWidget)

from .. import backend
from ..theme import C, icon_pixmap
from ..widgets.battery_ring import BatteryRing
from ..widgets.cards import Card, Pill, ToggleRow
from ..widgets.icon import SvgIcon
from ..widgets.meter import MeterBar
from ..widgets.segmented import SegmentedControl
from .common import Page


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "muted")
    lbl.setWordWrap(True)
    return lbl


def _kv_row(label: str, value: str) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 2, 0, 2)
    lbl = QLabel(label)
    lbl.setProperty("class", "rowTitle")
    lbl.setFixedWidth(160)
    val = QLabel(value)
    val.setProperty("class", "muted")
    row.addWidget(lbl)
    row.addWidget(val, 1)
    return w


def _primary_btn(text: str, icon: str | None = None) -> QPushButton:
    btn = QPushButton(("  " + text) if icon else text)
    btn.setProperty("class", "primaryPill")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon:
        btn.setIcon(QIcon(icon_pixmap(icon, "#0a2a3f", 16)))
    return btn


class _AsyncSignals(QObject):
    done = pyqtSignal(bool)


class _AsyncTask(QRunnable):
    """Run a blocking callable off the UI thread, emit its bool result."""

    def __init__(self, fn, signals: _AsyncSignals):
        super().__init__()
        self._fn = fn
        self._signals = signals

    def run(self):  # noqa: N802 (Qt naming)
        try:
            ok = bool(self._fn())
        except Exception:
            ok = False
        self._signals.done.emit(ok)


class BigTile(QPushButton):
    """A large utilities tile: centered icon, bold title, subtitle. Checkable."""

    def __init__(self, icon: str, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "bigTile")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(200)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)
        ic = SvgIcon(icon, C.ACCENT, 44)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setProperty("class", "cardTitle")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = QLabel(subtitle)
        s.setProperty("class", "muted")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ic, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(t)
        layout.addWidget(s)


# --------------------------------------------------------------------------- #
class UtilitiesPage(Page):
    """Two tiles (Network / Memory cleaner) that reveal a live, functional panel."""

    def __init__(self, parent=None):
        super().__init__("Utilities", parent=parent)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        self._net_tile = BigTile("wifi", "Network", "Connection status & Wi-Fi")
        self._mem_tile = BigTile("brush-cleaning", "Memory cleaner",
                                 "Optimize device memory usage")
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        grp.addButton(self._net_tile, 0)
        grp.addButton(self._mem_tile, 1)
        grid.addWidget(self._net_tile, 0, 0)
        grid.addWidget(self._mem_tile, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.content.addLayout(grid)

        self._detail = QStackedWidget()
        self._detail.addWidget(self._network_panel())
        self._detail.addWidget(self._memory_panel())
        self.content.addWidget(self._detail)
        self.content.addStretch(1)

        self._net_tile.clicked.connect(lambda: self._detail.setCurrentIndex(0))
        self._mem_tile.clicked.connect(lambda: self._detail.setCurrentIndex(1))
        self._mem_tile.setChecked(True)
        self._detail.setCurrentIndex(1)

    # -- Network panel -----------------------------------------------------
    def _network_panel(self) -> QWidget:
        card = Card(title="Network")
        self._net_rows = QVBoxLayout()
        self._net_rows.setSpacing(10)
        card.body.addLayout(self._net_rows)
        wifi = ToggleRow("Wi-Fi", "Enable or disable the wireless radio.",
                         checked=backend.network().wifi_on, on_toggle=self._toggle_wifi)
        card.body.addWidget(wifi)
        self._refresh_network()
        return card

    def _refresh_network(self) -> None:
        while self._net_rows.count():
            item = self._net_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        n = backend.network()
        for label, value in [("Connection", n.name), ("Type", n.conn_type),
                             ("IP address", n.ip)]:
            self._net_rows.addWidget(_kv_row(label, value))

    def _toggle_wifi(self, on: bool) -> None:
        backend.set_wifi(on)
        QTimer.singleShot(800, self._refresh_network)

    # -- Memory cleaner panel ---------------------------------------------
    def _memory_panel(self) -> QWidget:
        card = Card(title="Memory cleaner")
        card.body.addWidget(_muted("Free up reclaimable system memory (page cache, "
                                   "dentries and inodes)."))
        self._mem_bar = MeterBar(0.0, [(0, "#0078d4"), (1, "#4cc2ff")], 12)
        card.body.addWidget(self._mem_bar)
        self._mem_label = QLabel("")
        self._mem_label.setProperty("class", "muted")
        card.body.addWidget(self._mem_label)
        row = QHBoxLayout()
        clean = _primary_btn("Clean memory")
        clean.clicked.connect(self._clean_memory)
        row.addWidget(clean)
        row.addStretch(1)
        card.body.addLayout(row)
        self._refresh_memory()
        return card

    def _refresh_memory(self) -> None:
        m = backend.memory()
        self._mem_bar.set_value(m.used_pct / 100)
        self._mem_label.setText(
            f"{m.used_gb:.1f} GB used of {m.total_gb:.1f} GB  ·  "
            f"{m.available_gb:.1f} GB available ({m.used_pct}% used)")

    def _clean_memory(self) -> None:
        before = backend.memory().available_gb
        if backend.drop_caches():
            QTimer.singleShot(400, lambda: self._after_clean(before))

    def _after_clean(self, before: float) -> None:
        self._refresh_memory()
        freed = backend.memory().available_gb - before
        if freed > 0.05:
            self._mem_label.setText(self._mem_label.text() + f"   ✓ Freed {freed:.2f} GB")


APP_VERSION = "2.0.0"


class AppInfoPage(Page):
    """About this app: identity, version, tech stack, fork attribution."""

    def __init__(self, parent=None):
        super().__init__("App info", parent=parent)
        o = backend.os_info()

        head = Card()
        row = QHBoxLayout()
        row.setSpacing(18)
        logo = SvgIcon("logo", color=None, size=72)
        row.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        name = QLabel("Lenovo Vantage for Linux")
        name.setProperty("class", "cardTitle")
        col.addWidget(name)
        col.addWidget(_muted(f"Version {APP_VERSION}"))
        col.addWidget(_muted("A native PyQt6 control center for Lenovo laptops — "
                             "conservation mode, fan mode, Fn lock, battery health, "
                             "thermals and more, read straight from the hardware."))
        row.addLayout(col, 1)
        head.body.addLayout(row)
        self.content.addWidget(head)

        details = Card(title="About")
        for label, value in [
            ("Running on", o.name),
            ("Kernel", o.kernel),
            ("Toolkit", "PyQt6 (Qt 6)"),
            ("License", "GPL (inherited from upstream)"),
            ("Upstream", "Fork of niizam/vantage (originally bash + zenity)"),
        ]:
            details.body.addWidget(_kv_row(label, value))
        self.content.addWidget(details)

        links = Card(title="Resources")
        for text in ["Project repository", "Report an issue", "lucide.dev (icons)"]:
            link = QLabel(text)
            link.setProperty("class", "link")
            link.setCursor(Qt.CursorShape.PointingHandCursor)
            links.body.addWidget(link)
        self.content.addWidget(links)
        self.content.addStretch(1)


# --------------------------------------------------------------------------- #
class SystemUpdatePage(Page):
    def __init__(self, parent=None):
        super().__init__("System update", parent=parent)
        os_info = backend.os_info()

        hero = Card()
        inner = QWidget()
        inner.setProperty("class", "heroInner")
        row = QHBoxLayout(inner)
        row.setContentsMargins(24, 24, 24, 24)
        row.setSpacing(24)
        art = SvgIcon("system-update", C.ACCENT, 90)
        row.addWidget(art, 0, Qt.AlignmentFlag.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(10)
        head = QLabel("An up-to-date system is a healthy system")
        head.setProperty("class", "cardTitle")
        col.addWidget(head)
        col.addWidget(_muted(f"{os_info.name}\nKernel {os_info.kernel}\n"
                             f"Last package update: {os_info.last_update}"))
        self._status = QLabel("")
        self._status.setProperty("class", "muted")
        col.addWidget(self._status)
        btn_row = QHBoxLayout()
        self._check_btn = _primary_btn("Check for updates")
        self._check_btn.clicked.connect(self._check_updates)
        btn_row.addWidget(self._check_btn)
        btn_row.addStretch(1)
        col.addLayout(btn_row)
        row.addLayout(col, 1)
        hero.body.addWidget(inner)
        self.content.addWidget(hero)

        auto = Card()
        ar = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(8)
        t = QLabel("Update content")
        t.setProperty("class", "cardTitle")
        left.addWidget(t)
        left.addWidget(_muted("Updates are delivered by your distribution's package "
                              "manager. Use 'Check for updates' to query the cache for "
                              "available package upgrades."))
        left.addStretch(1)
        ar.addLayout(left, 1)
        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(ToggleRow("System packages", checked=True))
        right.addWidget(ToggleRow("Firmware (fwupd)", checked=True))
        ar.addLayout(right, 1)
        auto.body.addLayout(ar)
        self.content.addWidget(auto)
        self.content.addStretch(1)

    def _check_updates(self) -> None:
        self._check_btn.setEnabled(False)
        self._status.setText("Checking the package cache…")
        # let the label paint before the (brief) blocking query
        QTimer.singleShot(50, self._run_update_check)

    def _run_update_check(self) -> None:
        n = backend.update_count()
        if n is None:
            self._status.setText("Could not determine available updates.")
        elif n == 0:
            self._status.setText("✓ Your system is up to date.")
        else:
            self._status.setText(f"{n} package update(s) available.")
        self._check_btn.setEnabled(True)


# --------------------------------------------------------------------------- #
class SecurityPage(Page):
    def __init__(self, parent=None):
        super().__init__("Security", parent=parent)
        checks = backend.security_checks()
        passed = sum(1 for c in checks if c.ok)
        total = len(checks) or 1
        if passed == total:
            level, tone, ring_col = "Advanced", C.GREEN, C.GREEN
        elif passed >= total / 2:
            level, tone, ring_col = "Basic", C.ORANGE, C.ORANGE
        else:
            level, tone, ring_col = "At risk", C.RED, C.RED

        advisor = Card()
        advisor.body.addWidget(_section("Do you know how well protected is your device?"))
        advisor.body.addWidget(_muted("Security advisor evaluates the protection tools "
                                      "active on your Linux system."))
        row = QHBoxLayout()
        row.setSpacing(20)
        disc = BatteryRing(round(passed / total * 100), ring_col, 120,
                           center_text=level)
        row.addWidget(disc)
        box = QWidget()
        box.setProperty("class", "innerBox")
        bl = QVBoxLayout(box)
        head = QLabel(f"{level} protection")
        head.setProperty("class", "cardTitle")
        bl.addWidget(head)
        bl.addWidget(_muted(f"{passed} of {total} evaluated security features are "
                            "active on this device."))
        row.addWidget(box, 1)
        advisor.body.addLayout(row)
        self.content.addWidget(advisor)

        feats = Card(title="Evaluated security features")
        for c in checks:
            feats.body.addWidget(self._feature(c))
        self.content.addWidget(feats)
        self.content.addStretch(1)

    def _feature(self, check) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 8, 0, 8)
        col = QVBoxLayout()
        col.setSpacing(4)
        t = QLabel(check.name)
        t.setProperty("class", "rowTitle")
        col.addWidget(t)
        col.addWidget(_muted(check.desc))
        row.addLayout(col, 1)
        row.addWidget(Pill(check.status, "good" if check.ok else "bad"), 0,
                      Qt.AlignmentFlag.AlignTop)
        return w


# --------------------------------------------------------------------------- #
class GamingPage(Page):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        banner = QLabel("LEGION")
        banner.setProperty("class", "legion")
        self.content.addWidget(banner)

        # live CPU + RAM + GPU usage rings (refreshed every 2s, no blocking sleep)
        perf = Card(title="System performance")
        rings = QHBoxLayout()
        self._cpu_ring = BatteryRing(0, C.ACCENT, 150, center_text="0%")
        self._ram_ring = BatteryRing(0, C.ACCENT, 150, center_text="0%")
        self._gpu_ring = BatteryRing(0, C.ACCENT, 150, center_text="0%")
        rings.addStretch(1)
        rings.addLayout(self._ring_block(self._cpu_ring, "CPU"))
        rings.addStretch(1)
        rings.addLayout(self._ring_block(self._ram_ring, "Memory"))
        self._has_gpu = backend.gpu_usage() is not None
        if self._has_gpu:
            rings.addStretch(1)
            rings.addLayout(self._ring_block(self._gpu_ring, "GPU"))
        rings.addStretch(1)
        perf.body.addLayout(rings)
        self.content.addWidget(perf)

        # Performance mode (real fan/thermal mode) replaces the dead Legion toggles
        st = backend.vpc()
        if st.has_fan_mode:
            mode = Card(title="Performance mode")
            mode.body.addWidget(_muted("Switch the thermal/fan profile. Higher modes "
                                       "increase cooling and sustained performance."))
            seg = SegmentedControl(backend.FAN_MODES, st.fan_mode)
            seg.changed.connect(backend.set_fan_mode)
            mode.body.addWidget(seg)
            self.content.addWidget(mode)

        self.content.addWidget(self._kbd_lighting_card())
        self.content.addStretch(1)

        # seed an immediate real CPU reading, then refresh via timer deltas
        cpu0 = backend.cpu_usage()
        self._cpu_ring.set_percent(cpu0)
        self._cpu_ring.set_center_text(f"{cpu0}%")
        self._last_cpu = backend.cpu_times()
        self._refresh_perf(prime=True)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_perf)
        self._timer.start(2000)

    @staticmethod
    def _ring_block(ring: BatteryRing, label: str) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(ring, 0, Qt.AlignmentFlag.AlignHCenter)
        lbl = QLabel(label)
        lbl.setProperty("class", "muted")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(lbl)
        return col

    def _refresh_perf(self, prime: bool = False) -> None:
        idle, total = backend.cpu_times()
        di = idle - self._last_cpu[0]
        dt = total - self._last_cpu[1]
        self._last_cpu = (idle, total)
        if not prime and dt > 0:
            cpu = max(0, min(100, round((1 - di / dt) * 100)))
            self._cpu_ring.set_percent(cpu)
            self._cpu_ring.set_center_text(f"{cpu}%")
        m = backend.memory()
        self._ram_ring.set_percent(m.used_pct)
        self._ram_ring.set_center_text(f"{m.used_pct}%")
        if self._has_gpu:
            g = backend.gpu_usage()
            if g is not None:
                self._gpu_ring.set_percent(g[1])
                self._gpu_ring.set_center_text(f"{g[1]}%")

    # ------------------------------------------------- keyboard RGB (Spectrum)
    _RGB_PRESETS = ["000000", "#00A3FF", "#FF2DAA", "#39FF6A"]

    def _kbd_lighting_card(self) -> Card:
        card = Card(title="Keyboard lighting")
        card.body.addWidget(_muted("Lenovo Spectrum (ITE 8295 RGB) — driven through "
                                   "OpenRGB."))
        if not backend.rgb_available():
            card.body.addWidget(_muted(
                "OpenRGB is not installed, so the RGB keyboard can't be controlled "
                "yet. Install it with:  sudo dnf install openrgb"))
            return card

        seg = SegmentedControl(["Off", "1", "2", "3"], 0)
        seg.changed.connect(self._apply_rgb_profile)
        card.body.addWidget(seg)

        row = QHBoxLayout()
        custom = _primary_btn("Customize")
        custom.clicked.connect(self._pick_rgb_color)
        row.addWidget(custom)
        self._rgb_swatch = QFrame()
        self._rgb_swatch.setFixedSize(40, 24)
        self._rgb_swatch.setStyleSheet("background:#1f1f1f; border-radius:6px;")
        row.addWidget(self._rgb_swatch)
        self._rgb_status = QLabel("")
        self._rgb_status.setProperty("class", "muted")
        row.addWidget(self._rgb_status)
        row.addStretch(1)
        card.body.addLayout(row)

        # OpenRGB CLI is slow (~1-2s/call), so run it off the UI thread and
        # coalesce rapid clicks down to the latest requested colour.
        self._rgb_signals = _AsyncSignals()
        self._rgb_signals.done.connect(self._on_rgb_done)
        self._rgb_busy = False
        self._rgb_pending = None
        return card

    def _request_rgb(self, hex_color: str, fn) -> None:
        # optimistic swatch + queued apply (latest wins)
        self._rgb_swatch.setStyleSheet(f"background:{hex_color}; border-radius:6px;")
        self._rgb_pending = fn
        if not self._rgb_busy:
            self._start_rgb()

    def _start_rgb(self) -> None:
        if self._rgb_pending is None:
            return
        fn, self._rgb_pending = self._rgb_pending, None
        self._rgb_busy = True
        self._rgb_status.setText("Applying…")
        QThreadPool.globalInstance().start(_AsyncTask(fn, self._rgb_signals))

    def _on_rgb_done(self, ok: bool) -> None:
        self._rgb_busy = False
        if self._rgb_pending is not None:
            self._start_rgb()                      # a newer colour was requested
        else:
            self._rgb_status.setText(
                "" if ok else "Failed — check OpenRGB setup (udev rule / replug).")

    def _apply_rgb_profile(self, idx: int) -> None:
        if idx == 0:
            self._request_rgb("#1f1f1f", backend.set_rgb_off)
        else:
            color = self._RGB_PRESETS[idx]
            self._request_rgb(color, lambda c=color: backend.set_rgb(c))

    def _pick_rgb_color(self) -> None:
        c = QColorDialog.getColor()
        if c.isValid():
            hex_color = c.name()
            self._request_rgb(hex_color, lambda x=hex_color: backend.set_rgb(x))


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "cardTitle")
    return lbl
