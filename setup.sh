#!/usr/bin/env bash
set -e

# colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
die()   { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }

if [[ ! "$EUID" -eq 0 ]]; then
    die "Run this script as root user to install nusgmon."
    exit 1
fi

# preflight checks
[[ -f nusgmon ]]         || die "nusgmon binary not found. Run this from the repo root."
[[ -f nusgmon.service ]] || die "nusgmon.service not found. Run this from the repo root."
[[ -f config.toml ]]     || die "config.toml not found. Run this from the repo root."


command -v python3 &>/dev/null || die "python3 is not installed."
python3 -c "import psutil" 2>/dev/null || die "psutil not installed. Run: pip install psutil"

if ! systemctl --version &>/dev/null; then
    die "systemd is not available on this system."
fi

# interval prompt
while true; do
    read -rp "Enter record interval in seconds [default -> 3]: " _interval
    interval="${_interval:-3}"
    if [[ "$interval" =~ ^[1-9][0-9]*$ ]]; then
        break
    else
        warn "Invalid input. Enter a positive integer (e.g. 3)."
    fi
done

# install system wide
SERVICE_DIR="/etc/systemd/system"
BIN_PATH="/usr/local/bin/nusgmon"
CONFIG_DIR="/etc/nusgmon"

info "Installing nusgmon.."
mkdir -p "$CONFIG_DIR"
install -m 755 nusgmon "$BIN_PATH"
install -m 644 nusgmon.service "$SERVICE_DIR/nusgmon.service"
install -m 644 config.toml "$CONFIG_DIR/config.toml"

chmod 755 "$CONFIG_DIR"

sed -i "s|^ExecStart=.*|ExecStart=$BIN_PATH record -w $interval|" "$SERVICE_DIR/nusgmon.service"

systemctl daemon-reload
systemctl enable --now nusgmon
systemctl is-active --quiet nusgmon \
    && info "Service is running." \
    || warn "Service may not have started. Check: systemctl status nusgmon"


# check for old path of nusgmon (~/.nusgmon)
if [ -d "/home/$SUDO_USER/.nusgmon" ] && [ -f "/home/$SUDO_USER/.nusgmon/db.sqlite" ]; then
	echo -e "\n\e[1;37mYou have /home/$SUDO_USER/.nusgmon which takes your old data of your bandwidth usage\nAnd the new path for it is /var/lib/nusgmon\n\e[0m"
	read -p "Copy it to new path (/var/lib/nusgmon) ? [y/n]: " choice

	if [[ "$choice" == "y" ]]; then
		mkdir -p /var/lib/nusgmon
		chmod 755 /var/lib/nusgmon

		# force sqlite wal checkpoint to get full data in main DB file before copying
                python3 -c "import sqlite3; c=sqlite3.connect('/home/$SUDO_USER/.nusgmon/db.sqlite'); c.execute('PRAGMA wal_checkpoint(TRUNCATE);'); c.close()"

		# now copy and set permissions nicely
		cp /home/$SUDO_USER/.nusgmon/db.sqlite /var/lib/nusgmon/db.sqlite
		chmod 644 /var/lib/nusgmon/db.sqlite

		echo
		info "Database file copied to new path."
	fi
        echo
fi

info "Done! Interval set to ${interval}s."
