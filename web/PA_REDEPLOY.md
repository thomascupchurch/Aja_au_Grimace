# PythonAnywhere Redeploy Checklist (v2 Web Viewer)

This is a quick, copy/paste-friendly guide for redeploying the v2 Flask web app on PythonAnywhere.

App entry: `web/v2/app.py` (WSGI loader prefers v2), fallback legacy: `web/app.py`
WSGI file: `web/pythonanywhere_wsgi.py` (already in repo)
Web-only deps: `web/requirements-web.txt` (no PyQt)

---

## 0) Expected layout on PythonAnywhere

- Code: `~/Aja_au_Grimace` (repo root)
- App dir: `~/Aja_au_Grimace/web`
- Optional SQLite DB: `~/Aja_au_Grimace/project_data.db` (or set `PROJECT_DB_PATH`)
- Optional images folder: `~/Aja_au_Grimace/images` (or set `WEB_IMAGES_ROOT`)

Python version: 3.10+ recommended

---

## 1) Virtualenv and install (web-only)

- Create/activate your venv in the PA Web UI or Bash console
- Install deps from `web/requirements-web.txt`

Notes
- Keep it web-only to avoid desktop dependencies (PyQt)
- Packages include Flask, SQLAlchemy, PyMySQL, Gunicorn (for alternative hosting)

---

## 2) WSGI configuration

Use the repo’s WSGI file content at `web/pythonanywhere_wsgi.py`:
- Adds project and `web/` to PYTHONPATH
- chdir into `web/`
- Tries `from v2.app import app as application` first; falls back to legacy `app.py`

If you prefer, point the PA WSGI file directly to `~/Aja_au_Grimace/web/pythonanywhere_wsgi.py`.

---

## 3) Choose your DB backend

SQLite (quickest)
- Upload `project_data.db` to the repo root, or set an absolute `PROJECT_DB_PATH` in the PythonAnywhere Web UI > Environment Variables
- Optional: set `WEB_SQLITE_RO=1` for read-only SQLite (prevents locks)

MySQL (PythonAnywhere DB)
- In the PA Databases tab, create a MySQL database; note user/pass/host/db
- In PA Web UI > Environment Variables, set:
  - `WEB_DB_URL = mysql+pymysql://USER:PASSWORD@HOST/USER$DBNAME?charset=utf8mb4`
- App will use MySQL automatically when `WEB_DB_URL` is set and SQLAlchemy is installed

Write access (optional)
- To enable edits from the web UI, set an edit token in PA Web UI > Environment Variables:
  - `WEB_EDIT_TOKEN = your-strong-shared-secret`
- If using SQLite, ensure `WEB_SQLITE_RO` is not truthy. For writes, unset it or set `WEB_SQLITE_RO=0`.
- If using MySQL, ensure the DB user has UPDATE privileges on `project_parts`.

---

## 4) (Optional) Migrate SQLite → MySQL

There is a helper: `web/migrate_sqlite_to_mysql.py`
- Flags: `--create` (create table), `--truncate` (clean), `--replace` (drop+create)
- Typical run (in a PA Bash console, with venv activated):
  - `python3 web/migrate_sqlite_to_mysql.py --sqlite ~/Aja_au_Grimace/project_data.db --mysql "$WEB_DB_URL" --create --truncate`
- Table name defaults to `project_parts`

Verify after migration at `/api/debug` (row_count should match your SQLite source)

---

## 5) Images and header assets

- By default, images are served from `~/Aja_au_Grimace/images`
- To point elsewhere, set `WEB_IMAGES_ROOT` to an absolute path in PA Web UI
- Export/header uses `header.svg` or `header.png` from the repo root (optional branding)

Diagnostics
- `/api/debug` shows `images_root` (and count in legacy app); confirm path exists and contains files

---

## 6) Reload and verify

Reload
- Use the Reload button in the PA Web UI for your web app (or touch the WSGI file)

Verify
- Home (`/`) loads and shows Gantt
- `/api/debug` shows:
  - `db_backend: mysql` or `sqlite`
  - `db_path` (or host/db for MySQL)
  - `row_count` > 0
  - `images_root` path is correct
- Interactions:
  - Gantt/Timeline bars & labels: double‑click opens Full Details
  - Details… toolbar button enables after selection and opens the modal
  - Set Token… in the toolbar stores the token locally; Edit… button in Details opens an edit form. Saving calls `/api/task/update`.
  - Images/Database/Dashboard/Costs views load

---

## 7) Syncing the SQLite DB in-place (optional)

Helper: `web/pa_sync_db.py`
- Copies a source SQLite file to `~/Aja_au_Grimace/project_data.db` atomically
- Options: `--backup` creates timestamped `.bak`, `--reload` touches WSGI to reload
- Example:
  - `python3 web/pa_sync_db.py --src /home/youruser/incoming/project_data.db --backup --reload`

Defaults
- `--dest` → `~/Aja_au_Grimace/project_data.db`
- `--wsgi` → `~/Aja_au_Grimace/web/pythonanywhere_wsgi.py`

---

## 8) Troubleshooting quick hits

- 500/blank page → check error log in PA Web UI
- No tasks → wrong DB path/URL or empty table; confirm `/api/debug` and set `PROJECT_DB_PATH` or `WEB_DB_URL`
- Images missing → check `/api/debug` images_root; set `WEB_IMAGES_ROOT` and reload; ensure files and permissions
- MySQL auth/host errors → recheck `WEB_DB_URL` format and credentials
- Wrong app loading → ensure WSGI matches `web/pythonanywhere_wsgi.py`, correct venv is set, and Flask installed there

---

## 9) Security

- Edits (if enabled) require `WEB_EDIT_TOKEN` and are limited to a small set of columns: `% Complete`, `Status`, `Start Date`, `Duration (days)`, `Responsible`, `Type`, `Internal/External`, `Dependencies`, `Pace Link`, `Notes`.
- For a strictly read‑only site, omit `WEB_EDIT_TOKEN` and/or set `WEB_SQLITE_RO=1` (SQLite). Alternatively, use a MySQL user without UPDATE permission.
- Do not expose sensitive data publicly; restrict access at the PA app level if needed.

---

## 10) Useful endpoints

- `/` main viewer
- `/api/debug` diagnostics (backend, row count, paths)
- `/api/tasks`, `/api/database`, `/api/images`, `/api/metrics`, `/api/costs` data APIs
- `POST /api/task/update` write API (requires `WEB_EDIT_TOKEN` if set); JSON body: `{ "edit_token": "...", "project_part": "Name", "updates": { "Status": "In Progress", "% Complete": 20, ... } }`
