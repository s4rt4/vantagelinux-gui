"""Backend data layer — wired to real hardware.

Front-end ONLY principle: this module reproduces the exact hardware behaviour of
the original `vantage.sh` (sysfs reads, `pkexec tee` writes, pactl, nmcli). The
PyQt pages call these functions; the signatures are the contract and must not
change. Every value is read live from the machine; writes are elevated via
`pkexec` exactly like the bash script did.

Real sources (target = Lenovo 82K2, Fedora 43, Wayland):
  VPC = /sys/bus/platform/devices/VPC2004:00
  conservation_mode / fan_mode / fn_lock  -> read sysfs, write via `pkexec tee`
  battery health  -> /sys/class/power_supply/BAT*
  device info     -> /sys/class/dmi/id + lscpu + /proc/meminfo + /sys/block
  mic             -> pactl get/set-source-*
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from dataclasses import dataclass


# --- low-level helpers ----------------------------------------------------
def _read(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _read_int(path: str, default=None):
    v = _read(path)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _pkexec_write(path: str | None, value) -> bool:
    """Write `value` to a root-owned sysfs file via `pkexec tee` (as vantage.sh)."""
    if not path:
        return False
    try:
        subprocess.run(
            ["pkexec", "tee", path],
            input=f"{value}\n".encode(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _vpc_dir() -> str | None:
    for p in glob.glob("/sys/bus/platform/devices/VPC2004:*"):
        return p
    return None


def _bat_dir() -> str | None:
    for name in ("BAT1", "BAT0"):
        p = f"/sys/class/power_supply/{name}"
        if os.path.isdir(p):
            return p
    g = sorted(glob.glob("/sys/class/power_supply/BAT*"))
    return g[0] if g else None


# --- device identity ------------------------------------------------------
@dataclass
class DeviceInfo:
    name: str = "Lenovo Device"
    warranty: str = "Unknown"
    device_name: str = "linux"
    product_number: str = "—"
    serial_number: str = "—"
    bios_version: str = "—"
    processor: str = "—"
    storage: str = "—"
    ram: str = "—"
    device_id: str = "—"
    product_id: str = "—"


def _total_storage_gb() -> str:
    total = 0
    for dev in glob.glob("/sys/block/*"):
        name = os.path.basename(dev)
        if name.startswith(("zram", "loop", "ram", "sr", "dm-")):
            continue
        if _read_int(f"{dev}/removable", 0):
            continue
        sectors = _read_int(f"{dev}/size", 0) or 0
        total += sectors * 512
    if not total:
        return "—"
    return f"{total / 1_000_000_000:.1f} GB"


def _ram_str() -> str:
    info = _read("/proc/meminfo") or ""
    m = re.search(r"MemTotal:\s+(\d+)", info)
    if not m:
        return "—"
    gib = int(m.group(1)) / 1024 / 1024
    return f"{gib:.1f} GB"


def _processor() -> str:
    out = _run(["lscpu"])
    for line in out.splitlines():
        if line.startswith("Model name"):
            return line.split(":", 1)[1].strip()
    info = _read("/proc/cpuinfo") or ""
    m = re.search(r"model name\s*:\s*(.+)", info)
    return m.group(1).strip() if m else "—"


def reveal_serial() -> str | None:
    """Return the system serial number, elevating via pkexec if needed.

    /sys/class/dmi/id/product_serial is root-only, so when running unprivileged
    we ask dmidecode through pkexec (one polkit prompt). Returns None on failure.
    """
    s = _read("/sys/class/dmi/id/product_serial")
    if s and s not in ("", "None"):
        return s
    if not shutil.which("dmidecode"):
        return None
    try:
        r = subprocess.run(["pkexec", "dmidecode", "-s", "system-serial-number"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    val = r.stdout.strip() if r.returncode == 0 else ""
    return val or None


def device_info() -> DeviceInfo:
    dmi = "/sys/class/dmi/id"
    name = _read(f"{dmi}/product_version") or _read(f"{dmi}/product_family") \
        or _read(f"{dmi}/product_name") or "Lenovo Device"
    serial = _read(f"{dmi}/product_serial") or "—"  # root-only; "—" otherwise
    machine_id = _read("/etc/machine-id") or ""
    if len(machine_id) == 32:
        machine_id = "-".join([
            machine_id[0:8], machine_id[8:12], machine_id[12:16],
            machine_id[16:20], machine_id[20:32],
        ]).upper()
    return DeviceInfo(
        name=name,
        warranty="Out of warranty",
        device_name=_read("/proc/sys/kernel/hostname") or "linux",
        product_number=_read(f"{dmi}/product_name") or "—",
        serial_number=serial if serial not in (None, "", "None") else "—",
        bios_version=_read(f"{dmi}/bios_version") or "—",
        processor=_processor(),
        storage=_total_storage_gb(),
        ram=_ram_str(),
        device_id=machine_id or "—",
        product_id=_read(f"{dmi}/board_name") or "—",
    )


# --- battery / power ------------------------------------------------------
@dataclass
class Battery:
    percent: int = 0
    conservation_on: bool = False
    current_wh: float = 0.0
    full_wh: float = 0.0
    design_wh: float = 0.0
    temp_c: int = 0
    cycles: int = 0
    chemistry: str = "Rechargeable Battery"
    adapter: str = "Unknown"

    @property
    def health_pct(self) -> int:
        if not self.design_wh:
            return 0
        return round(self.full_wh / self.design_wh * 100)


_CHEM = {
    "li-ion": "Rechargeable Li-ion Battery",
    "lion": "Rechargeable Li-ion Battery",
    "li-poly": "Rechargeable Li-poly Battery",
    "lipo": "Rechargeable Li-poly Battery",
}


def _thermal_c() -> int:
    """Battery sysfs exposes no temp on 82K2; use the warmest acpi thermal zone."""
    best = 0
    for z in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        t = _read_int(z, 0) or 0
        best = max(best, t)
    return round(best / 1000) if best else 0


def battery() -> Battery:
    d = _bat_dir()
    if not d:
        return Battery()

    def wh(attr_energy, attr_charge):
        uwh = _read_int(f"{d}/{attr_energy}")
        if uwh is not None:
            return uwh / 1_000_000
        # fall back to charge (µAh) * voltage (µV)
        uah = _read_int(f"{d}/{attr_charge}")
        uv = _read_int(f"{d}/voltage_now")
        if uah is not None and uv is not None:
            return uah * uv / 1e12
        return 0.0

    status = (_read(f"{d}/status") or "").lower()
    ac_online = _read_int("/sys/class/power_supply/ACAD/online")
    plugged = ac_online == 1 or status in ("charging", "full")
    tech = (_read(f"{d}/technology") or "").lower().replace("-", "").replace(" ", "")

    return Battery(
        percent=_read_int(f"{d}/capacity", 0) or 0,
        conservation_on=vpc().conservation_mode,
        current_wh=wh("energy_now", "charge_now"),
        full_wh=wh("energy_full", "charge_full"),
        design_wh=wh("energy_full_design", "charge_full_design"),
        temp_c=_read_int(f"{d}/temp", None) // 10 if _read_int(f"{d}/temp") else _thermal_c(),
        cycles=_read_int(f"{d}/cycle_count", 0) or 0,
        chemistry=_CHEM.get(tech, "Rechargeable Li-ion Battery"),
        adapter="Plugged in" if plugged else "On battery",
    )


# --- VPC toggles (sysfs via pkexec tee) -----------------------------------
FAN_MODES = ["Super Silent", "Standard", "Dust Cleaning", "Efficient Thermal Dissipation"]
KBD_BACKLIGHT = ["Low", "High", "Off"]

# sysfs fan_mode value <-> FAN_MODES index (133 and 0 both mean Super Silent)
_FAN_VAL_TO_IDX = {0: 0, 133: 0, 1: 1, 2: 2, 4: 3}
_FAN_IDX_TO_VAL = {0: 0, 1: 1, 2: 2, 3: 4}


@dataclass
class VpcState:
    conservation_mode: bool = False
    fn_lock: bool = False            # UI semantic matches vantage.sh: On == sysfs 0
    fan_mode: int = 1                # index into FAN_MODES
    kbd_backlight: int = 2           # index into KBD_BACKLIGHT
    caps_osd: bool = False
    # capability flags — control whether a row is shown at all
    has_conservation: bool = False
    has_fn_lock: bool = False
    has_fan_mode: bool = False
    has_usb_charging: bool = False


def vpc() -> VpcState:
    d = _vpc_dir()
    if not d:
        return VpcState()
    fan_raw = _read_int(f"{d}/fan_mode")
    return VpcState(
        conservation_mode=_read_int(f"{d}/conservation_mode") == 1,
        # vantage.sh: status "On" when sysfs == 0
        fn_lock=_read_int(f"{d}/fn_lock") == 0,
        fan_mode=_FAN_VAL_TO_IDX.get(fan_raw, 1),
        kbd_backlight=2,
        caps_osd=False,
        has_conservation=os.path.isfile(f"{d}/conservation_mode"),
        has_fn_lock=os.path.isfile(f"{d}/fn_lock"),
        has_fan_mode=os.path.isfile(f"{d}/fan_mode"),
        has_usb_charging=os.path.isfile(f"{d}/usb_charging"),
    )


def set_conservation(on: bool) -> bool:
    d = _vpc_dir()
    return _pkexec_write(f"{d}/conservation_mode" if d else None, 1 if on else 0)


def set_fn_lock(on: bool) -> bool:
    # vantage.sh: Activate (On) -> write 0 ; Deactivate (Off) -> write 1
    d = _vpc_dir()
    return _pkexec_write(f"{d}/fn_lock" if d else None, 0 if on else 1)


def set_fan_mode(index: int) -> bool:
    d = _vpc_dir()
    return _pkexec_write(f"{d}/fan_mode" if d else None, _FAN_IDX_TO_VAL.get(index, 1))


# --- keyboard backlight (/sys/class/leds, when present) -------------------
@dataclass
class KbdBacklight:
    present: bool = False
    levels: list = None          # e.g. ["Off", "Low", "High"]
    current: int = 0             # index into levels


def _kbd_led() -> str | None:
    for pat in ("*kbd_backlight*", "*kbd*backlight*", "*::kbd_backlight"):
        for p in sorted(glob.glob(f"/sys/class/leds/{pat}")):
            return p
    return None


def kbd_backlight() -> KbdBacklight:
    """Detect a keyboard-backlight LED. 82K2 has none → present=False (row hides)."""
    led = _kbd_led()
    if not led:
        return KbdBacklight(present=False, levels=["Off", "Low", "High"], current=0)
    mx = _read_int(f"{led}/max_brightness", 0) or 0
    cur = _read_int(f"{led}/brightness", 0) or 0
    if mx >= 2:
        return KbdBacklight(True, ["Off", "Low", "High"], min(cur, 2))
    return KbdBacklight(True, ["Off", "On"], 1 if cur else 0)


def set_kbd_backlight(index: int) -> None:
    """Write LED brightness (index maps to 0..n). No-op if no LED present."""
    led = _kbd_led()
    if not led:
        return
    # LED brightness is usually writable by the active session (logind ACL);
    # fall back to pkexec only if a plain write is denied.
    try:
        with open(f"{led}/brightness", "w") as f:
            f.write(str(index))
        return
    except OSError:
        pass
    _pkexec_write(f"{led}/brightness", index)


# --- thermals (hwmon) -----------------------------------------------------
@dataclass
class ThermalSensor:
    group: str       # "Processor CPU" / "GPU" / "Disk" / "Other"
    icon: str        # lucide icon name
    name: str        # human-readable device label
    temp_c: int


# hwmon `name` -> (group label, icon). First match wins.
_HWMON_MAP = {
    "k10temp": ("Processor CPU", "cpu"),
    "coretemp": ("Processor CPU", "cpu"),
    "zenpower": ("Processor CPU", "cpu"),
    "amdgpu": ("GPU", "gpu"),
    "nvidia": ("GPU", "gpu"),
    "radeon": ("GPU", "gpu"),
    "nvme": ("Disk", "hard-drive"),
    "drivetemp": ("Disk", "hard-drive"),
}


def _nvme_model() -> str:
    for p in glob.glob("/sys/class/nvme/nvme*/model"):
        m = _read(p)
        if m:
            return m.strip()
    return "Disk"


def _nvidia_sensors() -> list[ThermalSensor]:
    """The NVIDIA dGPU exposes no hwmon; query nvidia-smi instead."""
    if not shutil.which("nvidia-smi"):
        return []
    out = _run(["nvidia-smi", "--query-gpu=name,temperature.gpu",
                "--format=csv,noheader"])
    sensors = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[1].isdigit():
            sensors.append(ThermalSensor("GPU", "gpu", parts[0], int(parts[1])))
    return sensors


def thermals() -> tuple[float, list[ThermalSensor]]:
    """Read every recognised sensor (hwmon + nvidia-smi); return (avg_c, sensors)."""
    sensors: list[ThermalSensor] = []
    for h in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        hwname = (_read(f"{h}/name") or "").lower()
        if hwname not in _HWMON_MAP:
            continue
        group, icon = _HWMON_MAP[hwname]
        milli = _read_int(f"{h}/temp1_input")
        if milli is None:
            continue
        if group == "Processor CPU":
            name = device_info().processor
        elif group == "GPU":
            name = "AMD Radeon(TM) Graphics" if hwname == "amdgpu" else hwname.upper()
        elif group == "Disk":
            name = _nvme_model()
        else:
            name = hwname
        sensors.append(ThermalSensor(group, icon, name, round(milli / 1000)))
    sensors.extend(_nvidia_sensors())
    # group order: CPU, GPU, Disk, Other
    order = {"Processor CPU": 0, "GPU": 1, "Disk": 2}
    sensors.sort(key=lambda s: order.get(s.group, 9))
    avg = round(sum(s.temp_c for s in sensors) / len(sensors), 1) if sensors else 0.0
    return avg, sensors


# --- audio (pactl) --------------------------------------------------------
@dataclass
class Mic:
    name: str = "Microphone"
    volume: int = 0       # 0..100
    muted: bool = False


def _default_source() -> str:
    return _run(["pactl", "get-default-source"])


def mic() -> Mic:
    src = _default_source()
    name = "Microphone"
    if src:
        # find the human-readable description for the default source
        out = _run(["pactl", "list", "sources"])
        block, cur = [], []
        for line in out.splitlines():
            if line.startswith("Source #"):
                if cur:
                    block.append(cur)
                cur = []
            cur.append(line)
        if cur:
            block.append(cur)
        for b in block:
            text = "\n".join(b)
            if f"Name: {src}" in text:
                m = re.search(r"Description:\s*(.+)", text)
                if m:
                    name = m.group(1).strip()
                break

    vol = 0
    vout = _run(["pactl", "get-source-volume", "@DEFAULT_SOURCE@"])
    m = re.search(r"(\d+)%", vout)
    if m:
        vol = int(m.group(1))
    muted = "yes" in _run(["pactl", "get-source-mute", "@DEFAULT_SOURCE@"]).lower()
    return Mic(name=name, volume=vol, muted=muted)


def set_mic_volume(percent: int) -> None:
    subprocess.run(
        ["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{max(0, min(100, percent))}%"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def set_mic_mute(muted: bool) -> None:
    subprocess.run(
        ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if muted else "0"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


# --- memory / Utilities → Memory cleaner ----------------------------------
@dataclass
class Memory:
    total_gb: float = 0.0
    used_gb: float = 0.0
    available_gb: float = 0.0

    @property
    def used_pct(self) -> int:
        return round(self.used_gb / self.total_gb * 100) if self.total_gb else 0


def memory() -> Memory:
    info = _read("/proc/meminfo") or ""
    vals = {}
    for key in ("MemTotal", "MemAvailable"):
        m = re.search(rf"{key}:\s+(\d+)", info)
        if m:
            vals[key] = int(m.group(1)) / 1024 / 1024  # kB -> GiB
    total = vals.get("MemTotal", 0.0)
    avail = vals.get("MemAvailable", 0.0)
    return Memory(total_gb=total, available_gb=avail, used_gb=max(0.0, total - avail))


def drop_caches() -> bool:
    """Free reclaimable pagecache/dentries/inodes. Needs root -> pkexec.

    Equivalent to: sync && echo 3 > /proc/sys/vm/drop_caches
    """
    try:
        subprocess.run(
            ["pkexec", "sh", "-c", "sync && echo 3 > /proc/sys/vm/drop_caches"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


# --- CPU load / Gaming → System performance -------------------------------
def _cpu_times() -> tuple[int, int]:
    """Return (idle, total) jiffies from the aggregate /proc/stat cpu line."""
    line = (_read("/proc/stat") or "").splitlines()[0] if _read("/proc/stat") else ""
    parts = line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return 0, 0
    nums = [int(x) for x in parts[1:]]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)  # idle + iowait
    return idle, sum(nums)


def cpu_times() -> tuple[int, int]:
    """Public snapshot of (idle, total) jiffies for delta-based load sampling."""
    return _cpu_times()


def gpu_usage() -> tuple[str, int] | None:
    """Return (label, utilisation %) for the primary GPU, or None if unknown.

    Prefers the NVIDIA dGPU (the gaming GPU), then falls back to amdgpu sysfs.
    """
    if shutil.which("nvidia-smi"):
        out = _run(["nvidia-smi", "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits"])
        for line in out.splitlines():
            v = line.strip()
            if v.isdigit():
                return "GPU", int(v)
    for p in sorted(glob.glob("/sys/class/drm/card*/device/gpu_busy_percent")):
        v = _read_int(p)
        if v is not None:
            return "GPU", v
    return None


def cpu_usage(sample_s: float = 0.12) -> int:
    """Instantaneous CPU utilisation (%) sampled over a short window."""
    import time
    idle1, total1 = _cpu_times()
    time.sleep(sample_s)
    idle2, total2 = _cpu_times()
    dt = total2 - total1
    di = idle2 - idle1
    if dt <= 0:
        return 0
    return max(0, min(100, round((1 - di / dt) * 100)))


# --- network / Utilities → Network ----------------------------------------
@dataclass
class Network:
    connected: bool = False
    name: str = "Not connected"
    conn_type: str = "—"
    ip: str = "—"
    wifi_on: bool = False


def network() -> Network:
    wifi_on = _run(["nmcli", "radio", "wifi"]).strip().lower() == "enabled"
    name, ctype = "Not connected", "—"
    out = _run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
    for line in out.splitlines():
        f = line.split(":")
        if len(f) >= 2 and f[1] != "loopback":
            name = f[0]
            ctype = {"802-11-wireless": "Wi-Fi", "802-3-ethernet": "Ethernet"}.get(
                f[1], f[1])
            break
    ip = "—"
    ipout = _run(["ip", "-4", "-o", "addr", "show", "scope", "global"])
    for line in ipout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            ip = parts[3].split("/")[0]
            break
    return Network(connected=name != "Not connected", name=name,
                   conn_type=ctype, ip=ip, wifi_on=wifi_on)


def set_wifi(on: bool) -> None:
    subprocess.run(["nmcli", "radio", "wifi", "on" if on else "off"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --- security advisor -----------------------------------------------------
@dataclass
class SecurityCheck:
    name: str
    desc: str
    ok: bool
    status: str        # "Enabled" / "Disabled" / "Enforcing" / ...


def security_checks() -> list[SecurityCheck]:
    checks: list[SecurityCheck] = []

    # Firewall (firewalld / ufw)
    fw_ok, fw_status = False, "Inactive"
    if shutil.which("firewall-cmd"):
        fw_ok = _run(["firewall-cmd", "--state"]).strip() == "running"
        fw_status = "Active" if fw_ok else "Inactive"
    elif shutil.which("ufw"):
        fw_ok = "active" in _run(["ufw", "status"]).lower()
        fw_status = "Active" if fw_ok else "Inactive"
    checks.append(SecurityCheck(
        "Firewall", "Establishes a barrier between trusted and untrusted networks.",
        fw_ok, fw_status))

    # Mandatory access control (SELinux / AppArmor)
    if shutil.which("getenforce"):
        mode = _run(["getenforce"]).strip() or "Disabled"
        checks.append(SecurityCheck(
            "SELinux", "Mandatory access control confines programs to the minimum "
            "privileges they need.", mode == "Enforcing", mode))
    elif os.path.isdir("/sys/module/apparmor"):
        checks.append(SecurityCheck(
            "AppArmor", "Mandatory access control profiles restrict program "
            "capabilities.", True, "Enabled"))

    # Secure Boot
    if shutil.which("mokutil"):
        sb = _run(["mokutil", "--sb-state"]).lower()
        sb_on = "enabled" in sb
        checks.append(SecurityCheck(
            "Secure Boot", "Ensures the system boots using only trusted, signed "
            "software.", sb_on, "Enabled" if sb_on else "Disabled"))

    return checks


# --- OS / System update ---------------------------------------------------
@dataclass
class OsInfo:
    name: str = "Linux"
    kernel: str = ""
    last_update: str = "—"


def os_info() -> OsInfo:
    pretty = "Linux"
    rel = _read("/etc/os-release") or ""
    m = re.search(r'PRETTY_NAME="?([^"\n]+)"?', rel)
    if m:
        pretty = m.group(1)
    return OsInfo(name=pretty, kernel=_run(["uname", "-r"]), last_update=_last_update())


def _last_update() -> str:
    """Best-effort timestamp of the most recent package transaction."""
    out = _run(["rpm", "-q", "--last", "kernel"])
    if out:
        # "kernel-6.x  Tue 10 Jun 2026 09:12:01 PM WIB"
        parts = out.splitlines()[0].split(None, 1)
        if len(parts) == 2:
            return parts[1].strip()
    return "—"


def update_count() -> int | None:
    """Count available package updates (cache-only, fast). None if unknown."""
    if shutil.which("dnf"):
        # exit 100 = updates available, 0 = none; -C uses cache (no network)
        try:
            r = subprocess.run(["dnf", "-q", "-C", "check-update"],
                               capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode not in (0, 100):
            return None
        return len([ln for ln in r.stdout.splitlines()
                    if ln.strip() and not ln.startswith(("Obsoleting", "Last "))])
    if shutil.which("apt"):
        out = _run(["apt", "list", "--upgradable"])
        return max(0, len([ln for ln in out.splitlines() if "/" in ln]) - 0)
    return None


# --- hardware components / Diagnostics → Hardware scan ---------------------
@dataclass
class Component:
    group: str
    name: str
    status: str = "OK"


def hardware_components() -> list[Component]:
    """Enumerate key hardware via /proc, /sys, lspci, lsblk (no root needed)."""
    out: list[Component] = []
    out.append(Component("Processor", _processor()))
    m = memory()
    out.append(Component("Memory", f"{m.total_gb:.1f} GB RAM"))

    # GPUs via lspci
    for line in _run(["lspci"]).splitlines():
        if re.search(r"VGA compatible controller|3D controller|Display controller", line):
            name = line.split(":", 2)[-1].strip()
            out.append(Component("Graphics", name))

    # Disks via lsblk (physical disks only)
    disks = _run(["lsblk", "-dno", "NAME,SIZE,TYPE,MODEL"])
    for line in disks.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 3 and parts[2] == "disk" and not parts[0].startswith("zram"):
            model = parts[3].strip() if len(parts) > 3 else parts[0]
            out.append(Component("Storage", f"{model} ({parts[1]})"))

    # Network interfaces via /sys/class/net
    for n in sorted(glob.glob("/sys/class/net/*")):
        dev = os.path.basename(n)
        if dev == "lo" or os.path.islink(f"{n}/device") is False:
            continue
        if os.path.exists(f"{n}/wireless"):
            out.append(Component("Network", f"{dev} (Wi-Fi)"))
        elif os.path.exists(f"{n}/device"):
            out.append(Component("Network", f"{dev} (Ethernet)"))
    return out


# --- keyboard RGB (Lenovo Spectrum / ITE 8295 via OpenRGB) -----------------
# The RGB keyboard isn't exposed in sysfs; it's an ITE 8295 HID controller.
# Rather than hand-roll the HID protocol, we drive OpenRGB. A plain CLI call
# re-scans every bus (~3.5s) — far too slow per colour change — so we keep one
# `openrgb --server` running and talk to it with `--client` (~50ms/change).
_RGB_PORT = 6742
_rgb_device_cache: int | None = None
_rgb_probed = False


def rgb_available() -> bool:
    """True when OpenRGB is installed (the dependency that drives the keyboard)."""
    return shutil.which("openrgb") is not None


def _rgb_server_up() -> bool:
    import socket
    try:
        socket.create_connection(("127.0.0.1", _RGB_PORT), timeout=0.3).close()
        return True
    except OSError:
        return False


def _ensure_rgb_server() -> bool:
    """Start (once) and reuse a background OpenRGB SDK server. ~3.5s first time."""
    if not rgb_available():
        return False
    if _rgb_server_up():
        return True
    import time
    try:
        subprocess.Popen(
            ["openrgb", "--server", "--server-port", str(_RGB_PORT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
    except OSError:
        return False
    for _ in range(80):                       # poll up to ~8s for device detection
        if _rgb_server_up():
            time.sleep(0.4)                   # let the server finish enumerating
            return True
        time.sleep(0.1)
    return False


def _openrgb_base(server: bool) -> list[str]:
    base = ["openrgb"]
    if server:
        base += ["--client", f"127.0.0.1:{_RGB_PORT}"]
    return base


def rgb_device() -> int | None:
    """OpenRGB device index of the keyboard, or None. Cached after first probe."""
    global _rgb_device_cache, _rgb_probed
    if _rgb_probed:
        return _rgb_device_cache
    _rgb_probed = True
    if not rgb_available():
        return None
    server = _ensure_rgb_server()
    out = _run(_openrgb_base(server) + ["--list-devices"])
    entries: list[tuple[int, str, list[str]]] = []
    for line in out.splitlines():
        m = re.match(r"^(\d+):\s*(.+)$", line)
        if m:
            entries.append((int(m.group(1)), m.group(2).strip(), []))
        elif entries:
            entries[-1][2].append(line)
    chosen = None
    for idx, name, block in entries:
        text = "\n".join(block)
        if "Keyboard" in text:          # prefer a device typed as Keyboard
            chosen = idx
            break
        if chosen is None and ("ITE" in name or "Lenovo" in name):
            chosen = idx
    _rgb_device_cache = chosen
    return chosen


def set_rgb(hex_color: str) -> bool:
    """Set a solid keyboard colour via OpenRGB. hex like '#RRGGBB' or 'RRGGBB'."""
    if not rgb_available():
        return False
    server = _ensure_rgb_server()
    dev = rgb_device()
    if dev is None:
        return False
    color = hex_color.lstrip("#")
    base = _openrgb_base(server)
    for mode in ("Direct", "Static"):
        try:
            r = subprocess.run(base + ["-d", str(dev), "-m", mode, "-c", color],
                               capture_output=True, text=True, timeout=12)
        except (OSError, subprocess.SubprocessError):
            return False
        if r.returncode == 0:
            return True
    return False


def set_rgb_off() -> bool:
    return set_rgb("000000")


# --- system status (Home stats card) --------------------------------------
@dataclass
class SystemStats:
    uptime: str = "—"
    boot: str = "—"
    volume: int = -1      # output %, -1 = unknown
    brightness: int = -1  # %, -1 = unknown


_boot_cache: str | None = None


def _fmt_uptime(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _boot_duration() -> str:
    global _boot_cache
    if _boot_cache is not None:
        return _boot_cache
    out = _run(["systemd-analyze", "time"])
    val = "—"
    m = re.search(r"=\s*([\d.]+)s\b", out)
    if m:
        val = f"{float(m.group(1)):.1f}s"
    else:
        m2 = re.search(r"=\s*(.+)$", out, re.M)
        if m2:
            val = m2.group(1).strip()
    _boot_cache = val
    return val


def _output_volume() -> int:
    out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    m = re.search(r"(\d+)%", out)
    return int(m.group(1)) if m else -1


def _brightness_pct() -> int:
    for b in sorted(glob.glob("/sys/class/backlight/*")):
        cur = _read_int(f"{b}/brightness")
        mx = _read_int(f"{b}/max_brightness")
        if cur is not None and mx:
            return round(cur / mx * 100)
    return -1


def system_stats() -> SystemStats:
    up = _read("/proc/uptime")
    uptime = _fmt_uptime(float(up.split()[0])) if up else "—"
    return SystemStats(uptime=uptime, boot=_boot_duration(),
                       volume=_output_volume(), brightness=_brightness_pct())


# --- display info + brightness (Device settings → Display) -----------------
@dataclass
class DisplayOut:
    name: str          # eDP-1 / HDMI-A-1
    resolution: str    # 1920x1080
    modes: int = 0


def displays() -> list[DisplayOut]:
    out: list[DisplayOut] = []
    for c in sorted(glob.glob("/sys/class/drm/card*-*")):
        if (_read(f"{c}/status") or "") != "connected":
            continue
        name = os.path.basename(c).split("-", 1)[-1]
        modes = (_read(f"{c}/modes") or "").splitlines()
        out.append(DisplayOut(name=name,
                              resolution=modes[0] if modes else "—",
                              modes=len(modes)))
    return out


def _backlight_dev() -> str | None:
    for b in sorted(glob.glob("/sys/class/backlight/*")):
        return os.path.basename(b)
    return None


@dataclass
class Brightness:
    present: bool = False
    percent: int = -1
    device: str = ""


def brightness() -> Brightness:
    dev = _backlight_dev()
    if not dev:
        return Brightness()
    cur = _read_int(f"/sys/class/backlight/{dev}/brightness")
    mx = _read_int(f"/sys/class/backlight/{dev}/max_brightness")
    pct = round(cur / mx * 100) if cur is not None and mx else -1
    return Brightness(present=True, percent=pct, device=dev)


def set_brightness(percent: int) -> bool:
    """Set screen brightness (0..100) via logind — no root needed for the
    active session. Falls back to a pkexec sysfs write."""
    dev = _backlight_dev()
    if not dev:
        return False
    mx = _read_int(f"/sys/class/backlight/{dev}/max_brightness") or 0
    if not mx:
        return False
    raw = max(1, round(max(1, min(100, percent)) / 100 * mx))  # never fully off
    try:
        subprocess.run(
            ["busctl", "call", "org.freedesktop.login1",
             "/org/freedesktop/login1/session/auto",
             "org.freedesktop.login1.Session", "SetBrightness", "ssu",
             "backlight", dev, str(raw)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError):
        return _pkexec_write(f"/sys/class/backlight/{dev}/brightness", raw)


# --- output (speaker) volume + open system settings ------------------------
def output_volume() -> tuple[int, bool]:
    out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    m = re.search(r"(\d+)%", out)
    pct = int(m.group(1)) if m else -1
    muted = "yes" in _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"]).lower()
    return pct, muted


def set_output_volume(percent: int) -> None:
    subprocess.run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@",
         f"{max(0, min(100, percent))}%"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_settings(panel: str = "") -> bool:
    """Open the desktop's system settings (optionally a specific panel)."""
    if shutil.which("gnome-control-center"):
        cmd = ["gnome-control-center"] + ([panel] if panel else [])
    elif shutil.which("systemsettings"):
        cmd = ["systemsettings"]
    elif shutil.which("systemsettings5"):
        cmd = ["systemsettings5"]
    else:
        return False
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except OSError:
        return False


