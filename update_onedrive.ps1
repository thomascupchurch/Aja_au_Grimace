<#!
.SYNOPSIS
  Incrementally update an existing deployed application folder in OneDrive (or any target path) from the current workspace.
.DESCRIPTION
  Compares the local source tree (or a PyInstaller onedir build) with the destination app folder and copies only changed / new files.
  Can optionally back up changed/removed files into a timestamped zip or folder, perform a dry run, and skip the live database.

.PARAMETER OneDriveAppPath
  Destination application folder previously deployed (root that contains main.py or dist/ depending on mode).
.PARAMETER Mode
  'source' (default) copies tracked source files (.py, assets) OR 'onedir' to sync contents of dist/main (PyInstaller onedir build).
.PARAMETER BackupDir
  If specified, create a timestamped backup zip of files that will be overwritten or deleted. If value ends with .zip the backup is a single archive. Otherwise a folder is created under BackupDir with timestamp.
.PARAMETER IncludeDb
  Include project_data.db if present (disabled by default to avoid overwriting live DB).
.PARAMETER IncludeLog
  Include app.log (excluded by default).
.PARAMETER Prune
  Remove destination files that do not exist in the source set (ignores DB/log unless inclusion flags provided). Safe dry run first recommended.
.PARAMETER DryRun
  Show planned actions without executing (alias: -WhatIfStyle).
.PARAMETER OverwriteUnchanged
  Force copy even if size & last write time suggest file is unchanged.
.PARAMETER DeployIgnore
  Optional path to a .deployignore file (defaults to repo root .deployignore if found).
.PARAMETER VerboseHash
  Compute SHA256 for more accurate change detection (slower). Without this, uses size+timestamp heuristic unless OverwriteUnchanged.
.PARAMETER Quiet
  Minimal console output (errors and summary only).

.EXAMPLE
  ./update_onedrive.ps1 -OneDriveAppPath "C:\Users\me\OneDrive - Org\PlannerApp" -DryRun
.EXAMPLE
  ./update_onedrive.ps1 -OneDriveAppPath "C:\Users\me\OneDrive - Org\PlannerApp" -BackupDir "C:\Backups\Planner" -Prune
.EXAMPLE
  ./update_onedrive.ps1 -OneDriveAppPath "C:\Users\me\OneDrive - Org\PlannerApp" -Mode onedir -VerboseHash
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)][string]$OneDriveAppPath,
  [ValidateSet('source','onedir')][string]$Mode='source',
  [string]$BackupDir,
  [switch]$IncludeDb,
  [switch]$IncludeLog,
  [switch]$Prune,
  [switch]$DryRun,
  [switch]$OverwriteUnchanged,
  [string]$DeployIgnore,
  [switch]$VerboseHash,
  [switch]$Quiet
)
$ErrorActionPreference='Stop'
function W($msg,$color='Gray'){ if(-not $Quiet){ Write-Host $msg -ForegroundColor $color } }
function Act($msg){ if(-not $Quiet){ Write-Host "[DO] $msg" -ForegroundColor Green } }
function Skip($msg){ if(-not $Quiet){ Write-Host "[==] $msg" -ForegroundColor DarkYellow } }
function Del($msg){ if(-not $Quiet){ Write-Host "[DEL] $msg" -ForegroundColor Red } }
function Err($msg){ Write-Host "[ERR] $msg" -ForegroundColor Red }

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
if(-not (Test-Path $OneDriveAppPath)){ throw "Destination path not found: $OneDriveAppPath" }

# Determine source set
if($Mode -eq 'onedir'){
  $buildRoot = Join-Path $repoRoot 'dist'
  if(-not (Test-Path $buildRoot)){ throw "dist/ not found. Build the onedir package first." }
  $candidates = Get-ChildItem -Path $buildRoot -Recurse -File
} else {
  $patterns = @('*.py','*.png','*.jpg','*.jpeg','*.gif','*.svg','*.ico','*.json','*.md','*.txt','*.csv','*.qml','*.ui')
  $candidates = @()
  foreach($pat in $patterns){ $candidates += Get-ChildItem -Recurse -File -Filter $pat -ErrorAction SilentlyContinue }
  # Always include spec files for reference
  $candidates += Get-ChildItem -Recurse -File -Include *.spec -ErrorAction SilentlyContinue
}
$candidates = $candidates | Sort-Object FullName -Unique

# Load .deployignore
if(-not $DeployIgnore){ $DeployIgnore = Join-Path $repoRoot '.deployignore' }
$ignorePatterns=@(); $negatePatterns=@()
if($DeployIgnore -and (Test-Path $DeployIgnore)){
  Get-Content $DeployIgnore | ForEach-Object {
    $l=$_.Trim(); if(-not $l -or $l.StartsWith('#')){ return }
    if($l.StartsWith('!')){ $negatePatterns += $l.Substring(1); return }
    $ignorePatterns += $l
  }
}
function MatchPattern($rel){ foreach($p in $ignorePatterns){ if($rel -like $p){ return $true } } return $false }
function Negated($rel){ foreach($p in $negatePatterns){ if($rel -like $p){ return $true } } return $false }

