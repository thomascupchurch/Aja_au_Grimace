<#!
.SYNOPSIS
  Convenience wrapper to generate header.ico (and optionally header.icns on macOS) using tools/make_icons.py.
.DESCRIPTION
  Ensures Python + Pillow available, then invokes make_icons.py with desired flags.
  On Windows typically only ICO is produced. On macOS (PowerShell Core) you may use -Icns.
.PARAMETER Force
  Force regeneration even if outputs appear up-to-date.
.PARAMETER Icns
  Also build header.icns (effective only on macOS host with iconutil available).
.PARAMETER Python
  Path to python executable (defaults to .venv/Scripts/python.exe if present, else python on PATH).
.PARAMETER Sizes
  Comma-separated size list (default 16,24,32,48,64,128,256).
.EXAMPLE
  ./tools/make_icons.ps1
.EXAMPLE
  ./tools/make_icons.ps1 -Force -Sizes 16,32,48,256
.EXAMPLE
  ./tools/make_icons.ps1 -Icns (on macOS PowerShell)
#>
param(
  [switch]$Force,
  [switch]$Icns,
  [string]$Python = ".venv/Scripts/python.exe",
  [string]$Sizes = "16,24,32,48,64,128,256"
)
$ErrorActionPreference = 'Stop'
function Resolve-Python {
  param([string]$Candidate)
  if (Test-Path $Candidate) { return (Resolve-Path $Candidate).Path }
  $alts = @('.venv/Scripts/python.exe','python','py')
  foreach ($a in $alts) { if (Get-Command $a -ErrorAction SilentlyContinue) { return $a } }
  throw 'Python not found. Provide -Python explicitly.'
}
$py = Resolve-Python $Python
Write-Host "[make_icons.ps1] Using Python: $py" -ForegroundColor Cyan
# Ensure Pillow
$pillowCheckCmd = "import importlib,sys;sys.exit(0 if importlib.util.find_spec('PIL') else 1)"
& $py -c $pillowCheckCmd 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Installing Pillow..." -ForegroundColor Yellow
  & $py -m pip install --upgrade Pillow
}
$script = Join-Path (Get-Location) 'tools/make_icons.py'
if (-not (Test-Path $script)) { throw "Script not found: $script" }
$argsList = @()
if ($Force) { $argsList += '--force' }
if ($Icns) { $argsList += '--icns' }
if ($Sizes) { $argsList += @('--sizes', $Sizes) }
Write-Host "Invoking: $script $($argsList -join ' ')" -ForegroundColor DarkCyan
& $py $script @argsList
if ($LASTEXITCODE -eq 0) {
  Write-Host "Icons generation complete." -ForegroundColor Green
  if (Test-Path 'header.ico') { (Get-Item 'header.ico') | Select-Object Name,Length | Format-Table | Out-String | Write-Host }
} else {
  Write-Host "Icon generation returned exit code $LASTEXITCODE" -ForegroundColor Red
  exit $LASTEXITCODE
}
