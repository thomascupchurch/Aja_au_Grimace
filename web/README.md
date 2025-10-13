# Web viewer (clean rebuild)

This folder contains a fresh, simplified Flask web viewer built directly from the desktop app's model (main.py). It is read‑only by default and supports both SQLite and MySQL (PythonAnywhere).

## Features
- Views: Gantt, Calendar, Timeline, Tree, Images, Database (read‑only)
- Backend endpoints:
  - `GET /api/tasks`: timeline/gantt/tree data parsed from `project_parts`
  - `GET /api/database`: Database table rows + columns (mirrors desktop columns)
  - `GET /api/images`: list of image files
  - `GET /api/debug`: environment + quick DB diagnostics
  - `GET /images/<name>`: serves images from configured root
- Diagnostics: `/api/debug` reports backend, row count, and images root

## Configuration (env vars)
- `PROJECT_DB_PATH`: path to SQLite file (overrides repo default). If missing, a `db_path.txt` in the repo root is honored.
- `WEB_DB_URL`: SQLAlchemy URL for MySQL/other (e.g. `mysql+pymysql://user:pass@host/user$db?charset=utf8mb4`). If set, MySQL is used.
- `WEB_SQLITE_RO`: `1/true` to open SQLite in read‑only mode.
- `WEB_IMAGES_ROOT`: path to images directory (default: repo `images/`).
- `WEB_WATERMARK_TEXT`: footer text shown under the app.

## Run locally
From the repo root:

```powershell
# Using your Python (ensure Flask is installed or use the repo venv)
python .\web\app.py
```

Open http://127.0.0.1:5000 and choose a view. Use `/api/debug` to verify DB connectivity.

## PythonAnywhere
- Keep using `web/pythonanywhere_wsgi.py` and your virtualenv
- Set `WEB_DB_URL` (quoted in shell if `$` in DB name)
- Optionally set `PROJECT_DB_PATH` if falling back to SQLite
- Reload the web app after syncing files

## Notes
- The web viewer is read‑only. It computes non‑destructive fields (Children, Calculated End Date if missing, % Complete normalization) at request time.
- Column order and naming mirror the desktop `ProjectDataModel.COLUMNS` to maintain familiarity.
