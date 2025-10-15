# Vols Signage App - Update Instructions

## How to Install and Run
1. Download and extract the release zip (e.g., `release_20251014_123853.zip`).
2. Open the extracted folder.
3. Edit `config.env` with your SQL Server details (ask your IT admin if unsure).
4. Double-click `Vols Signage.exe` to start the app.


## How to Update (Automated)
- When a new version is released:
  1. Place the new release zip (e.g., `release_20251014_123853.zip`) in your app folder and rename it to `release_latest.zip`.
  2. Double-click `update.bat`.
     - This will back up your config, extract the new files, restore your config, and launch the app.
  3. Your settings in `config.env` will be preserved.
- If only the configuration changes (e.g., new database info):
  1. Replace `config.env` with the new version.
  2. No need to update the executable unless instructed.

## Troubleshooting
- If the app won’t start, check that your `config.env` is correct and that you have access to the SQL Server.
- For further help, contact your IT admin or the app maintainer.

## Versioning
- Each release zip is named with a date and time (e.g., `release_20251014_123853.zip`).
- You can keep older versions for backup, but only run the latest for best results.

### VERSION file in releases
- Builds now include a `VERSION` file automatically when a `VERSION` file exists in the repository at build time.
- Alternatively, builds include `VERSION` when the build script is invoked with the `-Version` parameter.
- If both are provided, the explicit `-Version` parameter takes precedence.
- The GUI updater uses the `VERSION` file to display/update release versions.

### Release channel tagging
- If `-Channel` is not provided, the build script auto-derives a channel using git state:
  - Exact tag match like `v1.2.3` → `stable`
  - Tags with `beta` or `rc` → `beta`
  - Branch `main`/`master` → `stable`
  - Other branches → `dev`
- Override anytime by passing `-Channel <dev|beta|stable>` explicitly.

## Shared Network Database (SMB/UNC)
- Place `project_data.db` on a proper SMB share (Windows file server). Avoid cloud‑synced folders (OneDrive/SharePoint) for the live writable DB.
- The app coordinates a single active editor with a sidecar lock file: `project_data.db.lock.json`. Only the lock owner can write; others run in read‑only.
- SQLite tuning for shares: the app detects UNC paths and uses `journal_mode=DELETE` and `synchronous=FULL` to reduce corruption risk. Busy timeout is increased.
- Environment overrides (optional):
  - `PROJECTAPP_DB_NETWORK=1` → force network‑safe PRAGMAs even if path isn’t UNC.
  - `PROJECTAPP_SQLITE_WAL=1` → force WAL on network (not recommended).
- Backups: take backups when no editor holds the lock, or use `VACUUM INTO` to create a safe snapshot.
- Executable updates: don’t overwrite a running EXE on the share; publish versioned folders and point users to a stable “current” shortcut.

### Optional: Local-launch helper
To avoid locking the EXE on the share and improve startup speed, use the included launcher to copy the app to a per-user cache and run locally:

PowerShell:
  .\launch_local.ps1 -DbPath "\\server\share\ProjectPlanner\project_data.db" -Wait

Notes:
- The launcher detects new versions (by version file + size/date) and refreshes the cache automatically.
- It sets PROJECT_DB_PATH and flags network mode for safe PRAGMAs when the DB path is UNC.

---
For questions or support, contact: [Your Name/IT Contact]
