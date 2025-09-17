<#!
.SYNOPSIS
  Build and package a timestamped release archive for the Project Planner.
.DESCRIPTION
  Performs a clean PyInstaller build using main.spec, copies optional extras (cli.py, project_data.db, README.md),
  optionally generates a manifest.json with SHA256 hashes of all packaged files, and creates a zip archive named:
    release_yyyyMMdd_HHmmss[_channel][_gitHash].zip
.PARAMETER IncludeCLI
  Include cli.py utility in the packaged dist prior to zipping.
.PARAMETER IncludeDBTemplate
  Include project_data.db (current state) in the archive (use cautiously if DB contains real data).
.PARAMETER IncludeManifest
  Generate a manifest.json (file list + SHA256 hashes) inside the dist/main folder before zipping.
.PARAMETER Channel
  Optional channel tag (e.g. dev, beta, stable) appended to archive filename.
.PARAMETER Python
  Override path to Python executable (defaults to .venv/Scripts/python.exe).
.EXAMPLE
  ./build_release.ps1
.EXAMPLE
  ./build_release.ps1 -IncludeCLI -Channel dev -IncludeManifest
.EXAMPLE
  ./build_release.ps1 -IncludeCLI -IncludeDBTemplate -Channel stable
.NOTES
  Requires PowerShell 5+ and PyInstaller installed in the selected Python environment.
#>
param(
  [switch]$IncludeCLI,
  [switch]$IncludeDBTemplate,
  [switch]$IncludeManifest,
  [string]$Channel = "",
  [string]$Python = ".venv/Scripts/python.exe",
  [switch]$ForceKill,
  [switch]$SkipClean,
  [switch]$OneFile,
  [string]$Version = "",
  [int]$Keep = 0
)
$ErrorActionPreference = 'Stop'

function Resolve-PythonPath {
  param([string]$PathCandidate)
  if (Test-Path $PathCandidate) { return (Resolve-Path $PathCandidate).Path }
  $alt = @('.venv/Scripts/python.exe','venv/Scripts/python.exe','python.exe','py.exe')
  foreach ($p in $alt) { if (Test-Path $p) { return (Resolve-Path $p).Path } }
  throw "Python executable not found. Specify -Python explicitly."
}

function Get-GitShortHash {
  try { (git rev-parse --short HEAD) 2>$null } catch { return $null }
}

function Write-Section($title) {
  Write-Host "`n=== $title ===" -ForegroundColor Cyan
}

$pythonExe = Resolve-PythonPath ($Python -replace ' ','')
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$hash = Get-GitShortHash
$channelTag = if ($Channel) { "_" + $Channel } else { '' }
$hashTag = if ($hash) { "_" + $hash } else { '' }
$versionTag = if ($Version) { "_v" + ($Version -replace '[^0-9A-Za-z._-]','') } else { '' }
$archiveName = "release_${stamp}${versionTag}${channelTag}${hashTag}.zip"

if (-not $SkipClean) {
  Write-Section "Clean previous build artifacts"
  Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
} else {
  Write-Section "Skip clean (user requested)"
}

Write-Section "Run PyInstaller build"

$specFile = if ($OneFile) { 'main_onefile.spec' } else { 'main.spec' }
if (-not (Test-Path $specFile)) { throw "Spec file '$specFile' not found." }
Write-Host "Using spec: $specFile" -ForegroundColor DarkYellow

# If ForceKill specified, attempt to terminate any running instance of prior exe (common cause of WinError 5)
if ($ForceKill) {
  $possibleExe = Join-Path (Get-Location) 'dist/main.exe'
  $possibleOneDirExe = Join-Path (Get-Location) 'dist/main/main.exe'
  $targets = @($possibleExe,$possibleOneDirExe) | Where-Object { Test-Path $_ }
  if ($targets.Count -gt 0) {
    Write-Host "Attempting to terminate running processes locking previous build..." -ForegroundColor Yellow
    foreach ($t in $targets) {
      Get-Process | Where-Object { $_.Path -eq $t } | ForEach-Object { Write-Host "Killing PID $($_.Id) for $t"; $_ | Stop-Process -Force }
    }
    Start-Sleep -Milliseconds 300
  }
}

