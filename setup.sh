#!/usr/bin/env bash
set -euo pipefail

# colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
die()   { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }
bold()  { echo -e "${BOLD}$*${NC}"; }

SERVICE_DIR="/etc/systemd/system"
SERVICE_FILE="$SERVICE_DIR/nusgmon.service"
BIN_PATH="/usr/local/bin/nusgmon"
ROOT_CONFIG_DIR="/etc/nusgmon"
DB_DIR="/var/lib/nusgmon"
DB_FILE="$DB_DIR/db.sqlite"
DEFAULT_INTERVAL=3
SKIP_START=0
FORCE_INTERVAL=""

usage() {
    echo -e "${BOLD}nusgmon setup${NC}"
    echo
    echo "Installs the nusgmon binary, config and systemd service."
    echo
    echo "Options:"
    echo "  -i, --interval N   Record interval in seconds (skips the prompt)"
    echo "  -n, --no-start     Install everything but do not start the service"
    echo "  -h, --help         Show this help"
    echo
    echo "Without --interval you will be asked how often to record,"
    echo "e.g. \"1\" for every second."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--interval) [[ $# -ge 2 ]] || die "--interval needs a value."; FORCE_INTERVAL="$2"; shift 2 ;;
        -i=*|--interval=*) FORCE_INTERVAL="${1#*=}"; shift ;;
        -n|--no-start) SKIP_START=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1 (try --help)" ;;
    esac
done

[[ "${EUID}" -eq 0 ]] || die "Run this script as root user to install nusgmon."

SUDO_USER_NAME="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$SUDO_USER_NAME" | cut -d: -f6)"
USER_CONFIG_DIR="$REAL_HOME/.config/nusgmon"

# preflight checks
[[ -f nusgmon ]]         || die "nusgmon binary not found. Run this from the repo root."
[[ -f nusgmon.service ]] || die "nusgmon.service not found. Run this from the repo root."
[[ -f config.toml ]]     || die "config.toml not found. Run this from the repo root."

command -v python3 &>/dev/null || die "python3 is not installed."
command -v install &>/dev/null || die "the 'install' command is not available."

if ! python3 -c "import psutil" 2>/dev/null; then
    die "psutil is not installed. Install it with your package manager, e.g.:
  Arch:   sudo pacman -S python-psutil
  Debian: sudo apt install python3-psutil
  Fedora: sudo dnf install python3-psutil
  or:     pip install psutil"
fi

if ! systemctl --version &>/dev/null; then
    die "systemd is not available on this system."
fi

# read the interval currently baked into an already installed service
installed_interval() {
    [[ -f "$SERVICE_FILE" ]] || return 0
    sed -n 's|^ExecStart=.*[[:space:]]-w[[:space:]]\{1,\}\([0-9]\{1,\}\).*|\1|p' "$SERVICE_FILE" | head -1
}

interval_prompt() {
    local fallback="$1" answer

    # warnings go to stderr so stdout stays a clean single value
    if [[ ! -t 0 ]]; then
        echo "Not running interactively, using interval ${fallback}s." >&2
        echo "$fallback"
        return
    fi

    while true; do
        read -rp "Enter record interval in seconds [default -> ${fallback}]: " answer || true
        answer="${answer:-$fallback}"
        if [[ "$answer" =~ ^[1-9][0-9]*$ ]]; then
            echo "$answer"
            return
        fi
        echo "Invalid input. Enter a positive integer (e.g. 1 for every second)." >&2
    done
}

current="$(installed_interval)"

if [[ -n "$FORCE_INTERVAL" ]]; then
    [[ "$FORCE_INTERVAL" =~ ^[1-9][0-9]*$ ]] || die "Invalid --interval: $FORCE_INTERVAL"
    interval="$FORCE_INTERVAL"
    info "Using interval ${interval}s from --interval."
elif [[ "$current" =~ ^[1-9][0-9]*$ ]]; then
    # service is already set up, keep the installed interval and skip the prompt
    interval="$current"
    info "Service already set up, keeping interval ${interval}s."
else
    interval="$(interval_prompt "$DEFAULT_INTERVAL")"
    [[ "$interval" =~ ^[1-9][0-9]*$ ]] || die "Invalid interval: $interval"
fi

# ---- migrate an old database before the service can create a fresh empty one ----
OLD_DB_DIR="$REAL_HOME/.nusgmon"
if [[ -d "$OLD_DB_DIR" && -f "$OLD_DB_DIR/db.sqlite" && ! -f "$DB_FILE" ]]; then
    warn "Found an old database at $OLD_DB_DIR (data will move to $DB_FILE)."
    answer=""
    read -rp "Copy it to the new path? [y/N]: " answer || true
    if [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]; then
        mkdir -p "$DB_DIR"
        # force a wal checkpoint so the main db file holds the full data before copying
        python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('PRAGMA wal_checkpoint(TRUNCATE);'); c.close()" "$OLD_DB_DIR/db.sqlite"
        cp "$OLD_DB_DIR/db.sqlite" "$DB_FILE"
        if [[ -n "$REAL_HOME" && "$EUID" -eq 0 && "$REAL_HOME" != "/root" ]]; then
            chown -R "$SUDO_USER_NAME:$SUDO_USER_NAME" "$DB_DIR"
        fi
        chmod 755 "$DB_DIR"
        chmod 664 "$DB_FILE"
        info "Database copied to $DB_FILE."
    else
        warn "Skipped. Your old data stays at $OLD_DB_DIR/db.sqlite."
    fi
    echo
fi

# ---- install ----
info "Installing nusgmon.."

mkdir -p "$ROOT_CONFIG_DIR"
mkdir -p "$USER_CONFIG_DIR"

install -m 755 nusgmon "$BIN_PATH"
install -m 644 nusgmon.service "$SERVICE_FILE"

# never clobber a config the user already edited
if [[ -f "$ROOT_CONFIG_DIR/config.toml" ]]; then
    info "Kept existing $ROOT_CONFIG_DIR/config.toml"
else
    install -m 644 config.toml "$ROOT_CONFIG_DIR/config.toml"
fi

if [[ -f "$USER_CONFIG_DIR/config.toml" ]]; then
    info "Kept existing $USER_CONFIG_DIR/config.toml"
else
    install -m 644 config.toml "$USER_CONFIG_DIR/config.toml"
fi

if [[ -n "$REAL_HOME" && "$EUID" -eq 0 && "$REAL_HOME" != "/root" ]]; then
    chown -R "$SUDO_USER_NAME:$SUDO_USER_NAME" "$USER_CONFIG_DIR"
fi
chmod 755 "$ROOT_CONFIG_DIR" "$USER_CONFIG_DIR"

# only rewrite ExecStart when the installed binary changed or the interval changed
if ! cmp -s nusgmon "$BIN_PATH" 2>/dev/null; then
    install -m 755 nusgmon "$BIN_PATH"
fi

sed -i "s|^ExecStart=.*|ExecStart=$BIN_PATH record -w $interval|" "$SERVICE_FILE"

systemctl daemon-reload

if [[ "$SKIP_START" -eq 1 ]]; then
    systemctl enable nusgmon
    warn "Service installed and enabled but not started. Start it with: systemctl start nusgmon"
else
    systemctl enable --now nusgmon
    sleep 1
    if systemctl is-active --quiet nusgmon; then
        info "Service is running."
    else
        warn "Service may not have started. Check: systemctl status nusgmon"
    fi
fi

bold "Done! :)"
