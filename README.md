# ProjectPlanner

PyQt6/PySide6-based project management application with Gantt charts, timelines, and tree views.

## Features
- ✅ Editable Project Tree view
- ✅ Read-only Gantt chart visualization  
- ✅ Calendar and Timeline views
- ✅ Cross-platform compatibility (Windows/Mac)
- ✅ Export capabilities
- ✅ Multi-user support with read-only mode

## Requirements
- **Python 3.8-3.12** (3.11 recommended for best compatibility)
- PySide6 6.6.3+ (auto-installed) or PyQt6 6.6.1+

## Quick Setup

### Automated Setup (Recommended)
```bash
# Run version-aware setup script
python setup_env.py

# Launch application
python main.py
```

### Manual Setup
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Launch application
python main.py
```

## Building Executables

### Windows
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ProjectPlanner main.py
# Executable created in dist/ProjectPlanner.exe
```

### macOS
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ProjectPlanner main.py
# App bundle created in dist/ProjectPlanner.app
```

## Project Structure
```
ProjectPlanner/
├── main.py              # Main application entry point
├── setup_env.py         # Environment setup script
├── requirements.txt     # Python dependencies
├── VERSION             # Version tracking
├── project_data.db     # SQLite database (created on first run)
├── images/             # Project images and attachments
└── .github/
    └── workflows/
        └── build.yml   # CI/CD build configuration
```

## Migration Status
- ✅ PyQt5 → PyQt6/PySide6 migration complete
- ✅ Python version compatibility checks  
- ✅ Automatic Qt binding detection
- ✅ Cross-platform build workflow
- ✅ Version-locked dependencies
- ✅ Compatibility layer for enum changes

## Usage
1. **First Launch**: App creates `project_data.db` database
2. **Project Tree**: Editable project hierarchy with drag-drop
3. **View Switching**: Toggle between Tree, Gantt, Calendar, Timeline
4. **Multi-user**: Enable read-only mode for viewers
5. **Export**: PDF export with customizable settings

## Troubleshooting
- **Qt import errors**: Run `python setup_env.py` for guided setup
- **Python 3.14+ issues**: Use Python 3.11 for best compatibility  
- **Build failures**: Ensure compatible Python version in CI/CD
- **Database issues**: Delete `project_data.db` to reset (loses data)

## Development
- Auto-detects PySide6 or PyQt6 at runtime
- Backward compatibility layer for PyQt5→PyQt6 migration
- Cross-platform GitHub Actions build workflow
- Comprehensive error handling and logging

## License
Internal LSI Graphics project management tool.

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

