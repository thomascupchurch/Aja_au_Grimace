<#
.SYNOPSIS
    Quickstart script for Windows PowerShell (v5+)
.DESCRIPTION
    Creates/uses a Python virtual environment, installs requirements, and launches the app.
    To avoid OneDrive bloat, you can create a per-user venv outside OneDrive.

.PARAMETER Python
    Optional explicit python executable to use for creating the venv (e.g., C:\Python311\python.exe).
.PARAMETER DbPath
    Optional database path override; sets PROJECT_DB_PATH for this session and persists to db_path.txt.
.PARAMETER UseUserVenv
    If provided, create/use per-user venv at %LocalAppData%\Vols_Signage\venv instead of .venv in the repo.
.PARAMETER UserVenvPath
    Optional override for the per-user venv path. Default: %LocalAppData%\Vols_Signage\venv.
.PARAMETER Help
    Show usage and exit.
#>
param(
        [string]$Python = "",
        [string]$DbPath = "",
        [switch]$UseUserVenv,
        [string]$UserVenvPath = "",
        [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "Usage: .\quickstart.ps1 [-Python <exe>] [-DbPath <path>] [-UseUserVenv] [-UserVenvPath <path>]" -ForegroundColor Yellow
    Write-Host "  -UseUserVenv        Use per-user venv at %LocalAppData%\\Vols_Signage\\venv (or -UserVenvPath)" -ForegroundColor Gray
    Write-Host "  -DbPath <path>      Set PROJECT_DB_PATH and persist to db_path.txt" -ForegroundColor Gray
    return
}

function Resolve-PythonBase {
    param([string]$Preferred)
    if ($Preferred -and (Test-Path $Preferred)) { return $Preferred }
    $candidates = @(
        "py -3",
        "py",
        "python.exe"
    )
    foreach ($c in $candidates) {
        try {
            $ver = & $c -c "import sys;print(sys.version)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver) { return $c }
        } catch {}
    }
    throw "No system Python found. Install Python 3.9+ from https://python.org and re-run."
}

function Get-VenvPythonPath {
    param([string]$VenvRoot)
    return (Join-Path $VenvRoot 'Scripts\python.exe')
}

if ($UseUserVenv -and -not $UserVenvPath) {
    $UserVenvPath = Join-Path $env:LocalAppData 'Vols_Signage\venv'
}

$venvRoot = if ($UseUserVenv) { $UserVenvPath } else { Join-Path $PSScriptRoot '.venv' }
$venvPy = Get-VenvPythonPath -VenvRoot $venvRoot

Write-Host "[1/5] Ensuring virtual environment ($venvRoot)" -ForegroundColor Cyan
if (-not (Test-Path $venvPy)) {
    $pyBase = Resolve-PythonBase -Preferred $Python
    Write-Host "[debug] Using base Python: $pyBase" -ForegroundColor DarkGray
    New-Item -ItemType Directory -Force -Path $venvRoot | Out-Null
    & $pyBase -m venv $venvRoot
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPy)) { throw "Failed to create venv at $venvRoot" }
}
Write-Host "[debug] Venv Python: $venvPy" -ForegroundColor DarkGray

Write-Host "[2/5] Upgrading pip/setuptools/wheel" -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip setuptools wheel | Out-Host

Write-Host "[3/5] Installing requirements" -ForegroundColor Cyan
& $venvPy -m pip install -r "$PSScriptRoot\requirements.txt" | Out-Host

if ($DbPath) {
    Write-Host "[info] Using DB override: $DbPath" -ForegroundColor Yellow
    $env:PROJECT_DB_PATH = $DbPath
    try { Set-Content -Path (Join-Path $PSScriptRoot 'db_path.txt') -Value $DbPath -Encoding UTF8 } catch {}
}

Write-Host "[4/5] Launching app" -ForegroundColor Cyan
& $venvPy "$PSScriptRoot\main.py"

Write-Host "[5/5] Done" -ForegroundColor Green
