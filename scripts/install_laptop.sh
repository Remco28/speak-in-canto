#!/usr/bin/env bash
# Install Canto Reader as a local desktop app on Ubuntu/Debian.
#
# - Checks for / installs Python 3.12+
# - Installs GTK + WebKit2GTK system dependencies for pywebview
# - Creates a venv and installs Python dependencies
# - Creates .env from .env.example if missing
# - Writes a .desktop launcher entry
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

APP_NAME="Canto Reader"
DESKTOP_FILE="${HOME}/.local/share/applications/canto-reader.desktop"
ICON_PATH="${PROJECT_ROOT}/assets/canto-reader.svg"
LAUNCHER_PATH="${PROJECT_ROOT}/scripts/canto-reader.sh"

log() { printf '\033[1;36m==> \033[0m%s\n' "$*"; }
warn() { printf '\033[1;33mwarning: \033[0m%s\n' "$*"; }
fail() { printf '\033[1;31merror: \033[0m%s\n' "$*" >&2; exit 1; }

run_sudo() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    if ! command -v sudo >/dev/null 2>&1; then
      fail "sudo is required to install system packages, but it was not found."
    fi
    sudo "$@"
  fi
}

detect_python() {
  local candidate
  for candidate in python3.12 python3.13 python3.14 python3.15 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

detect_webkit_pkg() {
  local version_id major
  version_id="$( ( . /etc/os-release && printf '%s' "${VERSION_ID:-0}" ) 2>/dev/null || printf '0' )"
  major="${version_id%%.*}"
  if [ "$major" -ge 24 ]; then
    printf '%s' "gir1.2-webkit2-4.1"
  else
    printf '%s' "gir1.2-webkit2-4.0"
  fi
}

# 1. Python 3.12+
PYTHON_BIN="$(detect_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  log "Python 3.12+ not found; installing via apt."
  run_sudo apt-get update
  run_sudo apt-get install -y python3 python3-venv python3-pip
  PYTHON_BIN="$(detect_python || true)"
  if [ -z "$PYTHON_BIN" ]; then
    fail "Python 3.12+ still not available after apt install. On Ubuntu 22.04, install 3.12 via deadsnakes PPA or pyenv, then re-run."
  fi
fi
log "Using Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

# 2. System GUI dependencies
WEBKIT_PKG="$(detect_webkit_pkg)"
log "Installing system GUI dependencies (WebKit package: $WEBKIT_PKG)..."
run_sudo apt-get update
run_sudo apt-get install -y \
  python3-venv python3-dev build-essential pkg-config \
  libgtk-3-0 libgirepository1.0-dev libcairo2-dev \
  gir1.2-gtk-3.0 python3-gi python3-gi-cairo \
  "$WEBKIT_PKG"

# 3. Virtualenv + Python deps
if [ ! -d ".venv" ]; then
  log "Creating virtualenv..."
  "$PYTHON_BIN" -m venv .venv
fi
log "Installing Python dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-desktop.txt

# 4. .env
if [ ! -f ".env" ]; then
  log "Creating .env from .env.example..."
  cp .env.example .env
  warn "Edit .env and add OPENROUTER_API_KEY and Google TTS credentials."
else
  log ".env already exists; leaving it unchanged."
fi

# 5. Launcher + .desktop entry
chmod +x "$LAUNCHER_PATH"

log "Writing desktop entry: $DESKTOP_FILE"
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Cantonese reading app
Exec=${LAUNCHER_PATH}
Icon=${ICON_PATH}
Terminal=false
Categories=Education;Utility;
EOF
chmod +x "$DESKTOP_FILE"

# 6. Next steps
cat <<'EOF'

Done. Next steps:
  1. Edit .env and set:
     - OPENROUTER_API_KEY
     - Google TTS credentials (GOOGLE_APPLICATION_CREDENTIALS or GCP_SERVICE_ACCOUNT_JSON)
  2. Optionally add dictionary data:
       .venv/bin/python scripts/prepare_dictionary_data.py --cedict <file> --cccanto <file>
  3. Launch "Canto Reader" from your app menu, or run scripts/canto-reader.sh.
EOF
