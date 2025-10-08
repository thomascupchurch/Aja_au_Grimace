param(
  [switch]$OneFile,
  [switch]$DryRun,
  [switch]$PassThru,
  [switch]$Wait,
  [switch]$Diag
)
$ErrorActionPreference = 'Stop'

function Resolve-AppExe {
  param([switch]$ForceOneFile)
  $root = Get-Location
  $oneDirExe = Join-Path $root 'dist/main/main.exe'
  $oneFileExe = Join-Path $root 'dist/main.exe'
  if ($ForceOneFile) {
    if (Test-Path $oneFileExe) { return $oneFileExe }
    throw 'One-file executable not found (expected dist/main.exe). Build with build_release.ps1 -OneFile.'
  }
  if (Test-Path $oneDirExe) { return $oneDirExe }
  if (Test-Path $oneFileExe) { return $oneFileExe }
  throw 'No executable found.'
}

function Test-PyQt5($python) {
  $probe = Join-Path $env:TEMP "pyqt_probe_$([System.Guid]::NewGuid().ToString('N')).py"
  @'
import sys, os, traceback
print("=== PYTHON EXEC ===", sys.executable)
print("=== VERSION ===", sys.version.replace("\\n"," "))
print("=== PLATFORM ===", sys.platform)
print("=== FIRST PATH ENTRIES ===", sys.path[:5])
print("=== PATH HEAD ===", os.environ.get("PATH","")[:300])
print("=== TRY IMPORT PYQT5 ===")
try:
    import PyQt5, PyQt5.QtCore, PyQt5.QtWidgets
    print("PYQT5_OK", PyQt5.__file__, PyQt5.QtCore.QT_VERSION_STR)
except Exception as e:
    print("PYQT5_FAIL", type(e).__name__, repr(e))
    traceback.print_exc()
    raise
'@ | Set-Content -Path $probe -Encoding UTF8
  & $python $probe
  $exit = $LASTEXITCODE
  Remove-Item $probe -ErrorAction SilentlyContinue
  return ($exit -eq 0)
}

# MAIN
try {
  $exe = Resolve-AppExe -ForceOneFile:$OneFile
} catch {
  $mainPy = Join-Path (Get-Location) 'main.py'
  if (-not (Test-Path $mainPy)) { Write-Error $_.Exception.Message; exit 1 }
  Write-Warning "No packaged executable; running source."
  $venvPy = "$PSScriptRoot\.venv\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) { Write-Error "Missing .venv. Create with: python -m venv .venv"; exit 1 }

  if ($Diag) {
    Write-Host "Running PyQt5 diagnostics..." -ForegroundColor Cyan
    if (-not (Test-PyQt5 $venvPy)) {
      Write-Error @"
PyQt5 import failed.
Repair steps:
  Remove-Item -Recurse -Force .venv
  (ensure official python.org Python first in PATH)
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\pip.exe install --no-cache-dir --force-reinstall PyQt5 PyQt5-Qt5 PyQt5-sip
"@
      exit 1
    } else {
      Write-Host "PyQt5 OK." -ForegroundColor Green
    }
  }

  if ($DryRun) { Write-Host "[dry-run] Would run $venvPy $mainPy"; exit 0 }
  & $venvPy $mainPy
  exit $LASTEXITCODE
}

$exeDir = Split-Path $exe -Parent
Write-Host "Launcher: using '$exe'" -ForegroundColor Cyan
if ($DryRun) { exit 0 }

$startInfo = @{
  FilePath        = $exe
  WorkingDirectory= $exeDir
}
if ($Wait) { $startInfo.Add('Wait', $true) }
if ($PassThru -or $Wait) { $startInfo.Add('PassThru', $true) }

try {
  $p = Start-Process @startInfo
  if ($PassThru -or $Wait) { return $p }
} catch {
  Write-Error "Failed to launch: $($_.Exception.Message)"
  exit 1
}

if (Test-Path '.\shared_db_path.txt') {
    $dbTarget = Get-Content '.\shared_db_path.txt' -Raw
    $env:PROJECT_DB_PATH = $dbTarget.Trim()
    Write-Host "Using shared DB override: $env:PROJECT_DB_PATH" -ForegroundColor Yellow
}