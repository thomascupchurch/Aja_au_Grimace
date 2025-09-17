# Project Management App

A desktop project planning & visualization tool built with PyQt5 + QGraphicsScene. Data is stored in a local SQLite database (`project_data.db`). Only the Project Tree is editable; all other visualizations are generated from the saved data.

## Core Views

| View | Purpose | Editable | Notes |
|------|---------|----------|-------|
| Project Tree | Create / edit / delete project parts and their attributes | YES | Persists immediately to SQLite |
| Gantt Chart | Time‑scaled bar chart with dependencies, hierarchy connectors, critical path, and progress overlays | NO | Hover & click interactivity |
| Calendar | Month-style placement of items | NO | Read-only snapshot |
| Project Timeline | Linear condensed horizontal timeline | NO | White text theme |
| Progress Dashboard | Aggregated metrics (% complete, risk counts, etc.) | NO | Auto-derived rollups |

## Key Features

- Hierarchical project parts (Phase / Feature / Item) with parent roll‑up of: % Complete, Status
- Weighted progress aggregation (duration-weighted averaging)
- Automatic schema migration (new columns appended without data loss)
- Baseline capture (first valid start/duration snapshot)
- Working-day end date calculation (skips weekends)
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
- Export Gantt or Timeline to PNG / PDF (scene render)
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

1. Press Ctrl+Shift+P → Run Task → "Run Project Management App"  (or Terminal → Run Task...)
2. Or manually:
   ```powershell
   .venv\Scripts\python.exe main.py
   ```

## Building a Frozen Executable (Windows)

PyInstaller spec file `main.spec` is included. Two options:

### 1. One-file build via task
```powershell
python -m PyInstaller --noconfirm --noconsole --onefile --name ProjectManager main.py
```
Output binary: `dist/ProjectManager.exe`

### 2. Using existing spec
```powershell
python -m PyInstaller main.spec
```

If images do not appear in the packaged build, confirm they are collected—adjust the spec's datas list accordingly.

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
