# Simple test runner for PyQt5 headless tests
param(
  [string]$Python = ""
)

$ErrorActionPreference = 'Stop'
function Resolve-Python([string]$Preferred) {
  if ($Preferred -and (Test-Path $Preferred)) { return $Preferred }
  $candidates = @(
    "$PSScriptRoot\.venv\Scripts\python.exe",
    "py",
    "python.exe"
  )
  foreach ($c in $candidates) {
    try {
      if ($c -eq 'py') {
        $v = & py -3 -c "import sys;print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) { return 'py' }
      } else {
        $v = & $c -c "import sys;print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) { return $c }
      }
    } catch {}
  }
  throw 'No Python interpreter found.'
}

$py = Resolve-Python $Python
if ($py -ne 'py' -and -not (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe")) {
  Write-Host "[setup] Creating .venv and installing deps" -ForegroundColor Cyan
  & $py -m venv "$PSScriptRoot\.venv"
  $py = "$PSScriptRoot\.venv\Scripts\python.exe"
  & $py -m pip install --upgrade pip setuptools wheel | Out-Host
  & $py -m pip install -r "$PSScriptRoot\requirements.txt" | Out-Host
}

if ($py -eq 'py') {
  py -3 -m pytest -q
} else {
  & $py -m pytest -q
}
