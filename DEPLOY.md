# Deploying the Read‑only Web Viewer

This guide covers deploying the Flask web viewer in `web/` to PythonAnywhere and Render. The viewer is read‑only and serves data from your SQLite database.

Quick facts
- App entry point: `web/app.py` (Flask app object is `app`)
- Working directory for the web app: the `web/` folder
- Database path: uses `PROJECT_DB_PATH` env var, or `db_path.txt` in the repo root, else `project_data.db` in the repo root
- Vendor assets: `web/static/vendor/frappe-gantt.umd.js` and `.css` are included to avoid CDNs

Contents
- PythonAnywhere (shared hosting)
- Render (managed container)
- On‑prem: Windows service/IIS/Docker
- Environment variables and DB placement
- Verification and troubleshooting

---

## PythonAnywhere

1) Create a PythonAnywhere account and a new Web App
- Choose Manual configuration (Flask)
- Pick a Python version compatible with your project (3.10+ recommended)

2) Upload or sync your project
- Recommended layout on PythonAnywhere:
  - Code: `~/Aja_au_Grimace` (root of this repo)
  - The Flask app lives in `~/Aja_au_Grimace/web`
  - SQLite DB:
    - Option A: Upload a copy of `project_data.db` to `~/Aja_au_Grimace/`
    - Option B: Point to a shared DB via absolute path and set `PROJECT_DB_PATH`

3) Virtualenv and requirements
- Create a virtualenv in the PA UI and set it for this web app
- Install only web requirements (avoid heavy desktop deps like PyQt):
  ```bash
  pip install -r ~/Aja_au_Grimace/web/requirements-web.txt
  ```

4) WSGI configuration
Edit your web app’s WSGI file in PythonAnywhere and replace contents with:
```python
import os, sys

PROJECT_ROOT = os.path.expanduser('~/Aja_au_Grimace')
WEB_DIR = os.path.join(PROJECT_ROOT, 'web')

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.append(WEB_DIR)

# Optional: point to a shared or custom database
# os.environ['PROJECT_DB_PATH'] = '/home/youruser/path/to/project_data.db'

os.chdir(WEB_DIR)
from app import app as application
```

5) Environment variables (optional but recommended)
- In the PA “Environment Variables” section, add `PROJECT_DB_PATH` if your DB is not at the repo root.

6) Reload the web app
- Open the PythonAnywhere dashboard page for the web app and click “Reload”
- Visit your site; see verification below

7) Optional: sync DB updates
- Use the helper script to atomically replace the deployed DB from a source path and reload:
  ```bash
  # In a PythonAnywhere Bash console
  python3 web/pa_sync_db.py --src /home/youruser/incoming/project_data.db --backup --reload
  ```
  Flags:
  - `--dest` defaults to `~/Aja_au_Grimace/project_data.db`
  - `--wsgi` defaults to `~/Aja_au_Grimace/web/pythonanywhere_wsgi.py`
  - `--backup` creates `project_data.db.bak_YYYYmmdd_HHMMSS`


## Render.com

Two options: point-and-click dashboard or IaC (`render.yaml`). This repo includes everything needed; we also provide a minimal `render.yaml` template below.

Important: Use a web‑only requirements file to avoid installing PyQt on the server.

1) Prepare repo contents
- Ensure `web/requirements-web.txt` exists (this repo has it):
  ```text
  Flask==3.0.3
  gunicorn==22.0.0
  ```

2) Create a new Web Service on Render (env: Python)
- Root repository: this repo
- Working directory: `web`
- Build command:
  ```bash
  pip install -r requirements-web.txt
  ```
- Start command:
  ```bash
  gunicorn -w 2 -b 0.0.0.0:$PORT app:app
  ```
- Environment variable (if using a shared DB):
  - `PROJECT_DB_PATH=/opt/render/project/src/project_data.db` (or another absolute path you provide/mount)

3) Using render.yaml (optional)
Add a `render.yaml` at the repo root with:
```yaml
services:
  - type: web
    name: project-gantt-viewer
    env: python
    plan: free
    autoDeploy: true
    workingDirectory: web
    buildCommand: pip install -r requirements-web.txt
    startCommand: gunicorn -w 2 -b 0.0.0.0:$PORT app:app
    envVars:
      - key: PROJECT_DB_PATH
        value: /opt/render/project/src/project_data.db
```

If you commit this file, Render can auto-detect and configure the service.

4) Database placement on Render
- For a simple read‑only snapshot, commit `project_data.db` to the repo (not recommended if it’s sensitive)
- Better: upload the DB at deploy time or mount persistent storage, then set `PROJECT_DB_PATH` accordingly


## On‑prem (Windows/IIS/Docker)

