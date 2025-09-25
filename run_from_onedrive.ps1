# Run the app directly from a OneDrive-shared source folder
# - Resolves Python (prefers local .venv if present)
# - Reads db_path.txt if present and sets PROJECT_DB_PATH
# - Launches main.py
param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
function Resolve-Python {
    param([string]$Preferred)
    if ($Preferred -and (Test-Path $Preferred)) { return $Preferred }
    $candidates = @(
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
    throw "No Python interpreter found. Create .venv with quickstart.ps1 or install Python 3.9+."
}

$py = Resolve-Python -Preferred $Python

# If there's a db_path.txt alongside this script, use it
$dbTxt = Join-Path $PSScriptRoot 'db_path.txt'
if (Test-Path $dbTxt) {
    $dbPath = (Get-Content $dbTxt -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($dbPath) {
        Write-Host "[info] PROJECT_DB_PATH from db_path.txt: $dbPath" -ForegroundColor Yellow
        $env:PROJECT_DB_PATH = $dbPath
    }
}

# Launch the app
if ($py -eq 'py') {
    py -3 (Join-Path $PSScriptRoot 'main.py')
} else {
    & $py (Join-Path $PSScriptRoot 'main.py')
}
