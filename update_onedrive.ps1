param(
  [Parameter(Mandatory=$true)]
  [string]$OneDriveAppPath,
  [ValidateSet('source','onedir')]
  [string]$Mode = 'source',
  [switch]$DryRun,
  [string]$BackupDir = '',
  [string]$Python = ''
)

# Incrementally update the OneDrive app folder from the current repo
# - Preserves db_path.txt if present
# - Skips transient/build folders and venv
# - Optional backup (pre-sync snapshot)
# - For 'onedir' mode, rebuilds if dist/main missing or when -Rebuild is provided

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

function New-Timestamp { (Get-Date).ToString('yyyyMMdd_HHmmss') }

function Copy-Incremental($src, $dst, $include, $exclude, [switch]$WhatIf) {
  if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Force -Path $dst | Out-Null }
  $srcResolved = (Resolve-Path $src).Path
  if (-not $srcResolved.EndsWith('\')) { $srcResolved += '\' }
  $filterScript = {
    param($path)
    foreach ($pat in $exclude) { if ($path -like $pat) { return $false } }
    if ($include.Count -eq 0) { return $true }
    foreach ($pat in $include) { if ($path -like $pat) { return $true } }
    return $false
  }
  Get-ChildItem -Path $srcResolved -Recurse -Force | ForEach-Object {
    $rel = $_.FullName.Substring($srcResolved.Length)
    $rel = $rel.TrimStart([char[]]"\\/")
    if (& $filterScript $rel) {
      $target = Join-Path $dst $rel
      if ($_.PSIsContainer) {
        if (-not (Test-Path $target)) {
          if ($WhatIf) { Write-Host "[DRY] mkdir $target" }
          else { New-Item -ItemType Directory -Force -Path $target | Out-Null }
        }
      } else {
        $doCopy = $true
        if (Test-Path $target) {
          $srcInfo = Get-Item $_.FullName
          $dstInfo = Get-Item $target
          if ($srcInfo.Length -eq $dstInfo.Length -and $srcInfo.LastWriteTimeUtc -eq $dstInfo.LastWriteTimeUtc) { $doCopy = $false }
        }
        if ($doCopy) {
          if ($WhatIf) { Write-Host "[DRY] copy $rel" }
          else { Copy-Item $_.FullName -Destination $target -Force }
        }
      }
    }
  }
}

if (-not (Test-Path $OneDriveAppPath)) { throw "OneDrive app path not found: $OneDriveAppPath" }

# Preserve db_path.txt if present
$dbPathFile = Join-Path $OneDriveAppPath 'db_path.txt'
$dbPathVal = ''
if (Test-Path $dbPathFile) { $dbPathVal = (Get-Content $dbPathFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim() }

# Optional backup
if ($BackupDir) {
  $stamp = New-Timestamp
  $backup = Join-Path $BackupDir ("onedrive_app_backup_$stamp.zip")
  if ($DryRun) { Write-Host "[DRY] backup -> $backup" }
  else {
    if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($OneDriveAppPath, $backup)
    Write-Host "[backup] $backup" -ForegroundColor Yellow
  }
}

$srcRoot = $PSScriptRoot
$exclude = @(
  'dist*','build*','.venv*','__pycache__*','*.pyc','*.pyo','.git*','release_*.zip','*.sha256','*.spec' # include main.spec via list below
)
$include = @(
  'main.py','README.md','requirements.txt','header.png','header.svg','main.spec','quickstart.ps1','quickstart.sh','run_app.ps1','run_from_onedrive.ps1','deploy_onedrive.ps1','update_onedrive.ps1','shared_template*','web*','images*','VERSION','project_data.db'
)

if ($Mode -eq 'source') {
  Write-Host "[sync] Updating source files -> $OneDriveAppPath" -ForegroundColor Cyan
  Copy-Incremental -src $srcRoot -dst $OneDriveAppPath -include $include -exclude $exclude -WhatIf:$DryRun
  if ($dbPathVal) { Set-Content -Path $dbPathFile -Value $dbPathVal -Encoding UTF8 }
  Write-Host "[done]" -ForegroundColor Green
} else {
  # onedir: ensure dist/main exists; build if needed
  $exe = Join-Path $srcRoot 'dist\main\main.exe'
  if (-not (Test-Path $exe)) {
    Write-Host "[build] Creating onedir build via main.spec" -ForegroundColor Yellow
    $py = Resolve-Python $Python
    if ($py -eq 'py') { py -3 -m PyInstaller (Join-Path $srcRoot 'main.spec') } else { & $py -m PyInstaller (Join-Path $srcRoot 'main.spec') }
  }
  if (-not (Test-Path $exe)) { throw 'PyInstaller build not found after attempt.' }
  $destApp = Join-Path $OneDriveAppPath 'main'
  if ($DryRun) { Write-Host "[DRY] replace $destApp with dist/main" }
  else {
    if (Test-Path $destApp) { Remove-Item -Recurse -Force $destApp }
    Copy-Item (Join-Path $srcRoot 'dist\main') $OneDriveAppPath -Recurse -Force
  }
  # Also copy launcher if present
  $launcher = Join-Path $srcRoot 'run_app.ps1'
  if (Test-Path $launcher) { Copy-Item $launcher $OneDriveAppPath -Force }
  # Restore db_path.txt
  if ($dbPathVal) { Set-Content -Path $dbPathFile -Value $dbPathVal -Encoding UTF8 }
  Write-Host "[done]" -ForegroundColor Green
}
