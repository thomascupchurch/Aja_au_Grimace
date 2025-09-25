# Quickstart script for Windows PowerShell (v5+)
# - Creates a local venv in .venv
# - Installs requirements
# - Optionally sets a DB path override (PROJECT_DB_PATH)
# - Launches the app
param(
    [string]$Python = "",
    [string]$DbPath = ""
)

$ErrorActionPreference = "Stop"
function Resolve-Python {
    param([string]$Preferred)
    if ($Preferred -and (Test-Path $Preferred)) { return $Preferred }
    $candidates = @(
        "$PSScriptRoot\.venv\Scripts\python.exe",
        "python.exe",
        "py -3"
    )
    foreach ($c in $candidates) {
        try {
            $ver = & $c -c "import sys;print(sys.version)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver) { return $c }
        } catch {}
    }
    throw "No Python interpreter found. Install Python 3.9+ from https://python.org and re-run."
}

Write-Host "[1/4] Ensuring virtual environment (.venv)" -ForegroundColor Cyan
if (-not (Test-Path "$PSScriptRoot\.venv")) {
    $py = Resolve-Python -Preferred $Python
    & $py -m venv "$PSScriptRoot\.venv"
}

$venvPy = "$PSScriptRoot\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { throw "Virtualenv python not found: $venvPy" }

Write-Host "[2/4] Upgrading pip/setuptools/wheel" -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip setuptools wheel | Out-Host

Write-Host "[3/4] Installing requirements" -ForegroundColor Cyan
& $venvPy -m pip install -r "$PSScriptRoot\requirements.txt" | Out-Host

if ($DbPath) {
    Write-Host "[info] Using DB override: $DbPath" -ForegroundColor Yellow
    $env:PROJECT_DB_PATH = $DbPath
}

Write-Host "[4/4] Launching app" -ForegroundColor Cyan
& $venvPy "$PSScriptRoot\main.py"
