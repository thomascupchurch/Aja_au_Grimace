
param(
  [switch]$OneFile,
  [switch]$DryRun,
  [switch]$PassThru,
  [switch]$Wait
)
$ErrorActionPreference = 'Stop'

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
  Write-Error $_.Exception.Message
  exit 1
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
