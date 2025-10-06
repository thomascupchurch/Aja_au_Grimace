# Project Management App

A desktop project planning & visualization tool built with PyQt5 + QGraphicsScene. Data is stored in a local SQLite database (`project_data.db`). Only the Project Tree is editable; all other visualizations are generated from the saved data.

## Core Views

| View | Purpose | Editable | Notes |
|------|---------|----------|-------|
| Project Tree | Create / edit / delete project parts and their attributes | YES | Persists immediately to SQLite |
| Gantt Chart | Time‑scaled bar chart with dependencies, hierarchy connectors, critical path, and progress overlays | NO | Hover/click, zoom/pan, fit‑to‑view, baselines overlay |
| Calendar | Month-style placement of items | NO | Read-only snapshot |
| Project Timeline | Linear condensed horizontal timeline | NO | White text theme |
| Progress Dashboard | Aggregated metrics (% complete, risk counts, etc.) | NO | Auto-derived rollups |
| Cost Estimates | Summarize production & installation pricing with totals + deltas vs. saved quote version | NO | Roll-ups, filters, version deltas, column layouts, XLSX export |

## Key Features

- Hierarchical project parts (Phase / Feature / Item) with parent roll‑up of: % Complete, Status
- Weighted progress aggregation (duration-weighted averaging)
- Automatic schema migration (new columns appended without data loss)
- Baseline snapshots (save named snapshots; select one to overlay on the Gantt)
- Working-day end date calculation (skips weekends)
- Weekend and holiday shading (holidays loaded from `holidays.json`)
- Critical path detection & gold highlighting of bars and connectors
- Dependency rendering with L‑shaped routed connectors
- Parent → child fan‑out connectors with animated fade & highlight emphasis
- Distinct styling for trunk vs. child connector segments (dashed vs. solid)
- Hover highlighting: bold label, bar emphasis, connector glow
- Click-to-lock highlight state (toggles off on second click)
- Always-visible external labels to the right of bars with rounded semi‑transparent backgrounds
- Label truncation (32 chars) + tooltip for full text
- Risk visualization: overdue (red outline), at-risk (amber outline) based on schedule slip vs. today
- Progress overlay fill inside each bar (% complete shading)
- Image preview on hover / click for tasks with associated images
- Inline editing dialogs for items via Project Tree
- SQLite persistence with immediate save on change
- PyInstaller build support (spec file present)
- Attachment linking per task with paperclip indicator & thumbnail preview fallback
- Horizontal Project Tree visualization (mirrors web tree layout): left‑to‑right branching node graph with status + % overlays, progress bar strip, hover image preview toggle, and fit/refresh controls
   - Minimap panel with click‑to‑center and smooth animated transitions
   - Collapsible Preview and Minimap panels (state persisted), zero‑height when hidden
   - Export/Settings for the tree view (PNG/PDF) honoring include‑header setting
   - Reset View button to restore default zoom and fit entire scene
   - Clear Cache button for preview images (useful if files change on disk)
- Export Gantt or Timeline to PNG / PDF (scene render) with automatic horizontal PDF pagination and page header image
- Search / jump-to-task field centers & highlights first matching bar
- Filter panel (status, internal/external, responsible substring, critical-only, risk-only) with ancestor auto-include
- Persistent filter settings across sessions (QSettings)
- Critical/risk filters (derived set & overdue/at-risk detection)
- Optional code signing + UPX-compressed distribution
- Conditional data bundling (attachments folder only if present)
- Accessible hover contrast (orange background preserved)

### Collaboration & OneDrive-friendly behavior

- Shared SQLite with safe defaults: WAL mode, busy timeout, and explicit transactions for writers
- Toggle Read-Only Mode to safely browse a shared DB without taking any write locks
- Holidays stored next to the active DB as `holidays.json` so all collaborators see the same calendar
- Tools menu helpers:
   - Switch Data File… writes `db_path.txt` and reloads, overriding the default `project_data.db`
   - Backup Database… creates timestamped copies of the `.db` and any `-wal`/`-shm` sidecar files
   - Reload Data brings in changes that synced while the app was open
   - Sync submenu:
     - Auto-Reload on Sync (Read-Only) – when enabled, the app automatically reloads upon detecting OneDrive updates while in read-only mode
     - Prompt to Reload on Sync (Editing) – when enabled, the app prompts you to reload when updates are detected while editing
     - Change Watch Interval… – lets you set the polling interval for update detection (default 2 seconds)

## Data Model (Selected Fields)

