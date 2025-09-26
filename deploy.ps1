<#!
.SYNOPSIS
  Deploy/sync the application to a destination folder (e.g. shared OneDrive/SharePoint sync path).
.DESCRIPTION
  Copies relevant runtime files for the PyQt application to a target folder. By default excludes the live SQLite DB and logs.
  Supports WhatIf dry-run and optional ZIP packaging.
.PARAMETER Destination
  Target folder path. Will be created if missing.
.PARAMETER IncludeDb
  Include the project_data.db file (default: false). Useful for initial seeding, otherwise omit to avoid overwriting shared live DB.
.PARAMETER IncludeLog
  Include app.log (default: false).
.PARAMETER Zip
  Create a versioned ZIP archive instead of (or in addition to) a straight copy. If specified, a zip is created in the parent of Destination (or given path if ends with .zip).
.PARAMETER Overwrite
  Overwrite existing files even if timestamp/size match (default: false).
.PARAMETER WhatIf
  Show planned operations without performing them.
.PARAMETER Clean
  Remove existing non-DB files in destination before copy (careful; skips *.db unless IncludeDb and Overwrite).
.PARAMETER Incremental
  If destination exists, invoke update_onedrive.ps1 for a faster incremental sync (ignores Clean/Overwrite logic here except IncludeDb/IncludeLog flags). Falls back to normal deploy when destination missing.
.EXAMPLE
  ./deploy.ps1 -Destination "C:\Share\AjaApp" -IncludeDb -Overwrite
.EXAMPLE
  ./deploy.ps1 -Destination "C:\Share\AjaApp" -Zip -WhatIf
.NOTES
  Respects optional .deployignore file with glob-style patterns (one per line) to exclude.
  Patterns starting with # are comments. Supports * and ? wildcards. A leading ! negates (re-include) a match.
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)][string]$Destination,
  [switch]$IncludeDb,
  [switch]$IncludeLog,
  [switch]$Zip,
  [switch]$Overwrite,
  [switch]$WhatIf,
  [switch]$Clean,
  [switch]$Incremental,
  [switch]$VerboseHash
)
$ErrorActionPreference = 'Stop'
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Skip($msg){ Write-Host "[SKIP] $msg" -ForegroundColor DarkYellow }
function Write-Do($msg){ Write-Host "[COPY] $msg" -ForegroundColor Green }
function Write-Del($msg){ Write-Host "[DEL ] $msg" -ForegroundColor Red }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Collect source files
$includeExt = @('*.py','*.png','*.svg','*.ico','*.txt','*.md','*.json','*.qml','*.spec')
$alwaysInclude = @('main.py','README.md')
$dbName = 'project_data.db'
$logName = 'app.log'
$ignoreFile = Join-Path $root '.deployignore'
$ignorePatterns = @()
$negatePatterns = @()
if(Test-Path $ignoreFile){
  Get-Content $ignoreFile | ForEach-Object {
    $line = $_.Trim()
    if(-not $line -or $line.StartsWith('#')){ return }
    if($line.StartsWith('!')){ $negatePatterns += $line.Substring(1); return }
    $ignorePatterns += $line
  }
}
function Test-MatchPattern($name, $patterns){
  foreach($p in $patterns){ if($name -like $p){ return $true } }
  return $false
}

if(-not (Test-Path $Destination)){ if($WhatIf){ Write-Info "Would create $Destination" } else { New-Item -ItemType Directory -Force -Path $Destination | Out-Null } }

# Incremental delegation
if($Incremental -and (Test-Path $Destination)){
  Write-Info "Incremental flag set – delegating to update_onedrive.ps1"
  $scriptPath = Join-Path $root 'update_onedrive.ps1'
  if(-not (Test-Path $scriptPath)){
    Write-Info 'update_onedrive.ps1 not found; performing standard deploy instead.'
  } else {
    $args = @('-OneDriveAppPath', $Destination, '-Mode','source')
    if($IncludeDb){ $args += '-IncludeDb' }
    if($IncludeLog){ $args += '-IncludeLog' }
    if($WhatIf){ $args += '-DryRun' }
    if($VerboseHash){ $args += '-VerboseHash' }
    Write-Info ("Calling update_onedrive.ps1 " + ($args -join ' '))
    if($WhatIf){ & powershell -ExecutionPolicy Bypass -File $scriptPath @args }
    else { & powershell -ExecutionPolicy Bypass -File $scriptPath @args }
    Write-Info 'Delegated incremental sync complete.'
    if(-not $Zip){ return } # proceed to zip if requested
  }
}

