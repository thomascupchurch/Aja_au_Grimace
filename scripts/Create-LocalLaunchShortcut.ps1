<#
.SYNOPSIS
Creates a Desktop shortcut that runs launch_local.ps1 with a fixed shared DB path.

.PARAMETER DbPath
UNC path to the shared project_data.db

.PARAMETER Name
Display name for the shortcut (optional, defaults to "ProjectPlanner (Local Launch)").

.PARAMETER IconPath
Optional .ico to use (defaults to header.ico if present).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$DbPath,
    [string]$Name = 'ProjectPlanner (Local Launch)',
    [string]$IconPath
)

$ErrorActionPreference = 'Stop'

# Resolve repo root and launcher script
$repoRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repoRoot 'launch_local.ps1'
if (-not (Test-Path $launcher)) { throw "launch_local.ps1 not found at $launcher" }

# Compose arguments with quoted DbPath
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcher`" -DbPath `"$DbPath`" -Wait"

# Default icon if not provided
if (-not $IconPath -or $IconPath.Trim().Length -eq 0) {
    $ico = Join-Path -Path $repoRoot -ChildPath 'header.ico'
    if (Test-Path $ico) { $IconPath = $ico }
}

# Create shortcut using the general helper
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop ("$Name.lnk")

# Shortcut targets powershell.exe with arguments to call the launcher
$powershellExe = (Get-Command powershell.exe).Source

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($lnkPath)
$sc.TargetPath = $powershellExe
$sc.Arguments = $arguments
$sc.WorkingDirectory = $repoRoot
if ($IconPath -and (Test-Path $IconPath)) { $sc.IconLocation = $IconPath }
$sc.Save()

Write-Host "Shortcut created:" $lnkPath
