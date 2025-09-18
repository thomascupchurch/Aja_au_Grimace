param(
    [string]$DbPath = "\\\\fileserver\\ProjectPlanner\\project_data.db"
)

# Configure the app to use a shared SQLite database over SMB.
# Recommended: keep the app folder read-only for users; place the DB on a separate RW share.
# Usage examples:
#   .\run_shared.ps1 -DbPath "\\server\share\ProjectPlanner\project_data.db"
#   .\run_shared.ps1                                  # uses default above

$ErrorActionPreference = 'Stop'

if (-not $DbPath) {
    Write-Error "DbPath cannot be empty. Provide a UNC path to project_data.db"
    exit 2
}

# Set env var the app reads to find the DB
$env:PROJECT_DB_PATH = $DbPath

# Prefer packaged exe if present, else fall back to venv/python
$exe = Join-Path $PSScriptRoot 'main.exe'
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$script = Join-Path $PSScriptRoot 'main.py'

if (Test-Path $exe) {
    & $exe
} elseif (Test-Path $venvPy) {
    & $venvPy $script
} else {
    # Fallback to system python if available
    python $script
}
