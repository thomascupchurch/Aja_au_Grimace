<#
.SYNOPSIS
Creates a Windows .lnk shortcut with an explicit icon (uses header.ico by default).

.EXAMPLE
# Shortcut to a packaged EXE on the Desktop
./scripts/Create-Shortcut.ps1 -TargetPath ".\release\Vols Signage\Vols Signage.exe"

.EXAMPLE
# Shortcut to the launcher script
./scripts/Create-Shortcut.ps1 -TargetPath ".\run_app.ps1" -Name "Vols Signage (Launcher)"

.PARAMETER TargetPath
Path to the executable or script. Can be relative; will be resolved to full path.

.PARAMETER ShortcutPath
Optional explicit .lnk path. Defaults to Desktop with name derived from TargetPath or -Name.

.PARAMETER Name
Display name for the shortcut (without .lnk). Defaults to the target file name without extension.

.PARAMETER IconPath
Optional path to .ico. Defaults to header.ico in repo root when present; otherwise the target's embedded icon is used.

.PARAMETER Arguments
Optional command line arguments to append to TargetPath when launching.

.PARAMETER WorkingDirectory
Optional working directory. Defaults to the target's directory.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$TargetPath,
    [string]$ShortcutPath,
    [string]$Name,
    [string]$IconPath,
    [string]$Arguments,
    [string]$WorkingDirectory
)

# Resolve target
$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedTarget = Resolve-Path -Path $TargetPath -ErrorAction SilentlyContinue
if (-not $resolvedTarget) {
    $candidate = Join-Path -Path $repoRoot -ChildPath $TargetPath
    $resolvedTarget = Resolve-Path -Path $candidate -ErrorAction SilentlyContinue
}
if (-not $resolvedTarget) {
    throw "TargetPath not found: $TargetPath"
}
$resolvedTarget = $resolvedTarget.Path

# Default name
if (-not $Name -or $Name.Trim().Length -eq 0) {
    $Name = [IO.Path]::GetFileNameWithoutExtension($resolvedTarget)
}

# Default shortcut location: Desktop
if (-not $ShortcutPath -or $ShortcutPath.Trim().Length -eq 0) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $ShortcutPath = Join-Path $desktop ("$Name.lnk")
}

# Default working directory
if (-not $WorkingDirectory -or $WorkingDirectory.Trim().Length -eq 0) {
    $WorkingDirectory = Split-Path -Path $resolvedTarget -Parent
}

# Default icon: header.ico in repo root if present
if (-not $IconPath -or $IconPath.Trim().Length -eq 0) {
    $ico = Join-Path -Path $repoRoot -ChildPath 'header.ico'
    if (Test-Path $ico) { $IconPath = $ico }
}

# Create COM shortcut
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($ShortcutPath)
$sc.TargetPath = $resolvedTarget
if ($Arguments) { $sc.Arguments = $Arguments }
$sc.WorkingDirectory = $WorkingDirectory
if ($IconPath -and (Test-Path $IconPath)) { $sc.IconLocation = $IconPath }
$sc.Save()

Write-Host "Shortcut created:" $ShortcutPath