- Project Part (string, unique name)
- Parent (string reference to parent part name; blank = top-level)
- Start Date (MM-DD-YYYY)
- Duration (days) (integer)
- Dependencies (comma-separated list of other Project Part names)
- Type (Phase | Feature | Item or custom)
- % Complete (0–100; auto-rolled for parents)
- Status (Planned | In Progress | Blocked | Done | Deferred)
- Actual Start / Finish Dates (set on status transitions)
- Baseline Start / End Dates (captured automatically once)
- Images (relative path stored; copied into `images/` on upload)
- Production Price (decimal – amount to charge for production work for this part)
- Installation Price (decimal – amount to charge for installation for this part)

### Cost Tracking & Pricing Intelligence

Add production and installation pricing per project part in the Project Tree (Edit dialog). The Cost Estimates view (sidebar) aggregates and analyzes:

- Per-part Production, Installation, and Total ($)
- Profit $, Margin %, price share (% of total)
- Optional parent roll-up (aggregate descendants into parents)
- Delta Price % and Delta Margin points vs. a selected saved Quote Version
- Highlight of top 10% price contributors
- CSV or PDF/PNG export with header/footer branding

Extended internal cost & pricing model (all appended non-destructively):

| Field | Purpose |
|-------|---------|
| Material Cost | Direct materials only |
| Fabrication Labor Hours | Shop hours for production |
| Installation Labor Hours | Field hours for installation |
| Labor Rate | Fabrication blended rate (defaults from Pricing Settings) |
| Install Labor Rate | Field labor rate (defaults from Pricing Settings) |
| Equipment Cost | Equipment / rental allocation |
| Permit/Eng Cost | Permitting or engineering fees |
| Contingency % | Buffer applied to internal cost before margin target pricing suggestion |
| Warranty Reserve % | Portion of price earmarked; affects effective margin shown in suggestions |
| Risk Level | Qualitative (Low / Medium / High) placeholder for future margin adjustments |
| Production Cost | Internal production cost (auto-derived if blank and material + labor provided) |
| Installation Cost | Internal install cost (auto-derived if blank and install hours + equipment/permit provided) |
| Production Price | Charge amount (can apply suggested value) |
| Installation Price | Charge amount |
| Frozen Production/Installation Cost/Price | Snapshot values captured in a Quote Version |
| Quote Version | Current working version label (read-only per row) |

Pricing Suggestions:
- Configured via Tools → Pricing Settings (Target Margin %, Fabrication Labor Rate, Install Labor Rate).
- When editing a part, suggested Production / Installation Prices are computed as: (Internal Cost * (1 + Contingency %)) / (1 - Target Margin).
- If Production or Installation Cost is zero, the app derives it from Material Cost + (Labor Hours * Rate) (+ Equipment + Permit for installation) before suggesting.
- Effective margin after Warranty Reserve % is displayed to show impact on profit.
- Apply buttons let you copy suggested values into the price fields.
 - Risk Level adjusts target margin before suggestion: Low = target −2 pts, High = target +3 pts (clamped 1–95%), with a Risk Adj badge shown when applied.

Quote Versioning & Deltas:
- Use the “Freeze Version…” button in Cost Estimates to snapshot all per-part internal costs & prices (stored in `quote_versions`).
- Select a version from the dropdown to view Δ Price % and Δ Margin pts columns comparing current values to the frozen baseline.
- Multiple versions can be saved; selecting <None> hides deltas.
- Frozen columns in the Edit dialog display per-row snapshot values when present (read-only).
 - Remove an obsolete snapshot with the Delete Version button (action is irreversible).

Exports (Unified Dialog):
- Use the single "Export…" button in Cost Estimates to open a dialog—choose CSV, XLSX, PDF, or PNG.
- CSV: raw tabular data honoring current filters, sort, visible columns, and (optionally) selection subset.
- PDF/PNG: formatted table with optional header banner (`header.svg` preferred, else `header.png`) + standardized footer “© 2025 LSI – For Internal Use Only”. PDF paginates horizontally as needed. Respects Selected Only subset and Include Header toggle.
- XLSX: visible columns only; `_Meta` sheet records timestamp, selected quote version, filters, and Subset (All/Selected). Numeric typing preserved with currency & percent formats applied.
- Selected Only: If enabled (either main checkbox or dialog option), only selected rows export; if no rows are selected it safely falls back to all to avoid empty output.

Column Visibility & Order Layouts:
- Use the Columns… button in the Cost Estimates view to open the management dialog.
- Toggle individual column visibility with the checkboxes (applies immediately).
- Columns can be drag-reordered directly in the table header; the order is captured when you Save Layout.
- Save Layout stores visibility + order under a name (persisted via QSettings, JSON-encoded).
- Apply Layout restores both visibility and order (with a compatibility check on column count).
- Delete Layout removes a saved pattern.
- The last applied layout name is remembered and re-applied automatically on next launch.
 - Programmatic test API: `save_layout_programmatic(name)` and `apply_layout_programmatic(name)` methods (on CostEstimatesView) allow automated round‑trip testing of layout persistence.
 - Partial layout feedback: If a saved layout no longer matches the current column set, the app applies what it can (by matching column names) and reports missing or new columns.