$files = @()
foreach($ext in $includeExt){ $files += Get-ChildItem -Recurse -File -Filter $ext }
foreach($f in $alwaysInclude){ if(Test-Path $f){ $files += Get-Item $f } }
$files = $files | Sort-Object FullName -Unique

# Filter ignores
$filtered = @()
foreach($f in $files){
  $rel = Resolve-Path -Relative $f.FullName
  $relUnix = $rel -replace '\\','/'
  if(Test-MatchPattern $relUnix $ignorePatterns){
     if(Test-MatchPattern $relUnix $negatePatterns){ $filtered += $f }
     else { Write-Skip "$rel (ignored)" }
     continue
  }
  if((Split-Path $f.FullName -Leaf) -eq $dbName -and -not $IncludeDb){ Write-Skip "$rel (DB excluded)"; continue }
  if((Split-Path $f.FullName -Leaf) -eq $logName -and -not $IncludeLog){ Write-Skip "$rel (log excluded)"; continue }
  $filtered += $f
}

if($Clean){
  Write-Info "Cleaning destination (non-DB files)"
  Get-ChildItem -Path $Destination -Recurse -File | ForEach-Object {
    $leaf = $_.Name
    if($leaf -eq $dbName -and -not $IncludeDb){ return }
    if($leaf -eq $logName -and -not $IncludeLog){ return }
    if($WhatIf){ Write-Del "Would remove $($_.FullName)" }
    else { Remove-Item -Force $_.FullName }
  }
}

# Perform copy
foreach($f in $filtered){
  $relPath = Resolve-Path -Relative $f.FullName
  $destPath = Join-Path $Destination $relPath
  $destDir = Split-Path -Parent $destPath
  if(-not (Test-Path $destDir)){ if(-not $WhatIf){ New-Item -ItemType Directory -Force -Path $destDir | Out-Null } }
  $doCopy = $true
  if((Test-Path $destPath) -and -not $Overwrite){
     $srcInfo = Get-Item $f.FullName
     $dstInfo = Get-Item $destPath
     if($srcInfo.Length -eq $dstInfo.Length -and $srcInfo.LastWriteTimeUtc -le $dstInfo.LastWriteTimeUtc){
        Write-Skip "$relPath (up-to-date)"; $doCopy=$false
     }
  }
  if($doCopy){
    if($WhatIf){ Write-Do "Would copy $relPath" }
    else { Copy-Item -Force $f.FullName $destPath; Write-Do "$relPath" }
  }
}

if($Zip){
  $zipName = if($Destination.ToLower().EndsWith('.zip')){ $Destination } else { Join-Path (Split-Path -Parent $Destination) ( (Split-Path -Leaf $Destination) + (Get-Date -Format '_yyyyMMdd_HHmm') + '.zip') }
  Write-Info "Creating zip: $zipName"
  if($WhatIf){ Write-Info 'Zip skipped (WhatIf)' }
  else {
    if(Test-Path $zipName){ Remove-Item -Force $zipName }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::GetTempPath()) -Name ("deploy_" + [System.Guid]::NewGuid().ToString())
    try {
      $tmpRoot = $tmp.FullName
      foreach($f in $filtered){
        $relPath = Resolve-Path -Relative $f.FullName
        $outPath = Join-Path $tmpRoot $relPath
        $outDir = Split-Path -Parent $outPath
        if(-not (Test-Path $outDir)){ New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
        Copy-Item -Force $f.FullName $outPath
      }
      [System.IO.Compression.ZipFile]::CreateFromDirectory($tmpRoot, $zipName)
      Write-Info "Zip created ($zipName)"
    }
    finally {
      Remove-Item -Recurse -Force $tmp.FullName -ErrorAction SilentlyContinue
    }
  }
}
Write-Info 'Deployment complete.'