Write-Host "Invoking PyInstaller..." -ForegroundColor DarkCyan
$buildLogFile = Join-Path $env:TEMP "build_release_pyinstaller_$(Get-Random).log"
$previousErrorPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
  & $pythonExe -m PyInstaller --clean --noconfirm $specFile 2>&1 | Tee-Object -FilePath $buildLogFile
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    Write-Host "Initial PyInstaller run failed (exit $exitCode). Retrying without --clean..." -ForegroundColor Yellow
  & $pythonExe -m PyInstaller --noconfirm $specFile 2>&1 | Tee-Object -FilePath $buildLogFile
    $exitCode = $LASTEXITCODE
  }
  if ($exitCode -ne 0) {
    Write-Host "PyInstaller failed. Last 40 log lines:" -ForegroundColor Red
    if (Test-Path $buildLogFile) { Get-Content $buildLogFile -Tail 40 | ForEach-Object { Write-Host $_ -ForegroundColor Red } }
    throw "PyInstaller build failed (exit $exitCode)"
  }
} finally {
  $ErrorActionPreference = $previousErrorPreference
}
Write-Host "PyInstaller build succeeded." -ForegroundColor Green

$distRoot = Join-Path (Get-Location) 'dist'

# PyInstaller spec currently builds one-file (main.exe in dist) or one-dir (dist/main/). Detect.
$oneFileExe = Join-Path $distRoot 'main.exe'
$oneDirFolder = Join-Path $distRoot 'main'

$staging = Join-Path (Get-Location) "_stage_main"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

if (Test-Path $oneDirFolder) {
  Write-Host "Detected one-dir build layout (dist/main/)." -ForegroundColor Green
  Copy-Item (Join-Path $oneDirFolder '*') $staging -Recurse -Force
} elseif (Test-Path $oneFileExe) {
  Write-Host "Detected one-file build layout (dist/main.exe)." -ForegroundColor Green
  Copy-Item $oneFileExe (Join-Path $staging 'main.exe')
} else {
  throw "Neither dist/main folder nor dist/main.exe found. Build layout unexpected."
}

if ($Version) {
  Set-Content -Path (Join-Path $staging 'VERSION') -Value $Version -Encoding UTF8
}

if ($IncludeCLI) {
  if (Test-Path 'cli.py') { Copy-Item 'cli.py' $staging }
  else { Write-Warning 'cli.py not found; skipping.' }
}
if ($IncludeDBTemplate) {
  if (Test-Path 'project_data.db') { Copy-Item 'project_data.db' $staging }
  else { Write-Warning 'project_data.db not found; skipping DB template.' }
}
if (Test-Path 'README.md') { Copy-Item 'README.md' $staging }

if ($IncludeManifest) {
  Write-Section "Generate manifest.json"
  $manifest = @()
  Get-ChildItem -Path $staging -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($staging.Length+1)
    $hashObj = Get-FileHash -Algorithm SHA256 -Path $_.FullName
    $manifest += [PSCustomObject]@{
      path = $rel
      bytes = $_.Length
      sha256 = $hashObj.Hash.ToLower()
    }
  }
  $json = $manifest | ConvertTo-Json -Depth 4
  $json | Out-File -FilePath (Join-Path $staging 'manifest.json') -Encoding UTF8
}

Write-Section "Create archive $archiveName"
if (Test-Path $archiveName) { Remove-Item $archiveName -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $archiveName -Force

$sizeKB = [math]::Round(((Get-Item $archiveName).Length / 1KB),2)
Write-Host "Archive created: $archiveName (${sizeKB} KB)" -ForegroundColor Green

# Generate checksum file
Write-Section "Checksum"
$sha = (Get-FileHash -Algorithm SHA256 -Path $archiveName).Hash.ToLower()
$checksumLine = "$sha *$archiveName"
Set-Content -Path "$archiveName.sha256" -Value $checksumLine -Encoding ASCII
Write-Host "SHA256: $sha" -ForegroundColor Green

if ($Keep -gt 0) {
  Write-Section "Prune old releases (keep $Keep)"
  $releases = Get-ChildItem -File -Filter 'release_*.zip' | Sort-Object LastWriteTime -Descending
  $toRemove = $releases | Select-Object -Skip $Keep
  foreach ($r in $toRemove) {
    $hashFile = "$($r.Name).sha256"
    Write-Host "Deleting old release: $($r.Name)" -ForegroundColor DarkYellow
    Remove-Item $r.FullName -Force
    if (Test-Path $hashFile) { Remove-Item $hashFile -Force }
  }
}

Write-Section "Contents (staging top-level)"
Get-ChildItem $staging | Select-Object Name, Length | Format-Table -AutoSize

Write-Section "Done"
Write-Host "Use: Expand-Archive $archiveName -DestinationPath test_release" -ForegroundColor Yellow
Write-Host "(Temporary staging folder '$staging' retained; safe to delete.)" -ForegroundColor DarkGray
