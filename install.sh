#!/bin/bash
# Install runtime dependencies for the Vantage PyQt6 GUI.
#
# The GUI needs: Python 3 + PyQt6, polkit (pkexec) for the privileged sysfs
# writes (conservation_mode / fan_mode / fn_lock), and upower for battery info.
# pactl (PipeWire/PulseAudio) and NetworkManager are optional — the backend
# degrades gracefully if they are missing.

detect_package_manager() {
    if command -v pacman &> /dev/null; then echo "pacman"
    elif command -v apt &> /dev/null; then echo "apt"
    elif command -v dnf &> /dev/null; then echo "dnf"
    elif command -v zypper &> /dev/null; then echo "zypper"
    else echo "unknown"; fi
}

install_for() {
    case "$1" in
        pacman)
            echo "Detected pacman (Arch and derivatives)"
            sudo pacman -S --needed python-pyqt6 polkit upower
            ;;
        apt)
            echo "Detected apt (Debian/Ubuntu and derivatives)"
            sudo apt update
            sudo apt install -y python3-pyqt6 policykit-1 upower
            ;;
        dnf)
            echo "Detected dnf (Fedora and derivatives)"
            sudo dnf install -y python3-pyqt6 polkit upower
            ;;
        zypper)
            echo "Detected zypper (openSUSE)"
            sudo zypper install -y python3-PyQt6 polkit upower
            ;;
        *)
            echo "Unable to detect a supported package manager."
            echo "Please install manually: Python 3, PyQt6, polkit, upower."
            exit 1
            ;;
    esac
}

# Prefer the distro family from /etc/os-release, fall back to PM detection.
distro=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    distro="${ID_LIKE:-$ID}"
fi

case "$distro" in
    *arch*)             install_for pacman ;;
    *debian*|*ubuntu*)  install_for apt ;;
    *fedora*|*rhel*)    install_for dnf ;;
    *suse*)             install_for zypper ;;
    *)                  install_for "$(detect_package_manager)" ;;
esac

echo "Requirements are installed."