Choose the approach that fits your infra. All options read the same SQLite DB path your desktop uses (OneDrive/SMB). Set `WEB_SQLITE_RO=1` to connect read‑only and avoid locks.

### A) Windows service (Gunicorn via Waitress alternative)

While Gunicorn is Linux‑oriented, you can run the Flask app with Waitress on Windows.

1) Create a venv on the server and install web deps
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r web\requirements-web.txt
pip install waitress
```

2) Start the server (test) — or use the helper script `web/serve_waitress.ps1`
```powershell
$env:PROJECT_DB_PATH = "\\\server\share\project_data.db"  # or C:\path\to\project_data.db
$env:WEB_SQLITE_RO = "1"
python -m waitress --listen=0.0.0.0:8000 web.app:app
```
Helper:
```powershell
cd web
./serve_waitress.ps1 -DbPath "\\server\share\project_data.db" -Port 8000 -ReadOnly
```

3) Optional: install as a Windows service (NSSM) — or use `scripts/install_service_nssm.ps1`
- Download NSSM, then:
```powershell
nssm install GanttViewer "C:\path\to\python.exe" "-m" "waitress" "--listen=0.0.0.0:8000" "web.app:app"
nssm set GanttViewer AppDirectory "C:\path\to\Aja_au_Grimace"
nssm set GanttViewer AppEnvironmentExtra "PROJECT_DB_PATH=\\server\share\project_data.db" "WEB_SQLITE_RO=1"
```
Helper:
```powershell
./scripts/install_service_nssm.ps1 -DbPath "\\server\share\project_data.db" -Port 8000 -ReadOnly
```

### B) IIS with wfastcgi

1) Install wfastcgi in your venv
```powershell
pip install wfastcgi
python -m wfastcgi enable
```

2) Configure an IIS Site or App pointing to the repo root
- Handler mapping: FastCGI with `wfastcgi.py`
- Set environment variables for the app pool:
  - `WSGI_HANDLER=app.app` (module: `web/app.py`, object: `app`)
  - `PYTHONPATH=C:\path\to\Aja_au_Grimace;C:\path\to\Aja_au_Grimace\web`
  - `PROJECT_DB_PATH=\\server\share\project_data.db`
  - `WEB_SQLITE_RO=1`

3) Ensure the IIS App Pool identity has read access to the share/path

### C) Docker (Windows/Linux host)

1) Create `web/Dockerfile` (example)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY web/requirements-web.txt /app/
RUN pip install --no-cache-dir -r requirements-web.txt
COPY web /app
ENV WEB_SQLITE_RO=1
EXPOSE 8000
CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","app:app"]
```

2) Build and run (this repo already includes `web/Dockerfile`)
```bash
docker build -t gantt-viewer -f web/Dockerfile .
docker run -d -p 8000:8000 \
  -e PROJECT_DB_PATH=/data/project_data.db \
  -e WEB_SQLITE_RO=1 \
  -v \\server\share:/data:ro \
  gantt-viewer
```

On Linux hosts, mount your SMB share with `//server/share` to `/data` and pass `:ro` for read‑only.

## Environment and DB setup

Database path resolution order at runtime:
1. Environment variable `PROJECT_DB_PATH`
2. `db_path.txt` file at the repo root containing the absolute path
3. Fallback: `project_data.db` at the repo root

For shared or central DBs, prefer `PROJECT_DB_PATH`.

Read‑only mode for network shares:
- Set `WEB_SQLITE_RO=1` (or `true/yes`) to open SQLite in `mode=ro`. This reduces lock contention and prevents the web app from writing to the file.


## Verify deployment

1. Open `/api/debug` in your deployed site
   - Confirms `db_path`, existence, and row count
2. Open the root `/`
   - Should render the Gantt
3. If bars or assets are missing
   - Check `web/static/vendor/` files are present (JS/CSS)
   - The page will try CDN, then use a local stub if JS fails to load


## Troubleshooting

- HTTP 500 or blank page
  - Check provider logs (PythonAnywhere error log; Render service logs)
- No tasks shown
  - `/api/debug` row_count is 0 or DB not found → set `PROJECT_DB_PATH` or place `db_path.txt`
- CDN blocked / CSP errors
  - Ensure vendored JS is present: `web/static/vendor/frappe-gantt.umd.js`
- Gunicorn not found (Render)
  - Ensure `gunicorn` is listed in `web/requirements-web.txt`
- Incorrect working directory
  - Make sure working directory is `web/` so `from app import app` resolves, and header/static paths work


## Security notes

- This viewer is read‑only and serves whatever is in your SQLite file
- Do not expose sensitive data publicly
- Prefer a snapshot DB for public demos
- For private/internal use, restrict access at the platform level or place behind SSO
