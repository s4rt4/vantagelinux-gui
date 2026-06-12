Name:           vantage
Version:        2.0.0
Release:        1%{?dist}
Summary:        Unofficial Lenovo Vantage control center for Linux (PyQt6)

License:        GPL-3.0-or-later
URL:            https://github.com/s4rt4/vantagelinux-gui
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  make
Requires:       python3
Requires:       python3-pyqt6
Requires:       polkit
Requires:       upower
Recommends:     pipewire-pulseaudio
Recommends:     NetworkManager
Recommends:     openrgb

%description
A native PyQt6 desktop app that brings the look and core features of the
Windows Lenovo Vantage control center to GNU/Linux: conservation mode, rapid
charge, fan mode, battery health, live thermals, an RGB keyboard control (via
OpenRGB) and more, reading and controlling the hardware directly.

Unofficial — not affiliated with, endorsed by, or supported by Lenovo.

%prep
%autosetup -n %{name}-%{version}

%build

%install
make install-files DESTDIR=%{buildroot} PREFIX=/usr

%files
%license LICENSE
%doc README.md
/usr/bin/vantage
/usr/share/vantage/
/usr/share/icons/hicolor/scalable/apps/vantage.svg
/usr/share/applications/vantage.desktop

%changelog
* Fri Jun 12 2026 s4rt4 <surat.sarta@gmail.com> - 2.0.0-1
- Initial RPM release
