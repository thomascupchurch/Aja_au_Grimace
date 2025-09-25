# Project Planner Shared Folder (OneDrive)

This folder is designed to be placed in OneDrive so a small team can view/edit the same project data.

Recommended contents:
- `project_data.db` – SQLite database used by the desktop app
- `holidays.json` – Shared holidays used for weekend/holiday shading
- `images/` – Any task-linked images you want previewed across machines
- `attachments/` – Optional linked files
- `backups/` – Destination for timestamped database backups (optional)

The app will also create/manage:
- `project_data.db.lock.json` – Lightweight edit lock file to coordinate a single active editor
- `project_data.db-wal` / `project_data.db-shm` – SQLite WAL sidecar files (OneDrive will sync them automatically)

## How teammates should wire it up

1. Put this folder in OneDrive and share it with your teammates.
2. Each teammate runs the desktop app locally (not from this folder) and points the app to this DB:
   - In the app: Tools → Switch Data File… → select `project_data.db` in this folder.
   - Or set the env var `PROJECT_DB_PATH` to the full path of this file before launching.
3. Viewers turn on Tools → Read-Only Mode. Editors turn it off to acquire the edit lock.
4. If you see a stale lock, coordinate with the team. The app can prompt for a polite takeover when allowed by settings.

## Backups

Use Tools → Backup Database… to create a timestamped copy placed next to the DB. You can move backups into `backups/` for housekeeping.

## Don’ts

- Don’t store your local virtual environment (`.venv`) or Python caches here.
- Don’t share source code here unless all collaborators are co-developers; prefer Git for code.