Quote Version Management Enhancements:
- Rename Version button allows retitling an existing snapshot (with overwrite safeguard if the target name exists).
- Overwrite confirmation on Freeze if a version name already exists.

Notes:
- Values stored as REAL/text; schema adds missing columns automatically on upgrade (append-only, safe for existing DBs).
- Roll-up mode aggregates descendants into parents while preserving leaf-only filter option.
- Empty / invalid numeric inputs are treated as 0.00.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Quickstart (Windows)

If you prefer a one-command setup, use the included helper which creates a virtualenv, installs dependencies, and launches the app:

```powershell
./quickstart.ps1
```

Optional parameters:
- `-DbPath "C:\\path\\to\\shared\\project_data.db"` – run against a specific SQLite file (also works with a OneDrive-shared path)
- `-Python "C:\\Path\\To\\python.exe"` – override the Python interpreter if needed

Examples:

```powershell
./quickstart.ps1 -DbPath "C:\\Users\\you\\OneDrive - Org\\Shared\\project_data.db"
./quickstart.ps1 -Python "C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"
```

## Quickstart (macOS / Linux)

Use the shell script to set up a virtualenv and run the app:

```bash
./quickstart.sh --db "/path/to/shared/project_data.db"
```

Options:
- `--db <path>` – optional; writes `db_path.txt` and exports `PROJECT_DB_PATH` for this run
- `--python </path/to/python>` – specify a particular interpreter

If you see Qt platform plugin errors on Linux in a headless environment, set `QT_QPA_PLATFORM=offscreen` when running tests only; the GUI app itself requires an X/Wayland session.

## Running (VS Code Task)

Use the built-in task:

1. Press Ctrl+Shift+P → Run Task → "Run App (PyQt5)"  (or Terminal → Run Task...)
2. Or manually:
   ```powershell
   .venv\Scripts\python.exe main.py
   ```

## Read-only Web Viewer (Flask)

For quick sharing in a browser, a minimal web viewer is included (read-only Gantt):

- Requirements: `Flask` (already listed in `requirements.txt`).
- Uses the same database as the desktop app. It honors `PROJECT_DB_PATH` or a `db_path.txt` file for the SQLite path; otherwise defaults to `project_data.db` in the workspace.

Run locally (VS Code Task):

1. Ctrl+Shift+P → Run Task → "Run Web Viewer (Flask)"
2. Open http://127.0.0.1:5000 in your browser.

Manual run:

```powershell
.venv\Scripts\python.exe .\web\app.py
```

Deployment guides:
- See `DEPLOY.md` for step-by-step instructions for PythonAnywhere and Render, including minimal web-only requirements and start commands.

PythonAnywhere quick setup:
- Create a Manual (Flask) Web App and set a new virtualenv.
- Install deps: `pip install -r ~/Aja_au_Grimace/web/requirements-web.txt`.
- In the WSGI file, paste the contents of `web/pythonanywhere_wsgi.py` (or point to it) which imports `web/app.py`.
- Set environment vars in the PA UI (optional): `PROJECT_DB_PATH=/home/youruser/Aja_au_Grimace/project_data.db`, `WEB_SQLITE_RO=1`.
- Reload, then verify:
   - `/health` → ok
   - `/api/debug` → shows db path, existence, and row count

### Vendoring frontend assets (offline / restricted networks)

The web viewer prefers a local copy of the Gantt JS to avoid flaky CDNs. Place either file in `web/static/vendor/`:

- `frappe-gantt.umd.js` (preferred UMD build) or
- `frappe-gantt.min.js` (minified build)
- Optional styles: `frappe-gantt.css`

If neither JS file exists, the page will try the CDN and, if that fails, falls back to a tiny local stub that shows a preview instead of the interactive chart. You can source the files from a trusted machine and copy them into the folder. The route `/static/vendor/frappe-gantt.umd.js` will serve `.umd.js` if present, else `.min.js`. If `frappe-gantt.css` exists, it's loaded after the fallback CSS and will take precedence.

## Building a Frozen Executable (Windows)

PyInstaller spec files are provided for two build modes:

| Mode | Output | Pros | Cons | When to Use |
|------|--------|------|------|-------------|
| One-dir (default `main.spec`) | `dist/main/` folder with `main.exe`, DLLs, resources | DB & images visible/editable in-place; faster incremental launches | Larger footprint; multiple files to distribute | Shared/synced data (OneDrive), easier debugging |
| One-file (`main_onefile.spec`) | Single `dist/main.exe` (unpacks to temp at runtime) | Single portable file | Internal DB/resources unpacked to temp (changes not in exe); slower first launch | Quick ad‑hoc distribution where persistence lives elsewhere |

