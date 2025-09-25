# Getting Started (Shared Data)

Place this folder in OneDrive and share it with your team. Then either:

Option A – Point your local app at this DB (recommended)
1) Launch the desktop app locally
2) Tools → Switch Data File… → select this folder’s `project_data.db`
3) Toggle Tools → Read-Only Mode ON if you’re just viewing. Toggle OFF to edit (takes lock)

Option B – Environment variable
- Set `PROJECT_DB_PATH` to the full path of `project_data.db` in this folder before launching the app

Notes
- The app uses an edit-lock file to coordinate a single active editor. If a lock looks stale, you may be prompted to take over (configurable).
- Backups: use Tools → Backup Database…; you can keep them in `backups/`.
- Don’t put your `.venv` here; keep virtualenvs local.
