"""Device settings: a secondary nav column (Power/Display/.../Device details)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QSlider, QStackedWidget, QVBoxLayout,
                             QWidget)

from .. import backend
from ..theme import C, icon_pixmap
from ..widgets.cards import Card, CopyRow, Pill, RevealRow, ToggleRow
from ..widgets.icon import SvgIcon
from ..widgets.meter import MeterBar
from ..widgets.nav import SubNav
from ..widgets.segmented import SegmentedControl

SUB_NAV = [
    ("power", "battery-charging", "Power"),
    ("display", "monitor", "Display"),
    ("sound", "music-2", "Sound"),
    ("input", "keyboard", "Input"),
    ("widgets", "grid-2x2-check", "Widgets"),
    ("details", "laptop", "Device details"),
]


def _hrule() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setProperty("class", "rule")
    line.setFixedHeight(1)
    return line


def _link_row(text: str, on_click=None) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    lbl = QLabel(text)
    lbl.setProperty("class", "link")
    lbl.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click is not None:
        def _press(_e, fn=on_click):
            fn()  # discard the return value — event handlers must return None

        lbl.mousePressEvent = _press
    row.addWidget(lbl)
    row.addWidget(SvgIcon("monitor", C.ACCENT, 15))
    row.addStretch(1)
    return w


def _subhead(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "rowTitle")
    return lbl


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "muted")
    lbl.setWordWrap(True)
    return lbl


def _slider_block(icon: str, value: int, on_change, lo: int = 0, hi: int = 100) -> QWidget:
    """Icon + horizontal slider with a live percentage label."""
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(6)
    val = QLabel(f"{value}%")
    val.setProperty("class", "muted")
    val.setAlignment(Qt.AlignmentFlag.AlignRight)
    v.addWidget(val)
    srow = QHBoxLayout()
    srow.addWidget(SvgIcon(icon, C.TEXT_DIM, 18))
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(lo, hi)
    slider.setValue(max(lo, min(hi, value)))

    def changed(x):
        val.setText(f"{x}%")
        on_change(x)

    slider.valueChanged.connect(changed)
    srow.addWidget(slider, 1)
    v.addLayout(srow)
    return box


class DeviceSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # left: section title + secondary nav
        left = QWidget()
        left.setFixedWidth(300)
        left_col = QVBoxLayout(left)
        left_col.setContentsMargins(40, 28, 20, 28)
        left_col.setSpacing(20)
        title = QLabel("Device settings")
        title.setProperty("class", "pageTitle")
        left_col.addWidget(title)
        self.nav = SubNav(SUB_NAV)
        left_col.addWidget(self.nav)
        left_col.addStretch(1)
        root.addWidget(left)

        # right: stacked sub-pages in a scroll area
        self.stack = QStackedWidget()
        self._pages = {
            "power": self._power_page(),
            "display": self._display_page(),
            "sound": self._sound_page(),
            "input": self._input_page(),
            "widgets": self._coming_soon_page(
                "Widgets", "Dashboard widgets aren't available yet — "
                "they're planned for a future update."),
            "details": self._details_page(),
        }
        self._order = [k for k, _i, _t in SUB_NAV]
        for key in self._order:
            self.stack.addWidget(self._scrollable(self._pages[key]))
        root.addWidget(self.stack, 1)

        self.nav.selected.connect(self._show)
        self.nav.select("power")

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
        column.setMaximumWidth(960)
        col = QVBoxLayout(column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(18)
        heading = QLabel(title)
        heading.setProperty("class", "pageHeading")
        col.addWidget(heading)
        outer.addWidget(column, 1)
        outer.addStretch(0)
        return host, col

    # ------------------------------------------------------------- sub-pages
    def _power_page(self) -> QWidget:
        batt = backend.battery()
        st = backend.vpc()
        host, col = self._shell("Power")

        # Conservation / rapid charge / fan mode — the headline battery controls.
        rc_avail, rc_on = backend.rapid_charge()
        if st.has_conservation or st.has_fan_mode or rc_avail:
            settings = Card(title="Battery & thermal")
            added = False
            if st.has_conservation:
                settings.body.addWidget(ToggleRow(
                    "Conservation mode",
                    "Caps the battery charge near 60% to extend its lifespan when "
                    "the laptop is mostly plugged in.",
                    checked=st.conservation_mode, on_toggle=backend.set_conservation))
                added = True
            if rc_avail:
                if added:
                    settings.body.addWidget(_hrule())
                settings.body.addWidget(ToggleRow(
                    "Rapid charge",
                    "Charge the battery at the fastest rate. Turn off to use the "
                    "standard charge rate.",
                    checked=rc_on, on_toggle=backend.set_rapid_charge))
                added = True
            if st.has_fan_mode:
                if added:
                    settings.body.addWidget(_hrule())
                settings.body.addWidget(_subhead("Fan mode"))
                fan = SegmentedControl(backend.FAN_MODES, st.fan_mode)
                fan.changed.connect(backend.set_fan_mode)
                settings.body.addWidget(fan)
            col.addWidget(settings)

        health = Card(title="Battery health", menu=True)
        bar = MeterBar(batt.health_pct / 100, [(0, "#2ea043"), (1, "#7ee787")], 12)
        health.body.addWidget(bar)
        legend = QHBoxLayout()
        legend.setSpacing(20)
        legend.addStretch(1)
        legend.addWidget(_dot_label(C.GREEN, f"Current charge: {batt.current_wh:.2f} Wh"))
        legend.addWidget(_dot_label("#7ee787", f"Full charge capacity: {batt.full_wh:.2f} Wh"))
        legend.addStretch(1)
        health.body.addLayout(legend)
        design = QHBoxLayout()
        design.addStretch(1)
        design.addWidget(_dot_label("#6e6e6e", f"Original design capacity: {batt.design_wh:.2f} Wh"))
        design.addStretch(1)
        health.body.addLayout(design)
        col.addWidget(health)

        temp = Card()
        temp.body.addWidget(_subhead(f"Temperature:  {batt.temp_c}°C / {batt.temp_c * 9 // 5 + 32}°F"))
        temp.body.addWidget(MeterBar(0.45, [
            (0.0, "#5b6cff"), (0.4, "#3fb950"), (0.7, "#d29922"), (1.0, "#f85149")], 12))
        col.addWidget(temp)

        glance = Card(title="At a glance")
        glance.body.addWidget(self._glance_row("Current charge", f"No activity({batt.percent}%)"))
        glance.body.addWidget(self._glance_row(
            "Full charge capacity comparison",
            f"{batt.health_pct}% capacity (100% original capacity)", ("Good", "good")))
        glance.body.addWidget(self._glance_row(
            "Accumulated charge cycles", str(batt.cycles), ("High", "high")))
        glance.body.addWidget(self._glance_row("Battery chemistry", batt.chemistry))
        glance.body.addWidget(self._glance_row("Power adapter", batt.adapter))
        col.addWidget(glance)
        col.addStretch(1)
        return host

    def _glance_row(self, label: str, value: str, pill=None) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 6, 0, 6)
        lbl = QLabel(label)
        lbl.setProperty("class", "rowTitle")
        lbl.setFixedWidth(280)
        val = QLabel(value)
        val.setProperty("class", "muted")
        row.addWidget(lbl)
        row.addWidget(val, 1)
        if pill is not None:
            row.addWidget(Pill(pill[0], pill[1]))
        return w

    def _display_page(self) -> QWidget:
        host, col = self._shell("Display")

        br = backend.brightness()
        if br.present:
            bcard = Card()
            bcard.body.addWidget(_subhead("Brightness"))
            bcard.body.addWidget(
                _slider_block("sun", br.percent, backend.set_brightness, lo=5))
            nl = backend.gsettings_bool(*backend.NIGHT_LIGHT)
            if nl is not None:
                bcard.body.addWidget(_hrule())
                bcard.body.addWidget(ToggleRow(
                    "Night light",
                    "Shift the display to warmer colors to reduce eye strain.",
                    checked=nl,
                    on_toggle=lambda v: backend.set_gsettings_bool(*backend.NIGHT_LIGHT, v)))
            col.addWidget(bcard)

        info = Card()
        info.body.addWidget(_subhead("Displays"))
        outs = backend.displays()
        if outs:
            for d in outs:
                info.body.addWidget(
                    self._glance_row(d.name, f"{d.resolution}  ·  {d.modes} modes"))
        else:
            info.body.addWidget(_muted("No connected display detected."))
        info.body.addWidget(_hrule())
        info.body.addWidget(_link_row("Open system display settings",
                                      lambda: backend.open_settings("display")))
        col.addWidget(info)

        pers = Card()
        pers.body.addWidget(_subhead("Colors & themes"))
        pers.body.addWidget(_muted("Personalize your background, colors, and contrast "
                                   "themes in the system appearance settings."))
        pers.body.addWidget(_link_row("Open appearance settings",
                                      lambda: backend.open_settings("background")))
        col.addWidget(pers)
        col.addStretch(1)
        return host

    def _sound_page(self) -> QWidget:
        host, col = self._shell("Sound")

        ovol, _omute = backend.output_volume()
        out = Card()
        out.body.addWidget(_subhead("Output volume"))
        out.body.addWidget(
            _slider_block("volume-2", max(ovol, 0), backend.set_output_volume))
        out.body.addWidget(_hrule())
        out.body.addWidget(_link_row("Open system sound settings",
                                     lambda: backend.open_settings("sound")))
        col.addWidget(out)

        m = backend.mic()
        inp = Card()
        inp.body.addWidget(_subhead("Microphone"))
        inp.body.addWidget(QLabel(m.name))
        inp.body.addWidget(
            _slider_block("music-2", max(m.volume, 0), backend.set_mic_volume))
        col.addWidget(inp)
        col.addStretch(1)
        return host

    def _input_page(self) -> QWidget:
        st = backend.vpc()
        host, col = self._shell("Input")

        # ---- Keyboard ----
        kcard = Card()
        kcard.body.addWidget(_subhead("Keyboard"))
        kbd = backend.kbd_backlight()
        if kbd.present:
            kcard.body.addWidget(_muted("Backlight brightness (Fn + Space)"))
            seg = SegmentedControl(kbd.levels, kbd.current)
            seg.changed.connect(backend.set_kbd_backlight)
            kcard.body.addWidget(seg)
            kcard.body.addWidget(_hrule())
        if st.has_fn_lock:
            kcard.body.addWidget(ToggleRow(
                "Function lock (Fn + FnLock)",
                "Switch functions of the function keys (F1–F12). Function keys provide "
                "two sets of functions: special and standard.",
                checked=st.fn_lock, on_toggle=backend.set_fn_lock))
            kcard.body.addWidget(_hrule())
        kcard.body.addWidget(_link_row("Open keyboard settings",
                                       lambda: backend.open_settings("keyboard")))
        col.addWidget(kcard)

        # ---- Touchpad (GNOME peripherals via gsettings) ----
        tap = backend.gsettings_bool(*backend.TOUCHPAD_TAP)
        if tap is not None:
            tcard = Card()
            tcard.body.addWidget(_subhead("Touchpad"))
            names = [n for k, n in backend.input_devices() if k == "Touchpad"]
            if names:
                tcard.body.addWidget(_muted(names[0]))
            tcard.body.addWidget(ToggleRow(
                "Tap to click", "Tap the touchpad surface to register a click.",
                checked=tap,
                on_toggle=lambda v: backend.set_gsettings_bool(*backend.TOUCHPAD_TAP, v)))
            nsc = backend.gsettings_bool(*backend.TOUCHPAD_NSCROLL)
            if nsc is not None:
                tcard.body.addWidget(_hrule())
                tcard.body.addWidget(ToggleRow(
                    "Natural scrolling", "Scrolling moves the content, not the view.",
                    checked=nsc,
                    on_toggle=lambda v: backend.set_gsettings_bool(*backend.TOUCHPAD_NSCROLL, v)))
            col.addWidget(tcard)

        # ---- Detected input devices ----
        devs = backend.input_devices()
        if devs:
            dcard = Card()
            dcard.body.addWidget(_subhead("Detected input devices"))
            for kind, name in devs:
                dcard.body.addWidget(self._glance_row(kind, name))
            col.addWidget(dcard)

        col.addStretch(1)
        return host

    def _coming_soon_page(self, title: str, message: str) -> QWidget:
        host, col = self._shell(title)
        card = Card()
        box = QVBoxLayout()
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.setSpacing(10)
        icon = SvgIcon("grid-2x2-check", C.TEXT_DIM, 48)
        box.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
        head = QLabel("Coming soon")
        head.setProperty("class", "cardTitle")
        head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(head)
        msg = _muted(message)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(msg)
        card.body.addLayout(box)
        col.addWidget(card)
        col.addStretch(1)
        return host

    def _details_page(self) -> QWidget:
        info = backend.device_info()
        host, col = self._shell("Device details")
        card = Card()
        rows = []
        for label, value in [
            ("Device name", info.device_name),
            ("Product number", info.product_number),
        ]:
            r = CopyRow(label, value)
            rows.append(r)
            card.body.addWidget(r)
        serial_row = RevealRow("Serial number", info.serial_number,
                               backend.reveal_serial)
        rows.append(serial_row)
        card.body.addWidget(serial_row)
        for label, value in [
            ("Bios version", info.bios_version),
            ("Processor", info.processor),
            ("Storage", info.storage),
            ("Installed ram", info.ram),
            ("Device id", info.device_id),
            ("Product id", info.product_id),
        ]:
            r = CopyRow(label, value)
            rows.append(r)
            card.body.addWidget(r)
        col.addWidget(card)

        actions = QHBoxLayout()
        actions.addStretch(1)
        copy_all = QPushButton("Copy all")
        copy_all.setProperty("class", "primaryPill")
        copy_all.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_all.clicked.connect(lambda: self._copy_all(rows, copy_all))
        actions.addWidget(copy_all)
        col.addLayout(actions)
        col.addStretch(1)
        return host

    @staticmethod
    def _copy_all(rows, button=None) -> None:
        from PyQt6.QtWidgets import QApplication
        text = "\n".join(f"{lbl}: {val}" for lbl, val in (r.pair() for r in rows))
        QApplication.clipboard().setText(text)
        if button is not None:
            button.setText("Copied!")

def _dot_label(color: str, text: str) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    dot = QLabel("●")
    dot.setStyleSheet(f"color:{color}; font-size:11px;")
    lbl = QLabel(text)
    lbl.setProperty("class", "muted")
    row.addWidget(dot)
    row.addWidget(lbl)
    return w