Current default is one-dir for better transparency and to allow `project_data.db` to be stored alongside the executable for syncing.

### Manual one-file build (standalone example)
```powershell
python -m PyInstaller --noconfirm --noconsole --onefile --name ProjectManager main.py
```
Output binary: `dist/ProjectManager.exe`

### Using provided specs
```powershell
python -m PyInstaller main.spec          # one-dir (recommended for shared DB)
python -m PyInstaller main_onefile.spec  # one-file
```

If images do not appear in the packaged build, confirm they are collected—adjust the spec's datas list accordingly.

## Collaboration Setup (OneDrive / Microsoft 365)

You can place the SQLite database in a shared OneDrive folder so multiple teammates can view the same data. Recommended workflow:

1. Place `project_data.db` in a OneDrive-backed folder that all collaborators can access.
2. In the desktop app, use Tools → Switch Data File… to point at that DB. This writes `db_path.txt` so the path persists across launches. You can also set `PROJECT_DB_PATH` as an environment variable to override the path.
3. Viewers should enable Tools → Read-Only Mode. Editors can leave it off; the app will guard writes and display an edit lock status.
4. Use Tools → Reload Data to pick up changes that synced from other machines while your app is open.
5. Use Tools → Backup Database… to create timestamped copies of the `.db` (and any `-wal`/`-shm`) in the same folder before risky edits.

Notes:
- The app configures SQLite for collaboration: WAL journal mode, a sane busy timeout, and explicit BEGIN IMMEDIATE transactions for writes.
- Holidays are stored as `holidays.json` next to the active DB so everyone sees the same shading.
- Avoid simultaneous heavy edits from multiple writers; SQLite handles short overlaps, but it is not a multi-master database.

### Deploying to OneDrive (source or packaged)

Two helper scripts are included to make OneDrive sharing easy:

- `run_from_onedrive.ps1` (source): Place the repo folder inside OneDrive. Optionally create a `db_path.txt` in the same folder that contains the full path to your shared `project_data.db`. Then double‑click `run_from_onedrive.ps1` to launch using your local `.venv` if present (falls back to `py -3`/`python.exe`).
- `deploy_onedrive.ps1` (source or onedir): Copies either the source folder or a PyInstaller onedir build into your OneDrive under a chosen app folder name. It can also create a sibling shared data folder with `images/`, `attachments/`, `backups/`, and seed files from `shared_template/`.

Examples (PowerShell):

```powershell
# Copy source into OneDrive and create a shared data folder next to it
./deploy_onedrive.ps1 -OneDrivePath "C:\Users\you\OneDrive - Org" -Mode source -CreateSharedData -CopyDB

# Copy a packaged onedir build into OneDrive
./deploy_onedrive.ps1 -OneDrivePath "C:\Users\you\OneDrive - Org" -Mode onedir
```

Notes:
- When `-CreateSharedData` is used, the script writes `db_path.txt` in the app folder pointing to `<OneDrive>\ProjectPlanner-Shared\project_data.db` so all launches read that DB.
- You can move/rename the shared folder later; just update `db_path.txt`.
- The app also honors the `PROJECT_DB_PATH` environment variable; `run_from_onedrive.ps1` will set it automatically if `db_path.txt` exists.

### Updating an existing OneDrive app folder

Use `update_onedrive.ps1` to sync changes from this repo into your shared OneDrive app folder without re-copying everything:

```powershell
# Dry run first
./update_onedrive.ps1 -OneDriveAppPath "C:\Users\you\OneDrive - Org\ProjectPlanner-App" -Mode source -DryRun

# Perform update and create a backup zip of the previous state
./update_onedrive.ps1 -OneDriveAppPath "C:\Users\you\OneDrive - Org\ProjectPlanner-App" -Mode source -BackupDir "C:\Backups\App"
```

For packaged onedir deployments:

```powershell
./update_onedrive.ps1 -OneDriveAppPath "C:\Users\you\OneDrive - Org\ProjectPlanner-App" -Mode onedir
```

The script preserves any existing `db_path.txt` so users remain pointed at the shared database. A convenience launcher `run_app.ps1` can start a packaged onedir build by autodetecting `dist/main/main.exe` or `dist/main.exe`.

Advanced options (see script help for full list):

```powershell
# Dry run with prune preview and hash-based comparison
./update_onedrive.ps1 -OneDriveAppPath "C:\Users\you\OneDrive - Org\ProjectPlanner-App" -VerboseHash -Prune -DryRun

# Perform sync, create backup archive of changed & deleted files, then prune extraneous files
./update_onedrive.ps1 -OneDriveAppPath "C:\Users\you\OneDrive - Org\ProjectPlanner-App" -BackupDir "C:\Backups\Planner" -Prune

# Include database (rare – only for deliberate reseed) and log
./update_onedrive.ps1 -OneDriveAppPath "C:\Users\you\OneDrive - Org\ProjectPlanner-App" -IncludeDb -IncludeLog
```

