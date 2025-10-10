#!/usr/bin/env bash
set -euo pipefail

# Quickstart for macOS/Linux: create venv (prefer outside OneDrive), install deps once, and run the app
# Usage:
#   ./quickstart.sh [--db PATH] [--python /path/to/python] [--fast] [--force-install] [--app-name NAME] [--app-path /path/to/App.app]
# Options:
#   --db PATH             Set and persist PROJECT_DB_PATH for this and future runs
#   --python PATH         Use a specific python to create the venv
#   --fast                Skip dependency checks/installs (fastest startup)
#   --force-install       Force reinstall dependencies even if cached
#   --app-name NAME       Preferred macOS .app bundle name (default: "Vols Signage")
#   --app-path PATH       Explicit path to .app or Contents/MacOS binary (takes precedence)
# Env:
#   QUICKSTART_VENV_DIR   Absolute path to use for the virtualenv (overrides defaults)
#   APP_NAME              Preferred macOS .app bundle name (default: "Vols Signage")
#   APP_PATH              Explicit path to .app or Contents/MacOS binary (takes precedence)

DB_PATH=""
PYTHON_BIN=""
APP=""
APP_PATH_ARG=""
FAST=0
FORCE_INSTALL=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      cat <<'HELP'
Usage: ./quickstart.sh [options]
  --db PATH             Set and persist PROJECT_DB_PATH for this and future runs
  --python PATH         Use a specific python to create the venv
  --fast                Skip dependency checks/installs (fastest startup)
  --force-install       Force reinstall dependencies even if cached
  --app-name NAME       Preferred macOS .app bundle name (default: "Vols Signage")
  --app-path PATH       Explicit path to .app or Contents/MacOS binary (takes precedence)

Env:
  QUICKSTART_VENV_DIR   Absolute path to use for the virtualenv (overrides defaults)
  APP_NAME              Preferred macOS .app bundle name (default: "Vols Signage")
  APP_PATH              Explicit path to .app or Contents/MacOS binary (takes precedence)
HELP
      exit 0 ;;
    --db)
      DB_PATH="$2"; shift 2 ;;
    --python)
      PYTHON_BIN="$2"; shift 2 ;;
    --app-name)
      APP="$2"; shift 2 ;;
    --app-path)
      APP_PATH_ARG="$2"; shift 2 ;;
    --fast)
      FAST=1; shift 1 ;;
    --force-install)
      FORCE_INSTALL=1; shift 1 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON_BIN="python3"; else PYTHON_BIN="python"; fi
fi

# Choose venv location: prefer outside OneDrive to avoid slow sync of thousands of files
workspace_dir="$(pwd)"
venv_dir_default="${workspace_dir}/.venv"
if [[ -n "${QUICKSTART_VENV_DIR:-}" ]]; then
  VENV_DIR="$QUICKSTART_VENV_DIR"
else
  case "$workspace_dir" in
    *OneDrive*|*"OneDrive - "*)
      if [[ "$(uname -s)" == "Darwin" ]]; then
        VENV_DIR="$HOME/Library/Application Support/Aja_au_Grimace/venv"
      else
        VENV_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/Aja_au_Grimace/venv"
      fi
      ;;
    *)
      VENV_DIR="$venv_dir_default"
      ;;
  esac
fi
mkdir -p "$(dirname "$VENV_DIR")"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[setup] Creating venv at: $VENV_DIR using $PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

PY="$VENV_DIR/bin/python"
PIP_DISABLE_PIP_VERSION_CHECK=1 "$PY" -m pip install --upgrade pip setuptools wheel >/dev/null

# Compute requirements hash to avoid reinstalling on every launch
REQ_FILE="requirements.txt"
REQ_HASH_FILE="$VENV_DIR/.req.sha256"
compute_hash() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$REQ_FILE" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$REQ_FILE" | awk '{print $2}'
  else
    # fallback to python
    "$PYTHON_BIN" - <<'PY'
import hashlib,sys
p='requirements.txt'
h=hashlib.sha256(open(p,'rb').read()).hexdigest()
print(h)
PY
  fi
}

NEED_INSTALL=1
if [[ -f "$REQ_HASH_FILE" && $FORCE_INSTALL -eq 0 ]]; then
  CURR_HASH="$(compute_hash)"
  OLD_HASH="$(cat "$REQ_HASH_FILE" 2>/dev/null || echo)"
  if [[ "$CURR_HASH" == "$OLD_HASH" ]]; then
    NEED_INSTALL=0
  fi
fi

if [[ $FAST -eq 1 ]]; then
  NEED_INSTALL=0
fi

