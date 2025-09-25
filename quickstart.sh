#!/usr/bin/env bash
set -euo pipefail

# Quickstart for macOS/Linux: create venv, install deps, and run the app
# Usage:
#   ./quickstart.sh [--db PATH] [--python /path/to/python]

DB_PATH=""
PYTHON_BIN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --db)
      DB_PATH="$2"; shift 2 ;;
    --python)
      PYTHON_BIN="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON_BIN="python3"; else PYTHON_BIN="python"; fi
fi

if [[ ! -d .venv ]]; then
  echo "[setup] Creating .venv with $PYTHON_BIN"
  "$PYTHON_BIN" -m venv .venv
fi

PY="$(pwd)/.venv/bin/python"
"$PY" -m pip install --upgrade pip setuptools wheel >/dev/null
"$PY" -m pip install -r requirements.txt

if [[ -n "$DB_PATH" ]]; then
  # Persist override for subsequent runs via db_path.txt (and export for this run)
  printf "%s" "$DB_PATH" > db_path.txt
  export PROJECT_DB_PATH="$DB_PATH"
fi

exec "$PY" main.py