Key parameters:
- `-BackupDir <dir|archive.zip>`   Create backup zip of files that would be overwritten/removed.
- `-Prune`                        Remove destination files not present in source (never removes DB/log unless included).
- `-VerboseHash`                  Use SHA256 for change detection (slower, more accurate).
- `-OverwriteUnchanged`           Force copy regardless of size/time/hash.
- `-IncludeDb` / `-IncludeLog`    Opt-in to deploying `project_data.db` / `app.log`.
- `-DeployIgnore <file>`          Alternate ignore file (defaults to root `.deployignore`).

If you routinely update the same destination after an initial `deploy.ps1`, prefer the faster incremental `update_onedrive.ps1` to minimize OneDrive churn.

### Edit Lock (collaborative etiquette)

To reduce accidental concurrent edits on a shared database, the app maintains a lightweight file-based lock next to the database:

- Lock file: `<database>.lock.json` (created in the same folder as the `.db`)
- Contents: `{ owner: "user@host", when: <ISO timestamp>, pid: <process id> }`
- Status bar shows `Lock: —` when no lock is held, or `Lock: user@host @ time` when held

How to use it:
- Turning OFF Tools → Read-Only Mode attempts to acquire the edit lock. If another user holds it, you'll be notified and remain in read-only.
- Turning ON Read-Only Mode releases your lock immediately.
- Tools → Edit Lock → Acquire/Release lets you manage the lock directly.
- The app updates the lock's timestamp periodically while you’re editing, and releases the lock on exit.

Recovery / stale locks:
- If someone crashes or loses power, you may see a stale lock. Coordinate with your teammate first. If confirmed stale, the file `<database>.lock.json` can be deleted to clear the lock.
- There is no forced takeover in-app by design—this keeps the workflow polite and explicit for shared OneDrive folders.

## First-Time Co‑Worker Setup (Onboarding)

When a teammate runs the desktop app and the active database contains no tasks, an onboarding dialog appears (unless they previously chose to hide it). It now offers two focused actions (sample generation removed to avoid accidental seeding of production DBs):

1. Switch Data File… – Open a file picker to point the app at an existing shared `project_data.db` (e.g., inside a OneDrive folder someone else prepared).
2. Open Data Folder – Open the folder that currently holds (or will hold) the active `project_data.db`, so the user can inspect or drop in a database.

Hide option:
- A checkbox ("Don't show this again on empty databases") suppresses the dialog for future launches when empty. You can re‑enable it by deleting the `Onboarding/hide_empty_dialog` key from your system's QSettings store (or resetting application settings) or simply by using the built‑in Tools → Create Sample Data… action whenever needed.

Manual sample data creation:
- Use Tools → Generate Sample Data… to append a small illustrative hierarchy. If rows already exist you'll be prompted to confirm to avoid polluting production data. The action derives costs/prices minimally; you can later adjust or delete sample parts.

Recommended teammate first run:
1. Pull / copy the application (or run the packaged build) locally—not from the OneDrive shared data folder.
2. Launch the app. If the onboarding dialog appears choose Switch Data File… and select the shared `project_data.db` (or Open Data Folder to inspect where local data would live).
3. If they’re only reviewing, enable Tools → Read-Only Mode (should be on by default if another user holds the edit lock).
4. Use Tools → Reload Data periodically (or rely on auto-reload when in read-only) to see incoming changes from collaborators.

What gets persisted:
- The selected DB path (via `db_path.txt` and QSettings) so subsequent launches go straight to the shared data.
- The hide-onboarding preference.
- Read-Only Mode flag, zoom levels, preview/minimap toggles, and filter selections.

To reset onboarding for a user:
- Remove `db_path.txt` (so a new empty local DB is used), and clear the Onboarding QSettings key, or launch with a fresh profile.

Security / integrity note:
- The sample data routine merely inserts tasks; it does not alter existing data other than appending new rows. Always keep backups (Tools → Backup Database…) before large experimental imports.

## Shortcuts & Navigation

- Zoom: Ctrl + Mouse Wheel, or keyboard +/‑ (Zoom In/Out)
- Reset Zoom: Ctrl+0 (or use the Reset View button in the Project Tree)
- Fit to View: button in Gantt and Timeline toolbars
- Fit Selection (Gantt): fits selected bar(s), or the locked/highlighted bar if none selected
- Pan: click‑and‑drag (hand tool)

Zoom level persists per view across sessions.

## Baselines & Business Calendar