# --- gsettings-backed toggles (GNOME) -------------------------------------
def gsettings_bool(schema: str, key: str):
    """Return a gsettings boolean, or None if unavailable (gate UI on None)."""
    if not shutil.which("gsettings"):
        return None
    out = _run(["gsettings", "get", schema, key])
    if not out:
        return None
    return out.strip().lower() == "true"


def set_gsettings_bool(schema: str, key: str, value: bool) -> None:
    if shutil.which("gsettings"):
        subprocess.run(["gsettings", "set", schema, key,
                        "true" if value else "false"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


NIGHT_LIGHT = ("org.gnome.settings-daemon.plugins.color", "night-light-enabled")
TOUCHPAD_TAP = ("org.gnome.desktop.peripherals.touchpad", "tap-to-click")
TOUCHPAD_NSCROLL = ("org.gnome.desktop.peripherals.touchpad", "natural-scroll")


# --- input devices (Device settings → Input) ------------------------------
_INPUT_NOISE = ("button", "speaker", "video bus", "consumer control",
                "system control", "wireless radio", "headphone", "extra buttons",
                "hda ", "mic ")


def input_devices() -> list[tuple[str, str]]:
    """List real keyboards / touchpads / mice from /proc/bus/input/devices."""
    data = _read("/proc/bus/input/devices") or ""
    res: list[tuple[str, str]] = []
    seen = set()
    for block in data.split("\n\n"):
        nm = re.search(r'N: Name="([^"]+)"', block)
        if not nm:
            continue
        name = nm.group(1)
        low = name.lower()
        if any(n in low for n in _INPUT_NOISE):
            continue
        h = re.search(r"H: Handlers=(.+)", block)
        handlers = (h.group(1) if h else "").lower()
        if "touchpad" in low or "touchpad" in handlers:
            kind = "Touchpad"
        elif "mouse" in handlers and "keyboard" not in low:
            kind = "Mouse"
        elif "kbd" in handlers and "keyboard" in low:
            kind = "Keyboard"
        else:
            continue
        if name not in seen:
            seen.add(name)
            res.append((kind, name))
    return res
