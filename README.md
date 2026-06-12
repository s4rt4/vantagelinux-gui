# Lenovo Vantage for Linux (Unofficial)

> ⚠️ **Unofficial project.** This is an independent, community-built application.
> It is **not** affiliated with, endorsed by, or supported by Lenovo. "Lenovo"
> and "Lenovo Vantage" are trademarks of Lenovo, used here only to describe what
> this tool emulates. Use at your own risk.

A modern, native **PyQt6** desktop app that brings the look and core features of
the Windows *Lenovo Vantage* control center to GNU/Linux. It reads and controls
your laptop's hardware directly through `sysfs`, `upower`, `pactl` and
`nvidia-smi`, with privileged writes elevated via `pkexec`.

> This is a ground-up GUI rewrite of the original bash + zenity script by
> [niizam/vantage](https://github.com/niizam/vantage). The hardware logic is
> ported faithfully — only the interface changed.

## :rocket: Features

* **Home** — device identity, battery ring, conservation status, warranty card
* **Device settings → Power** — Conservation mode toggle, Fan mode (Super Silent /
  Standard / Dust Cleaning / Efficient), battery health (Wh, cycles, temperature)
* **Device settings → Input** — Fn Lock toggle, keyboard backlight
* **Device settings → Sound** — microphone level (via PipeWire/PulseAudio)
* **Device settings → Device details** — model, BIOS, CPU, RAM, storage (with copy)
* **Device diagnostics → Thermal monitor** — live CPU / GPU / Disk temperatures
  (hwmon + NVIDIA via `nvidia-smi`), with a °C / °F toggle

## :computer: Installation

```bash
git clone https://github.com/niizam/vantage.git
cd vantage
sudo make install
```

Then launch **Lenovo Vantage** from your applications list, or run `vantage`.

To try it without installing:

```bash
make run        # equivalent to: python3 vantage.py
```

## :hotsprings: Uninstall

```bash
sudo make uninstall
```

## :warning: Requirements

Installed automatically by `make install` (which calls `install.sh`):

* Python 3 + **PyQt6**
* **polkit** (`pkexec`) — for privileged sysfs writes
* **upower** — battery information

Optional (the app degrades gracefully without them): `pactl`
(PipeWire/PulseAudio) for the microphone, `NetworkManager` for Wi-Fi,
`nvidia-smi` for discrete-GPU temperature.

## :wrench: Supported hardware

Targets Lenovo laptops exposing the `VPC2004` ACPI platform device
(`/sys/bus/platform/devices/VPC2004:*`). Features whose sysfs attributes are
absent on a given machine are hidden automatically.

---