- Baselines: Use the Baseline dropdown in the Gantt to select a snapshot to overlay. Click "Save Baseline…" to capture the current schedule as a named snapshot stored in SQLite.
- Holidays: Add date strings (MM‑dd‑YYYY) to `holidays.json` in the app folder to shade non‑working days in the Gantt and Timeline. Weekends are shaded automatically.

## Import / Export CLI

A standalone utility `cli.py` provides JSON / CSV export & import for `project_data.db`.

### Export

```powershell
python cli.py export --out data.json
python cli.py export --format csv --out parts.csv
```

### Import

Modes:
- merge (default): upsert by Project Part (updates existing, inserts new)
- append: insert all rows (duplicates possible)
- replace: delete existing logical rows then insert all

```powershell
python cli.py import --in data.json          # merge inferred JSON
python cli.py import --in parts.csv --mode replace --format csv
python cli.py import --in data.json --mode append --no-backup
```

Automatic backup: For merge/replace a timestamped `project_data.db.bak_YYYYmmdd_HHMMSS` is created unless `--no-backup`.

Arguments:
- `--database path/to/other.db` to operate on a different database file.
- `--format` may be omitted on import if the file extension is `.json` or `.csv`.

Exit codes: 0 success; 2 arg error; 3 IO/validation; 4 unexpected.

## Release Archives (build_release.ps1)

Use the PowerShell helper script `build_release.ps1` to produce a timestamped zip archive containing a staged copy of the PyInstaller build output. Archive naming pattern (new):

```
release_YYYYMMDD_HHMMSS[_vSemVer][_channel][_gitHash].zip
```

Segments:
- `YYYYMMDD_HHMMSS` – build timestamp
- `_vSemVer` – optional when `-Version` is supplied (e.g. `_v0.2.0`)
- `_channel` – optional channel tag (e.g. `_dev`, `_beta`, `_stable`)
- `_gitHash` – short commit hash when git available

Example invocations:
```powershell
./build_release.ps1                                         # basic onedir build + zip
./build_release.ps1 -IncludeCLI -Channel dev                # include cli.py; dev channel
./build_release.ps1 -IncludeManifest -Version 0.2.0         # versioned manifest build
./build_release.ps1 -IncludeDBTemplate -Channel stable -Keep 5
./build_release.ps1 -OneFile -Version 0.2.0 -IncludeCLI     # one-file exe packaged
./build_release.ps1 -ForceKill -SkipClean                   # faster incremental rebuild
```

Supported parameters / switches:
- `-IncludeCLI`          – Copy `cli.py` into the staged folder.
- `-IncludeDBTemplate`   – Copy current `project_data.db` (only do this if it contains seed data you are OK distributing).
- `-IncludeManifest`     – Generate `manifest.json` enumerating every file (path, bytes, sha256).
- `-Channel <tag>`       – Append channel tag to archive name (`dev`, `beta`, `stable`, etc.).
- `-Python <path>`       – Override Python interpreter (auto-resolves sensible defaults otherwise).
- `-OneFile`             – Use `main_onefile.spec` (single exe) instead of default `main.spec` onedir build.
- `-ForceKill`           – Attempt to terminate any running previously built `main.exe` that may lock the file (prevents WinError 5).
- `-SkipClean`           – Skip deleting `build/` and `dist/` for a faster iterative build (useful during rapid iteration).
- `-Version <semver>`    – Embed a `VERSION` file in the archive/staging and insert `_v<semver>` into the archive filename.
- `-Keep <N>`            – After creating the new archive, prune older `release_*.zip` (and matching `.sha256`) keeping only the newest N.

Always produced (no flag needed):
- `<archive>.sha256` – One-line SHA256 checksum file (format: `<hash> *<archiveName>`)

Manifest format (array of objects):
```json
[
   { "path": "main.exe", "bytes": 123456, "sha256": "..." },
   { "path": "README.md", "bytes": 2048, "sha256": "..." }
]
```

### Verifying Integrity

Check the archive hash matches the `.sha256` file:
```powershell
Get-FileHash .\release_20250917_142530_v0.2.0.zip -Algorithm SHA256
Get-Content  .\release_20250917_142530_v0.2.0.zip.sha256
```
Or strict compare:
```powershell
$calc = (Get-FileHash .\release_20250917_142530_v0.2.0.zip -Algorithm SHA256).Hash.ToLower()
$expect = (Get-Content .\release_20250917_142530_v0.2.0.zip.sha256).Split(' ')[0]
if ($calc -ne $expect) { Write-Error 'Checksum mismatch!' } else { 'OK' }
```

### Pruning Older Releases
`-Keep 3` keeps the three newest `release_*.zip` archives and removes older ones plus their `.sha256` companion files.

