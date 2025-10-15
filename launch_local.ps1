param(
    [string]$DbPath,
    [string]$TargetExe,
    [switch]$Wait,
    [string]$AppArgs
)

# Launch the app by copying the EXE (or onedir) to a per-user cache and running locally.
# Benefits: avoids locking the EXE on the share and speeds startup over slow links.
# Examples:
#   .\launch_local.ps1 -DbPath "\\server\share\ProjectPlanner\project_data.db"
#   .\launch_local.ps1 -TargetExe ".\Vols Signage.exe" -Wait

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[launch] $msg" }
function Test-UncPath($p) { return [bool]($p -match '^[\\\\]{2}') }

# Discover source root and exe
$root = $PSScriptRoot
if (-not $TargetExe) {
    $candidates = @('Vols Signage.exe','main.exe')
    foreach ($c in $candidates) {
        $p = Join-Path $root $c
        if (Test-Path $p) { $TargetExe = $p; break }
    }
}
if (-not $TargetExe) {
    throw "Could not locate target EXE. Use -TargetExe or run from the app folder."
}
$TargetExe = (Resolve-Path $TargetExe).Path
$srcDir = Split-Path $TargetExe -Parent
$exeName = Split-Path $TargetExe -Leaf

# Read optional VERSION next to the exe for stable cache folder naming
$version = $null
$versionFile = Join-Path $srcDir 'VERSION'
if (Test-Path $versionFile) {
    try { $version = (Get-Content -Raw -Encoding UTF8 $versionFile).Trim() } catch { $version = $null }
}
# Build a simple signature from size + mtime to detect changes
$fi = Get-Item $TargetExe
$versionSig = if ([string]::IsNullOrWhiteSpace($version)) { 'noversion' } else { $version }
$sig = "{0}-{1}-{2}" -f $versionSig, $fi.Length, $fi.LastWriteTimeUtc.Ticks
$safeSig = ($sig -replace '[^A-Za-z0-9_.-]','_')

# Cache destination
$cacheBase = Join-Path $env:LOCALAPPDATA 'ProjectPlanner\\RunCache'
if (-not (Test-Path $cacheBase)) { New-Item -ItemType Directory -Path $cacheBase | Out-Null }
$destDir = Join-Path $cacheBase $safeSig
$destExe = Join-Path $destDir $exeName

# Detect onedir vs onefile: if many runtime files live beside exe, treat as onedir
$sideFiles = @(Get-ChildItem -Path $srcDir -File -ErrorAction SilentlyContinue)
$likelyOneDir = $sideFiles.Count -gt 5

# Copy logic: only copy when missing; if exists but signature changed, recopy to a new folder name (safeSig)
if (-not (Test-Path $destDir)) {
    Write-Info "Priming local cache at $destDir"
    New-Item -ItemType Directory -Path $destDir | Out-Null
    if ($likelyOneDir) {
        # Copy entire folder contents (excluding DB/logs)
        $exclude = @('project_data.db*','*.db-wal','*.db-shm','app.log*')
        Write-Info "Copying onedir payload from $srcDir"
        $items = Get-ChildItem -Path $srcDir -Force
        foreach ($it in $items) {
            $dst = Join-Path $destDir $it.Name
            $skip = $false
            foreach ($pat in $exclude) { if ($it.Name -like $pat) { $skip = $true; break } }
            if ($skip) { continue }
            if ($it.PSIsContainer) {
                Copy-Item -Path $it.FullName -Destination $dst -Recurse -Force -ErrorAction Stop
            } else {
                Copy-Item -Path $it.FullName -Destination $dst -Force -ErrorAction Stop
            }
        }
    } else {
        # One-file exe
        Copy-Item -Path $TargetExe -Destination $destExe -Force -ErrorAction Stop
        # Opportunistically copy VERSION for debugging
        if (Test-Path $versionFile) { Copy-Item $versionFile -Destination (Join-Path $destDir 'VERSION') -Force -ErrorAction SilentlyContinue }
    }
} else {
    Write-Info "Using cached app at $destDir"
}

# Environment for the app
if ($DbPath) {
    $env:PROJECT_DB_PATH = $DbPath
    if (Test-UncPath $DbPath) { $env:PROJECTAPP_DB_NETWORK = '1' }
}
# Prefer running with working directory at the cached payload to ensure relative resources resolve
Push-Location $destDir
try {
    if (-not (Test-Path $destExe)) { $destExe = Join-Path $destDir $exeName } # in case onedir copy placed the exe
    if (-not (Test-Path $destExe)) { throw "Cached EXE not found at $destExe" }
    Write-Info "Launching $exeName from cache"
    if ($Wait) {
        if ($AppArgs) { & $destExe $AppArgs } else { & $destExe }
    } else {
        if ($AppArgs) {
            Start-Process -FilePath $destExe -ArgumentList $AppArgs | Out-Null
        } else {
            Start-Process -FilePath $destExe | Out-Null
        }
    }
}
finally {
    Pop-Location
}
