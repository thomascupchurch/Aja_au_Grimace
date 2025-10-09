param(
  [switch]$OneFile,
  [switch]$DryRun,
  [switch]$PassThru,
  [switch]$Wait,
  [switch]$Diag,
  [switch]$Source
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

# If -Source is specified, run from source directly
if ($Source) {
  $mainPy = Join-Path (Get-Location) 'main.py'
  if (-not (Test-Path $mainPy)) { Write-Error "main.py not found at $mainPy"; exit 1 }
  $venvPy = "$PSScriptRoot\.venv\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) { Write-Error "Missing .venv. Create with: python -m venv .venv"; exit 1 }
  if ($DryRun) { Write-Host "[dry-run] Would run $venvPy $mainPy"; exit 0 }
  & $venvPy $mainPy
  exit $LASTEXITCODE
}

try {
  $exe = Resolve-AppExe -ForceOneFile:$OneFile
} catch {
  $mainPy = Join-Path (Get-Location) 'main.py'
  if (-not (Test-Path $mainPy)) { Write-Error $_.Exception.Message; exit 1 }
  Write-Warning "No packaged executable; running source."
  $venvPy = "$PSScriptRoot\.venv\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) { Write-Error "Missing .venv. Create with: python -m venv .venv"; exit 1 }
  if ($DryRun) { Write-Host "[dry-run] Would run $venvPy $mainPy"; exit 0 }
  & $venvPy $mainPy
  exit $LASTEXITCODE
}

$exeDir = Split-Path $exe -Parent

# Apply shared DB override BEFORE launching so the child inherits the env var
if (Test-Path '.\shared_db_path.txt') {
  $dbTarget = Get-Content '.\shared_db_path.txt' -Raw
  $env:PROJECT_DB_PATH = $dbTarget.Trim()
  Write-Host "Using shared DB override: $env:PROJECT_DB_PATH" -ForegroundColor Yellow
}

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
  if ($PassThru -or $Wait) {
    if ($Wait) {
      # If waiting, report exit code for diagnostics
      Write-Host "Process exited with code $($p.ExitCode)" -ForegroundColor DarkGray
    }
    return $p
  }
} catch {
  Write-Error "Failed to launch: $($_.Exception.Message)"
  exit 1
}

Write-Host "Hint: run with -Wait to block until the app exits, or -Source to run from Python." -ForegroundColor DarkGray