### Typical Workflow
1. Commit changes (optional, to embed fresh git hash)
2. `./build_release.ps1 -Version 0.2.0 -IncludeManifest -Channel beta -Keep 5`
3. Distribute the resulting zip + `.sha256`
4. Recipient verifies hash, extracts, runs `main.exe`

### One-file Mode Persistence Note
When using the one-file build, PyInstaller unpacks the executable to a temporary folder each run. This project adds a first-run safeguard: if `project_data.db` is NOT present next to the launched `main.exe`, the bundled template DB is copied out, ensuring subsequent edits persist in the external working directory. (Location = the current working directory from which the user launches the exe.) If you distribute with `-IncludeDBTemplate`, that file becomes the initial seed.

### What the Script Does Internally
1. (Optional) Cleans previous build output unless `-SkipClean` is specified.
2. Runs PyInstaller with selected spec (`main.spec` or `main_onefile.spec`). Retries without `--clean` if first attempt fails.
3. Detects layout (onedir vs one-file) and copies artifacts into an ephemeral staging folder.
4. Writes `VERSION` if `-Version` supplied.
5. Copies optional extras (CLI, DB template, README) and generates `manifest.json` if requested.
6. Zips staging contents → `release_...zip`.
7. Computes SHA256 and writes `<archive>.sha256`.
8. Prunes older archives if `-Keep` specified.
9. Prints a summary of top-level staged contents.

Future enhancements (optional): code signing integration (`signtool`), CI workflow (GitHub Actions) building both modes automatically.


## Usage Notes
- Tree view header offers Fit, Refresh, Previews toggle, Export/Settings, Reset View, and Clear Cache.
- Use the Preview/Minimap checkboxes to reclaim vertical space; hidden panels fully collapse.
- If you replace image files on disk and previews don’t update, click Clear Cache.

- Only modify data in the Project Tree. Re-open Gantt / Timeline to refresh visuals after edits.
- Hover a bar to see: bolded label, connector emphasis, potential image preview.
- Click a bar to lock highlight; click again to unlock.
- Tooltips show full Project Part name when truncated.
- Status & % Complete: set leaves manually; parents auto-roll.
- Baselines: captured the first time a start/duration pair is valid; subsequent edits do not back-change the baseline.

## Roadmap / Potential Enhancements
Remaining / Future ideas (completed items removed or relocated above):

- Earned Value Metrics (PV, EV, SV, SPI, CPI) derived from baseline + progress
- Enhanced visibility toggles UI consolidation (single legend-driven menu)
- Undo/redo stack for edits
- Multi-select bulk status updates
- Working-day progress projection heat map / forecast burn-down
- Gray-out (instead of hide) non-matching filter mode
- Timeline view filtering parity & shared filter bus
- Persist dock layout & window geometry
- Modularization (split monolith into packages)
- Automated test harness for critical path & roll-up correctness
- Optional JSON import/export (portable data set)

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| Bars not updating | View not re-rendered | Switch away & back to Gantt or add refresh action |
| Missing images | File not copied or path invalid | Re-upload via Project Tree image cell |
| Frozen build misses resources | Spec not bundling images/db | Edit `main.spec` datas / collect binaries |

## Contributing / Extending

Since the application currently lives mostly in `main.py`, consider future refactors:
- Split into modules: `model.py`, `views/gantt.py`, `views/timeline.py`, `widgets/`, `persistence.py`
- Add tests for progress roll-up & critical path logic.

## License

Internal / proprietary (adjust this section as appropriate).

---

Generated & maintained with assistance from GitHub Copilot Chat.

## Lightweight Deployment / Sync (deploy.ps1)

For quickly pushing an updated working copy (source tree or PyInstaller build output) to a shared folder (e.g. a OneDrive/SharePoint synced location), use the included `deploy.ps1` script.

Typical scenario: you develop locally but need to refresh a shared "consumer" folder that teammates launch from (without giving them your git working copy). `deploy.ps1` copies only relevant runtime files, skipping the live database and log by default.

### Parameters

`-Destination <path>`  (required) Target folder. Created if missing.
`-IncludeDb`            Include `project_data.db` (omit for normal updates to avoid overwriting a live shared DB).
`-IncludeLog`           Include `app.log` (normally excluded).
`-Zip`                  Additionally produce a timestamped zip (next to destination) containing the deployed file set. If `-Destination` ends with `.zip`, creates only that archive (no folder copy).
`-Overwrite`            Force copy even when destination file size/date appear current.
`-Clean`                Remove existing (non‑DB unless `-IncludeDb`) files in the destination before copying.
`-WhatIf`               Dry run (prints planned actions; nothing is modified).

### Example Commands

Dry run (see what would copy):
```powershell
./deploy.ps1 -Destination "C:\Shared\PlannerApp" -WhatIf
```

