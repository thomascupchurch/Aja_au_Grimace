# Run the app directly from a OneDrive-shared source folder
# Interpreter search order (to avoid syncing huge .venv into OneDrive):
#   1) Per-user venv at %LocalAppData%\Vols_Signage\venv\Scripts\python.exe
#   2) Adjacent .venv (repo-local) \Scripts\python.exe (not recommended on OneDrive)
#   3) 'py' launcher
#   4) system 'python.exe'
# - Reads db_path.txt if present and sets PROJECT_DB_PATH
# - Launches main.py
param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
function Resolve-Python {
    param([string]$Preferred)
    if ($Preferred -and (Test-Path $Preferred)) { return $Preferred }
    # Prefer a per-user venv outside OneDrive to reduce sync size
    $userVenv = Join-Path $env:LocalAppData 'Vols_Signage\venv\Scripts\python.exe'
    $candidates = @(
        $userVenv,
        "$PSScriptRoot\.venv\Scripts\python.exe",
        "py",
        "python.exe"
    )
    foreach ($c in $candidates) {
        try {
            if ($c -eq 'py') {
                $ver = & py -3 -c "import sys;print(sys.version)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) { return 'py' }
            } else {
                $ver = & $c -c "import sys;print(sys.version)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) { return $c }
            }
        } catch {}
    }
    throw "No Python interpreter found. Create a per-user venv at %LocalAppData%\\Vols_Signage\\venv or install Python 3.9+."
}

$py = Resolve-Python -Preferred $Python
if ($py -eq 'py') {
    try { $resolved = (& py -3 -c "import sys;print(sys.executable)" 2>$null) } catch { $resolved='' }
    if ($resolved) { Write-Host "[info] Interpreter: py -3 ($resolved)" -ForegroundColor DarkGray } else { Write-Host "[info] Interpreter: py -3" -ForegroundColor DarkGray }
} else {
    Write-Host "[info] Interpreter: $py" -ForegroundColor DarkGray
}

# If there's a db_path.txt alongside this script, use it
$dbTxt = Join-Path $PSScriptRoot 'db_path.txt'
if (Test-Path $dbTxt) {
    $raw = (Get-Content $dbTxt -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($raw) {
        if ([System.IO.Path]::IsPathRooted($raw)) {
            $dbResolved = $raw
        } else {
            $dbResolved = (Join-Path $PSScriptRoot $raw)
        }
        try { $dbResolved = (Resolve-Path $dbResolved -ErrorAction Stop).Path } catch {}
        Write-Host "[info] PROJECT_DB_PATH from db_path.txt: $dbResolved" -ForegroundColor Yellow
        $env:PROJECT_DB_PATH = $dbResolved
    }
}

# Launch the app
if ($py -eq 'py') {
    py -3 (Join-Path $PSScriptRoot 'main.py')
} else {
    & $py (Join-Path $PSScriptRoot 'main.py')
}
