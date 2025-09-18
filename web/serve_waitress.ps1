param(
  [string]$DbPath,
  [int]$Port = 8000,
  [switch]$ReadOnly
)
$ErrorActionPreference = 'Stop'

# Resolve repo and web dir regardless of current working directory
$web = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$repo = Split-Path -Parent $web

if ($DbPath) { $env:PROJECT_DB_PATH = $DbPath }
if ($ReadOnly) { $env:WEB_SQLITE_RO = '1' }

# Pick interpreter (prefer repo venv) - compatible with Windows PowerShell 5.1
$venvPy = Join-Path $repo '.venv/Scripts/python.exe'
if (Test-Path $venvPy) {
  $python = $venvPy
} else {
  $python = 'python'
}

# Ensure waitress is installed in that interpreter (install quietly)
Write-Host "Ensuring 'waitress' is available in $python" -ForegroundColor DarkCyan
& $python -m pip install waitress --quiet | Out-Null

# Set PYTHONPATH to allow importing web.app:app
$env:PYTHONPATH = "$repo;$web"

Write-Host "Starting Waitress on port $Port (web.app:app) using $python" -ForegroundColor Cyan
Push-Location $repo
try {
  & $python -m waitress --listen=0.0.0.0:$Port web.app:app
} finally {
  Pop-Location
}
