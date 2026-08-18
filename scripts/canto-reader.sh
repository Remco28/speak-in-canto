#!/usr/bin/env bash
# Launch the Canto Reader desktop app (Flask + pywebview).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" run_app.py
fi

exec python3 run_app.py