$dbName='project_data.db'; $logName='app.log'
$sourceFiles = @()
foreach($f in $candidates){
  $rel = Resolve-Path -Relative $f.FullName
  $relUnix = $rel -replace '\\','/'
  $leaf = Split-Path $rel -Leaf
  if(MatchPattern $relUnix){ if(Negated $relUnix){ } else { Skip "$rel (ignored)"; continue } }
  if($leaf -eq $dbName -and -not $IncludeDb){ Skip "$rel (db excluded)"; continue }
  if($leaf -eq $logName -and -not $IncludeLog){ Skip "$rel (log excluded)"; continue }
  $sourceFiles += [pscustomobject]@{Rel=$relUnix; Full=$f.FullName }
}

# Change detection helpers
function GetHashFast($path){ if($VerboseHash){ return (Get-FileHash -Algorithm SHA256 -Path $path).Hash } else { return '' } }
$destRoot = (Resolve-Path $OneDriveAppPath).Path
$destFilesIndex = @{}
Get-ChildItem -Path $destRoot -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($destRoot.Length)
  # Normalize leading separators (handle both Windows and potential mixed separators)
  while($rel.StartsWith('\') -or $rel.StartsWith('/')){ $rel = $rel.Substring(1) }
  $rel = $rel -replace '\\','/'
  if(-not $rel){ return }
  $destFilesIndex[$rel] = $_
}

$copyPlan=@(); $skipPlan=@(); $overwritePlan=@(); $hashCache=@{}
foreach($sf in $sourceFiles){
  $rel = $sf.Rel
  $destPath = Join-Path $destRoot $rel
  $needCopy=$true
  if(Test-Path $destPath){
    if(-not $OverwriteUnchanged){
      $srcInfo = Get-Item $sf.Full
      $dstInfo = Get-Item $destPath
      if($VerboseHash){
        $srcH = GetHashFast $sf.Full
        $dstH = GetHashFast $destPath
        if($srcH -eq $dstH){ $needCopy=$false; $skipPlan += $rel }
      } else {
        if($srcInfo.Length -eq $dstInfo.Length -and $srcInfo.LastWriteTimeUtc -le $dstInfo.LastWriteTimeUtc){ $needCopy=$false; $skipPlan += $rel }
      }
    }
    if($needCopy){ $overwritePlan += $rel }
  }
  if($needCopy){ $copyPlan += $rel }
}

# Prune plan
$prunePlan=@()
if($Prune){
  foreach($existingRel in $destFilesIndex.Keys){
    if(-not ($sourceFiles.Rel -contains $existingRel)){
      $leaf = Split-Path $existingRel -Leaf
      if(($leaf -eq $dbName -and -not $IncludeDb) -or ($leaf -eq $logName -and -not $IncludeLog)) { continue }
      $prunePlan += $existingRel
    }
  }
}

# Backup if requested
$backupTarget=''
if($BackupDir){
  $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
  if($BackupDir.ToLower().EndsWith('.zip')){
    $backupTarget = $BackupDir
  } else {
    if(-not (Test-Path $BackupDir)){ if(-not $DryRun){ New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null } }
    $backupTarget = Join-Path $BackupDir "update_backup_$timestamp.zip"
  }
  W "Planned backup archive: $backupTarget" Cyan
}

W "Source files: $($sourceFiles.Count)" Cyan
W "Will copy: $($copyPlan.Count) (overwrite: $($overwritePlan.Count))" Cyan
if($Prune){ W "Will prune: $($prunePlan.Count)" Cyan }
if($DryRun){ W "Dry run only (no changes)." Yellow }

if(-not $DryRun -and $BackupDir){
  W "Creating backup..." Cyan
  if(Test-Path $backupTarget){ Remove-Item -Force $backupTarget }
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("upd_" + [guid]::NewGuid())
  New-Item -ItemType Directory -Path $tmpDir | Out-Null
  try {
    foreach($rel in ($overwritePlan + $prunePlan | Sort-Object -Unique)){
      $srcItem = $destFilesIndex[$rel]
      if(-not $srcItem){ continue }
      $outPath = Join-Path $tmpDir $rel
      $outDir = Split-Path -Parent $outPath
      if(-not (Test-Path $outDir)){ New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
      Copy-Item -Force $srcItem.FullName $outPath
    }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($tmpDir, $backupTarget)
    W "Backup archived: $backupTarget" Green
  }
  finally { Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue }
}

if(-not $DryRun){
  foreach($rel in $copyPlan){
    $srcFull = ($sourceFiles | Where-Object { $_.Rel -eq $rel }).Full
    $destPath = Join-Path $destRoot $rel
    $destDir = Split-Path -Parent $destPath
    if(-not (Test-Path $destDir)){ New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -Force $srcFull $destPath
    Act $rel
  }
  if($Prune){
    foreach($rel in $prunePlan){
      $full = Join-Path $destRoot $rel
      if(Test-Path $full){ Remove-Item -Force $full; Del $rel }
    }
  }
} else {
  foreach($rel in $copyPlan){ Act "(dry) $rel" }
  foreach($rel in $prunePlan){ Del "(dry) $rel" }
}

W "Update complete." Green
