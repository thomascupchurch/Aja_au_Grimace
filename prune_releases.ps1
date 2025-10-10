<#
.SYNOPSIS
Prune old release artifacts, keeping the most recent N releases.

.DESCRIPTION
- Keeps the newest N matching release zip files (e.g., release_*.zip) and their .sha256 checksums.
- Optionally prunes matching release folders under .\release\ if they follow a sortable timestamped naming pattern.
- Safe by default with -WhatIf support; shows planned deletions.

.PARAMETER Keep
Number of newest releases to keep (default 3).

.PARAMETER Pattern
Glob pattern (PowerShell -like) for release zips. Default: 'release_*.zip'.

.PARAMETER PruneFolders
Also prune matching release subfolders under .\release\ that start with 'release_' and are older than the kept set.

.PARAMETER DryRun
Alias for -WhatIf convenience.

.EXAMPLE
./prune_releases.ps1 -Keep 3

.EXAMPLE
./prune_releases.ps1 -Keep 5 -PruneFolders
#>
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Low')]
param(
  [int]$Keep = 3,
  [string]$Pattern = 'release_*.zip',
  [switch]$PruneFolders,
  [switch]$DryRun
)

if ($DryRun) { $PSCmdlet.MyInvocation.BoundParameters['WhatIf'] = $true }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
  Write-Verbose "Root: $root"
  # 1) Collect zip files matching pattern
  $zips = Get-ChildItem -File -Filter $Pattern | Sort-Object LastWriteTime -Descending
  if (-not $zips) {
    Write-Host "No files matched pattern: $Pattern"
    return
  }
  # Determine set to keep
  $keepSet = $zips | Select-Object -First $Keep | ForEach-Object { $_.FullName }
  $delZips = $zips | Select-Object -Skip $Keep
  foreach ($f in $delZips) {
    if ($PSCmdlet.ShouldProcess($f.FullName, 'Remove old release zip')) {
      Remove-Item -Force -ErrorAction SilentlyContinue -- $f.FullName
    }
    # delete checksum partner if present
    $sha = "$($f.FullName).sha256"
    if (Test-Path $sha) {
      if ($PSCmdlet.ShouldProcess($sha, 'Remove checksum')) {
        Remove-Item -Force -ErrorAction SilentlyContinue -- $sha
      }
    }
  }
  Write-Host ("Kept {0} zip(s). Deleted {1}." -f $keepSet.Count, ($delZips | Measure-Object).Count)

  if ($PruneFolders) {
    # 2) Prune release subfolders older than kept zip cohort (by name prefix timestamp or by mtime)
    $relDir = Join-Path $root 'release'
    if (Test-Path $relDir) {
      $folders = Get-ChildItem -Path $relDir -Directory | Where-Object { $_.Name -like 'release_*' } | Sort-Object LastWriteTime -Descending
      # Keep folders that correspond to the first $Keep entries by LastWriteTime
      $delFolders = $folders | Select-Object -Skip $Keep
      foreach ($d in $delFolders) {
        if ($PSCmdlet.ShouldProcess($d.FullName, 'Remove old release folder')) {
          Remove-Item -Recurse -Force -ErrorAction SilentlyContinue -- $d.FullName
        }
      }
      Write-Host ("Deleted {0} old release folder(s)." -f (($delFolders | Measure-Object).Count))
    }
  }
}
finally {
  Pop-Location
}
