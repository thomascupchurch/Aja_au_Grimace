#!/usr/bin/env python3
"""
PythonAnywhere DB sync helper.

Usage (on PythonAnywhere bash console):

  # Copy a DB file into the repo root as project_data.db (atomic move)
  python3 web/pa_sync_db.py --src /home/youruser/incoming/project_data.db

Options:
  --src <path>       Required. Source SQLite file to publish
  --dest <path>      Optional. Destination path (default: ~/Aja_au_Grimace/project_data.db)
  --backup           Create a timestamped .bak copy of existing dest before replace
  --reload           Touch the WSGI file to trigger app reload after sync
  --wsgi <path>      Path to WSGI file for reload (default: ~/Aja_au_Grimace/web/pythonanywhere_wsgi.py)

Notes:
- Performs write to a temp file then atomic rename to minimize partial reads
- Keeps permissions and paths simple for PythonAnywhere
- Designed for read-only viewer: the web app should have WEB_SQLITE_RO=1 set
"""
import argparse
import os
import shutil
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.expanduser('~/Aja_au_Grimace')
DEFAULT_DEST = os.path.join(PROJECT_ROOT, 'project_data.db')
DEFAULT_WSGI = os.path.join(PROJECT_ROOT, 'web', 'pythonanywhere_wsgi.py')


def touch(path: str):
    try:
        with open(path, 'a'):
            os.utime(path, None)
        return True
    except Exception as e:
        print(f"[sync] touch failed for {path}: {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--dest', default=DEFAULT_DEST)
    ap.add_argument('--backup', action='store_true')
    ap.add_argument('--reload', action='store_true')
    ap.add_argument('--wsgi', default=DEFAULT_WSGI)
    args = ap.parse_args()

    src = os.path.expanduser(args.src)
    dest = os.path.expanduser(args.dest)

    if not os.path.isfile(src):
        print(f"[sync] source not found: {src}", file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if args.backup and os.path.exists(dest):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = f"{dest}.bak_{ts}"
        try:
            shutil.copy2(dest, bak)
            print(f"[sync] backup created: {bak}")
        except Exception as e:
            print(f"[sync] backup failed: {e}", file=sys.stderr)
            return 3

    tmp = f"{dest}.tmp_{int(time.time())}"
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)  # atomic on same filesystem
        print(f"[sync] synced {src} -> {dest}")
    except Exception as e:
        print(f"[sync] copy/replace failed: {e}", file=sys.stderr)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return 4

    if args.reload:
        if touch(os.path.expanduser(args.wsgi)):
            print(f"[sync] reloaded via touch: {args.wsgi}")
        else:
            print(f"[sync] reload touch failed: {args.wsgi}", file=sys.stderr)
            return 5

    return 0


if __name__ == '__main__':
    sys.exit(main())
