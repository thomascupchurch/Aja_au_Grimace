param(
  [string]$ServiceName = 'GanttViewer',
  [string]$PythonPath,
  [string]$DbPath,
  [int]$Port = 8000,
  [switch]$ReadOnly,
  [string]$NssmPath = 'nssm'
)
$ErrorActionPreference = 'Stop'

# Resolve repo and web dirs
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $scriptDir
$webDir = Join-Path $RepoRoot 'web'

if (-not (Get-Command $NssmPath -ErrorAction SilentlyContinue)) {
  Write-Error "$NssmPath not found in PATH. Install NSSM and retry."
  exit 1
}

# Prefer venv Python if present
if (-not $PythonPath) {
  $venvPy = Join-Path $RepoRoot '.venv/\Scripts/python.exe'
  if (Test-Path $venvPy) { $PythonPath = $venvPy } else { $PythonPath = (Get-Command python).Source }
}

# Install service
& $NssmPath install $ServiceName $PythonPath -m waitress --listen=0.0.0.0:$Port web.app:app
& $NssmPath set $ServiceName AppDirectory $RepoRoot

# Environment extras
if ($DbPath) { & $NssmPath set $ServiceName AppEnvironmentExtra "PROJECT_DB_PATH=$DbPath" }
if ($ReadOnly) { & $NssmPath set $ServiceName AppEnvironmentExtra "WEB_SQLITE_RO=1" }
& $NssmPath set $ServiceName AppEnvironmentExtra "PYTHONPATH=$RepoRoot;$webDir"

Write-Host "Service '$ServiceName' installed. Use 'nssm start $ServiceName' to run." -ForegroundColor Green
