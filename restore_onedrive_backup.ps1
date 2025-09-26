<#!
.SYNOPSIS
  Restore (or inspect) a backup archive produced by update_onedrive.ps1.
.DESCRIPTION
  Lists available backup zip archives in a given backup directory and can extract one over (or alongside) an existing app folder.
  By default performs a safety validation (ensures target path exists; will not overwrite DB unless -IncludeDb provided).

.PARAMETER BackupDir
  Directory containing backup zip archives named like update_backup_YYYYMMDD_HHMMSS.zip (or custom names).
.PARAMETER List
  Only list available backup archives (sorted newest first) and exit.
.PARAMETER Restore
  File name (or partial prefix) of backup archive to restore (case-insensitive). If omitted with -List, just lists.
.PARAMETER Destination
  Existing application folder to restore into (in-place). If not provided, specify -OutDir to extract into a new folder.
.PARAMETER OutDir
  Alternate output directory (created) receiving extracted contents; cannot combine with in-place Destination restore.
.PARAMETER IncludeDb
  Allow overwrite of project_data.db when restoring.
.PARAMETER IncludeLog
  Allow overwrite of app.log when restoring.
.PARAMETER DryRun
  Show planned operations without changing files.
.PARAMETER KeepExisting
  Do not delete existing files when restoring in-place; only overwrite allowed items.
.PARAMETER Force
  Skip confirmation prompt.

.EXAMPLE
  ./restore_onedrive_backup.ps1 -BackupDir C:\Backups\Planner -List
.EXAMPLE
  ./restore_onedrive_backup.ps1 -BackupDir C:\Backups\Planner -Restore update_backup_20250926_101500.zip -Destination "C:\Users\me\OneDrive - Org\PlannerApp" -IncludeDb -Force
.EXAMPLE
  ./restore_onedrive_backup.ps1 -BackupDir C:\Backups\Planner -Restore 20250926_101500 -OutDir C:\Temp\Recovered
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)][string]$BackupDir,
  [switch]$List,
  [string]$Restore,
  [string]$Destination,
  [string]$OutDir,
  [switch]$IncludeDb,
  [switch]$IncludeLog,
  [switch]$DryRun,
  [switch]$KeepExisting,
  [switch]$Force
)
$ErrorActionPreference='Stop'
function Info($m){ Write-Host $m -ForegroundColor Cyan }
function Warn($m){ Write-Host $m -ForegroundColor Yellow }
function Act($m){ Write-Host $m -ForegroundColor Green }
function Err($m){ Write-Host $m -ForegroundColor Red }

if(-not (Test-Path $BackupDir)){ throw "BackupDir not found: $BackupDir" }
$archives = Get-ChildItem -Path $BackupDir -File -Filter *.zip | Sort-Object LastWriteTime -Descending
if(-not $archives){ Warn "No backup archives found."; return }

if($List -and -not $Restore){
  Info "Found $($archives.Count) archive(s):"
  $i=1; foreach($a in $archives){ Write-Host ("{0,2}. {1}  ({2} bytes)" -f $i,$a.Name,$a.Length) ; $i++ }
  return
}

if(-not $Restore){ throw "Specify -Restore <name or partial> or use -List." }
$match = $archives | Where-Object { $_.Name -like "*$Restore*" } | Select-Object -First 1
if(-not $match){ throw "No archive matching '$Restore'" }
Info "Selected archive: $($match.Name) ($([int]$match.Length) bytes)"

$inPlace = $Destination -and $OutDir
if($inPlace){ throw "Specify only one of -Destination or -OutDir" }
if(-not $Destination -and -not $OutDir){ throw "Provide either -Destination (in-place) or -OutDir (extraction target)." }

if($Destination){
  if(-not (Test-Path $Destination)){ throw "Destination not found: $Destination" }
  if(-not $Force){
    $confirm = Read-Host "Restore into $Destination ? (y/N)"
    if($confirm.ToLower() -ne 'y'){ Warn 'Aborted by user.'; return }
  }
} else {
  if(Test-Path $OutDir){ throw "OutDir already exists: $OutDir" }
  if($DryRun){ Info "[DRY] Would create $OutDir" } else { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$extractTemp = Join-Path ([System.IO.Path]::GetTempPath()) ("restore_" + [guid]::NewGuid())
if($DryRun){ Info "[DRY] Would extract $($match.FullName) -> $extractTemp" } else { New-Item -ItemType Directory -Path $extractTemp | Out-Null; [System.IO.Compression.ZipFile]::ExtractToDirectory($match.FullName, $extractTemp) }

try {
  $candidateRoot = Get-Item $extractTemp
  $files = if(Test-Path $extractTemp){ Get-ChildItem -Path $extractTemp -Recurse -File } else { @() }
  Info "Archive contains $($files.Count) file(s)."
  $dbName='project_data.db'; $logName='app.log'
  if($Destination){
    foreach($f in $files){
      $rel = $f.FullName.Substring($extractTemp.Length).TrimStart('\','/')
      $destPath = Join-Path $Destination $rel
      $destDir = Split-Path -Parent $destPath
      $leaf = Split-Path $destPath -Leaf
      # Skip DB/log unless explicitly included
      if(($leaf -eq $dbName -and -not $IncludeDb) -or ($leaf -eq $logName -and -not $IncludeLog)){
        Warn "Skipping $rel (protected)"; continue
      }
      if(-not (Test-Path $destDir)){ if($DryRun){ Info "[DRY] mkdir $destDir" } else { New-Item -ItemType Directory -Force -Path $destDir | Out-Null } }
      $shouldCopy = $true
      if($KeepExisting -and (Test-Path $destPath)){ $shouldCopy=$false; Warn "KeepExisting: preserving $rel" }
      if($shouldCopy){
        if($DryRun){ Act "[DRY] restore $rel" } else { Copy-Item -Force $f.FullName $destPath; Act "restore $rel" }
      }
    }
  } else {
    # OutDir extraction already created; now move content
    if(-not $DryRun){
      Move-Item -Path (Join-Path $extractTemp '*') -Destination $OutDir -Force
      Act "Extracted to $OutDir"
    } else {
      Info "[DRY] Would move extracted files to $OutDir"
    }
  }
}
finally {
  if(-not $DryRun){ Remove-Item -Recurse -Force $extractTemp -ErrorAction SilentlyContinue }
}

Info 'Restore complete.'