Deploy (skip DB, safe incremental):
```powershell
./deploy.ps1 -Destination "C:\Shared\PlannerApp"
```

First time seeding (include DB template copy):
```powershell
./deploy.ps1 -Destination "C:\Shared\PlannerApp" -IncludeDb -Overwrite
```

Create a zip archive only (for emailing / manual distribution):
```powershell
./deploy.ps1 -Destination "C:\Shared\planner_release.zip" -Zip
```

Clean + redeploy everything but preserve an already-live DB:
```powershell
./deploy.ps1 -Destination "C:\Shared\PlannerApp" -Clean
```

### Ignoring Files (.deployignore)

You can create a `.deployignore` file in the repository root to exclude paths/patterns from deployment. Wildcards `*` and `?` are supported per PowerShell `-like` semantics. Lines beginning with `#` are comments. A pattern starting with `!` re‑includes a previously excluded path.

Example `.deployignore`:
```
*.pyc
__pycache__/
.venv/
dist/
build/
*.db-shm
*.db-wal
app.log
!project_data.db.template
```

### Safety Notes

- By default the live SQLite database (`project_data.db`) is NOT copied—preventing accidental overwrite of a shared working DB.
- Use `-IncludeDb` only for initial provisioning (or when intentionally replacing with a known seed snapshot after taking a backup).
- `-Clean` never deletes the DB unless you also specify `-IncludeDb` AND the DB will be overwritten; otherwise it is left intact.
- Always keep periodic backups via the in‑app Tools → Backup Database… before large batch updates.

### Conflict Resolution (Optimistic Concurrency)

The application implements row‑level optimistic concurrency for edits originating in the Project Tree. Each project part stores a `row_version` and `last_modified_utc` in the SQLite table. Workflow:

1. When you begin editing a field, the UI remembers the row's current `row_version` (your expected version).
2. On save, an `UPDATE ... WHERE row_version = <expected>` is attempted.
3. If zero rows are affected (another user updated first), a Conflict Resolution dialog appears showing Original, Remote (current DB), and your Pending values for each changed field.
4. Choose:
   - Keep Remote: discard your local changes and refresh.
   - Overwrite Remote: force your pending values (using the new version) and increment `row_version`.
   - Merge & Save: pick Remote or Local per field then save merged result.

Every step (detected conflict, resolution choice, success/failure) is written to `app.log` as structured JSON lines for auditability.

If conflicts occur frequently:
 - Encourage users to enable Read-Only Mode when only browsing.
 - Break large multi-field edits into smaller sequential updates.
 - Verify OneDrive sync latency (occasionally pauses can delay remote visibility).

### Log Review

`app.log` (rotates at ~1MB → `app.log.1`) resides next to the active database. Each line is a JSON object with fields: timestamp (`ts` UTC), user, host, category (e.g. `concurrency`, `db`, `schema`), and event (`update_success`, `conflict`, etc.). Use tools like `jq` or PowerShell's `ConvertFrom-Json` for filtering:

```powershell
Get-Content app.log | Select-String '"category":"concurrency"' | ForEach-Object { $_.ToString() | ConvertFrom-Json }
```

Or just search for conflicts:
```powershell
Select-String -Path app.log -Pattern '"event":"conflict"'
```

### Deployment vs. Release

`deploy.ps1` is intentionally lightweight (fast copy/sync). For formal versioned archives with optional manifest & hashing, continue using `build_release.ps1` (see earlier section). You can chain them:

```powershell
./build_release.ps1 -Version 0.3.0 -IncludeManifest
Expand-Archive release_2025*.zip -DestinationPath .\staging
./deploy.ps1 -Destination "C:\Shared\PlannerApp" -Overwrite -Clean
```

This pattern ensures the shared folder always reflects an exact release artifact.

### Integrating deploy.ps1 and update_onedrive.ps1

Typical lifecycle:
1. First push to a new shared location: `deploy.ps1 -Destination <Folder> -IncludeDb` (seeds structure + optional DB).
2. Subsequent small code/content changes: `update_onedrive.ps1 -OneDriveAppPath <Folder> -DryRun` then run without `-DryRun`.
3. Periodic cleanup & backup: `update_onedrive.ps1 -OneDriveAppPath <Folder> -BackupDir C:\Backups\Planner -Prune`.
4. Formal release: `build_release.ps1 ...` followed by `deploy.ps1 -Destination <Folder> -Clean -Overwrite` (or extract release zip and run update script to prune).

Strategy notes:
- Use `update_onedrive.ps1` for rapid iteration (faster, fine-grained copying).
- Use `deploy.ps1` when you want a fresh canonical snapshot or to produce a zip artifact with identical contents.
- Always check `-DryRun` output before a destructive prune or DB-inclusive action.