if [[ $NEED_INSTALL -eq 1 ]]; then
  echo "[setup] Installing Python dependencies (this may take a minute the first time)…"
  PIP_DISABLE_PIP_VERSION_CHECK=1 "$PY" -m pip install -r "$REQ_FILE"
  compute_hash > "$REQ_HASH_FILE" || true
else
  echo "[setup] Using cached dependencies (requirements unchanged)"
fi

# Persist and/or load DB path override
if [[ -n "$DB_PATH" ]]; then
  printf "%s" "$DB_PATH" > db_path.txt
  export PROJECT_DB_PATH="$DB_PATH"
else
  if [[ -f db_path.txt ]]; then
    export PROJECT_DB_PATH="$(cat db_path.txt)"
  fi
fi

# macOS: if a packaged app bundle exists, prefer launching it for faster startup
if [[ "$(uname -s)" == "Darwin" ]]; then
  # Look for a packaged .app bundle
  # Priority:
  #  0) Explicit APP_PATH (flag/env)
  #  1) User-provided app name in ~/Applications and /Applications
  #  2) ./release/*.app (most recent)
  #  3) ./_stage_main/main.app
  #  4) Any .app under repo (fallback)
  APP_BIN=""
  # Default to 'Vols Signage' if not provided via flag/env
  if [[ -n "${APP:-}" ]]; then
    APP_NAME="$APP"
  elif [[ -n "${APP_NAME:-}" ]]; then
    APP_NAME="$APP_NAME"
  else
    APP_NAME="Vols Signage"
  fi
  APP_PATH="${APP_PATH_ARG:-${APP_PATH:-}}"
  resolve_app_bin() {
    local app_path="$1"
    if [[ -d "$app_path/Contents/MacOS" ]]; then
      # Try to find an executable in Contents/MacOS
      local exe
      exe=$(find "$app_path/Contents/MacOS" -maxdepth 1 -type f -perm -111 -print 2>/dev/null | head -n1 || true)
      if [[ -z "$exe" ]]; then
        exe=$(find "$app_path/Contents/MacOS" -maxdepth 1 -type f -perm +111 -print 2>/dev/null | head -n1 || true)
      fi
      if [[ -n "$exe" && -x "$exe" ]]; then
        echo "$exe"; return 0
      fi
    fi
    return 1
  }
  # 0) Explicit APP_PATH (can be a .app or a direct binary)
  if [[ -n "$APP_PATH" ]]; then
    if [[ -d "$APP_PATH" ]]; then
      cand=$(resolve_app_bin "$APP_PATH") || true
      if [[ -n "$cand" ]]; then APP_BIN="$cand"; fi
    elif [[ -f "$APP_PATH" && -x "$APP_PATH" ]]; then
      APP_BIN="$APP_PATH"
    fi
  fi
  # 1) Named app in user/system Applications
  if [[ -n "$APP_NAME" ]]; then
    for base in "$HOME/Applications" "/Applications"; do
      if [[ -d "$base/$APP_NAME.app" ]]; then
        cand=$(resolve_app_bin "$base/$APP_NAME.app") || true
        if [[ -n "$cand" ]]; then APP_BIN="$cand"; break; fi
      fi
    done
  fi
  # 2) Most recent app in ./release
  if [[ -z "$APP_BIN" && -d ./release ]]; then
    recent_app=$(find ./release -type d -name "*.app" -print0 2>/dev/null | xargs -0 ls -td 2>/dev/null | head -n1 || true)
    if [[ -n "$recent_app" ]]; then
      cand=$(resolve_app_bin "$recent_app") || true
      if [[ -n "$cand" ]]; then APP_BIN="$cand"; fi
    fi
  fi
  # 3) Staged app
  if [[ -z "$APP_BIN" && -d "./_stage_main/main.app" ]]; then
    cand=$(resolve_app_bin "./_stage_main/main.app") || true
    if [[ -n "$cand" ]]; then APP_BIN="$cand"; fi
  fi
  # 4) Fallback: any .app under repo
  if [[ -z "$APP_BIN" ]]; then
    CANDIDATE=$(find . -maxdepth 3 -type f -path "*/Contents/MacOS/*" -print 2>/dev/null | head -n1 || true)
    if [[ -n "$CANDIDATE" && -x "$CANDIDATE" ]]; then
      APP_BIN="$CANDIDATE"
    fi
  fi
  if [[ -n "$APP_BIN" ]]; then
    echo "[run] Launching packaged app: $APP_BIN (name='${APP_NAME:-}', path='${APP_PATH:-}')"
    exec "$APP_BIN"
  fi
fi

exec "$PY" main.py
