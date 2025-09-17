<#!
.SYNOPSIS
  Create a portable zip of the currently built app and data without rebuilding.
.DESCRIPTION
  - If onedir build (dist/main/) exists, zips that entire folder.
  - Else if one-file build (dist/main.exe) exists, zips main.exe + project_data.db + images/ + attachments/ if present.
  Produces portable_YYYYMMDD_HHMMSS.zip in the repo root.
.PARAMETER Quiet
  Reduce output noise.
.EXAMPLE
  ./pack_portable.ps1
#>
param(
  [switch]$Quiet
)
$ErrorActionPreference = 'Stop'
function Write-Info($msg){ if(-not $Quiet){ Write-Host $msg -ForegroundColor Cyan } }

$root = Get-Location
$distMain = Join-Path $root 'dist/main'
$oneFile = Join-Path $root 'dist/main.exe'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$zipName = "portable_${stamp}.zip"

if (Test-Path $zipName) { Remove-Item $zipName -Force }

if (Test-Path $distMain) {
  Write-Info "Zipping onedir dist/main -> $zipName"
  Compress-Archive -Path (Join-Path $distMain '*') -DestinationPath $zipName -Force
} elseif (Test-Path $oneFile) {
  Write-Info "Zipping one-file essentials -> $zipName"
  $temp = Join-Path $root "_portable_stage"
  if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
  New-Item -ItemType Directory -Path $temp | Out-Null
  Copy-Item $oneFile (Join-Path $temp 'main.exe')
  foreach($p in @('project_data.db','images','attachments','README.md')){
    if (Test-Path (Join-Path $root $p)) { Copy-Item (Join-Path $root $p) $temp -Recurse -Force }
  }
  Compress-Archive -Path (Join-Path $temp '*') -DestinationPath $zipName -Force
  Remove-Item $temp -Recurse -Force
} else {
  throw "No build found. Run ./build_release.ps1 first."
}

Write-Info "Created $zipName"
