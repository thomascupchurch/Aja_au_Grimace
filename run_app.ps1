
param(
  [switch]$OneFile,
  [switch]$DryRun,
  [switch]$PassThru,
  [switch]$Wait
)
$ErrorActionPreference = 'Stop'

function Test-PyQt5($python) {
  & $python - <<'PY' 2>$null
try:
    import PyQt5.QtWidgets  # noqa
except Exception as e:
    import sys
    print("PYQT5_IMPORT_ERROR:"+repr(e))
    sys.exit(1)
PY
  return ($LASTEXITCODE -eq 0)
}

function Resolve-AppExe {
  param([switch]$ForceOneFile)
  $root = Get-Location
  $oneDirExe = Join-Path $root 'dist/main/main.exe'
  $oneFileExe = Join-Path $root 'dist/main.exe'
  if ($ForceOneFile) {
    if (Test-Path $oneFileExe) { return $oneFileExe }
    throw 'One-file executable not found (expected dist/main.exe). Build it with build_release.ps1 -OneFile.'
  }
  if (Test-Path $oneDirExe) { return $oneDirExe }
  if (Test-Path $oneFileExe) { return $oneFileExe }
  throw 'No executable found. Run ./build_release.ps1 to create a build first.'
}

try {
  $exe = Resolve-AppExe -ForceOneFile:$OneFile
} catch {
  $mainPy = Join-Path (Get-Location) 'main.py'
  if (Test-Path $mainPy) {
    Write-Warning "No packaged executable; running source."
    $venvPy = "$PSScriptRoot\.venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) { Write-Error "Missing venv interpreter (.venv). Create it first."; exit 1 }
    if (-not (Test-PyQt5 $venvPy)) {
      Write-Error "PyQt5 failed to import. Reinstall with: .\.venv\Scripts\pip.exe install --force-reinstall PyQt5 PyQt5-Qt5 PyQt5-sip"
      exit 1
    }
    if ($DryRun) { Write-Host "[dry-run] Would run $venvPy $mainPy"; exit 0 }
    & $venvPy $mainPy
    exit 0
  } else {
    Write-Error $_.Exception.Message
    exit 1
  }
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
  $proc = Start-Process @startInfo
  if ($PassThru -or $Wait) { return $proc }
} catch {
  Write-Error "Failed to launch: $($_.Exception.Message)"
  exit 1
}