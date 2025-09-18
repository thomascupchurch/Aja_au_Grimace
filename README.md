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
- Export Gantt or Timeline to PNG / PDF (scene render) with automatic horizontal PDF pagination and page header image
- Search / jump-to-task field centers & highlights first matching bar
- Filter panel (status, internal/external, responsible substring, critical-only, risk-only) with ancestor auto-include
- Persistent filter settings across sessions (QSettings)
- Critical/risk filters (derived set & overdue/at-risk detection)
- Optional code signing + UPX-compressed distribution
- Conditional data bundling (attachments folder only if present)
- Accessible hover contrast (orange background preserved)

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

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

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

PythonAnywhere (notes):
- Create a new Flask app; point WSGI to `web/app.py` and set the working directory to the project folder.
- Ensure `Flask` is installed in the PythonAnywhere virtualenv.
- Configure `PROJECT_DB_PATH` (if using a shared DB) or upload a snapshot `project_data.db` for read-only viewing.
- Static assets load via CDN; optional `header.png` can be served via a static mapping to your workspace file.

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

## Shortcuts & Navigation

- Zoom: Ctrl + Mouse Wheel, or keyboard +/‑ (Zoom In/Out)
- Reset Zoom: Ctrl+0
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
