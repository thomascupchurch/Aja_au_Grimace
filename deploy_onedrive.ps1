param(
    [Parameter(Mandatory=$true)]
    [string]$OneDrivePath,
    [ValidateSet('source','onedir')]
    [string]$Mode = 'source',
    [switch]$CopyDB,
    [switch]$CreateSharedData,
    [string]$AppFolderName = 'ProjectPlanner-App',
    [string]$SharedDataName = 'ProjectPlanner-Shared',
    [string]$Python = ''
)

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

function Copy-IfExists($src, $dst) {
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Recurse -Force
    }
}

if (-not (Test-Path $OneDrivePath)) { throw "OneDrivePath not found: $OneDrivePath" }
$dest = Join-Path $OneDrivePath $AppFolderName
New-Item -ItemType Directory -Force -Path $dest | Out-Null

if ($Mode -eq 'source') {
    Write-Host "[1/3] Copying source files to OneDrive..." -ForegroundColor Cyan
    $include = @(
        'main.py','README.md','requirements.txt','header.png',
        'main.spec','main_onefile.spec','build_release.ps1','quickstart.ps1',
        'run_from_onedrive.ps1'
    )
    foreach ($i in $include) { Copy-IfExists (Join-Path $PSScriptRoot $i) $dest }
    # Optional folders
    foreach ($folder in @('images','web')) { Copy-IfExists (Join-Path $PSScriptRoot $folder) (Join-Path $dest $folder) }

    if ($CreateSharedData) {
        Write-Host "[2/3] Creating shared data folder..." -ForegroundColor Cyan
        $shared = Join-Path $OneDrivePath $SharedDataName
        if (-not (Test-Path $shared)) { New-Item -ItemType Directory -Force -Path $shared | Out-Null }
        foreach ($sub in @('images','attachments','backups')) { New-Item -ItemType Directory -Force -Path (Join-Path $shared $sub) | Out-Null }
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\README_SHARED.md') $shared
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\GETTING_STARTED_SHARED.md') $shared
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\holidays.json') $shared
        if ($CopyDB -and (Test-Path (Join-Path $PSScriptRoot 'project_data.db'))) {
            Copy-Item (Join-Path $PSScriptRoot 'project_data.db') (Join-Path $shared 'project_data.db') -Force
            foreach ($ext in '-wal','-shm') {
                $side = (Join-Path $PSScriptRoot ("project_data.db$ext"))
                if (Test-Path $side) { Copy-Item $side ((Join-Path $shared ("project_data.db$ext"))) -Force }
            }
        }
        # Write db_path.txt in app folder to point to shared DB
        $sharedDb = Join-Path $shared 'project_data.db'
        Set-Content -Path (Join-Path $dest 'db_path.txt') -Value $sharedDb -Encoding UTF8
    } elseif ($CopyDB) {
        Write-Host "[2/3] Copying DB into app/data..." -ForegroundColor Cyan
        $data = Join-Path $dest 'data'
        New-Item -ItemType Directory -Force -Path $data | Out-Null
        if (Test-Path (Join-Path $PSScriptRoot 'project_data.db')) {
            Copy-Item (Join-Path $PSScriptRoot 'project_data.db') (Join-Path $data 'project_data.db') -Force
            foreach ($ext in '-wal','-shm') {
                $side = (Join-Path $PSScriptRoot ("project_data.db$ext"))
                if (Test-Path $side) { Copy-Item $side ((Join-Path $data ("project_data.db$ext"))) -Force }
            }
            # Point to local data folder
            Set-Content -Path (Join-Path $dest 'db_path.txt') -Value (Join-Path $data 'project_data.db') -Encoding UTF8
        }
        Copy-IfExists (Join-Path $PSScriptRoot 'holidays.json') $data
    }
    Write-Host "[3/3] Done. To run from OneDrive use run_from_onedrive.ps1 in $dest" -ForegroundColor Green
} else {
    # onedir mode: copy PyInstaller build
    Write-Host "[1/3] Preparing onedir build..." -ForegroundColor Cyan
    $exePath = Join-Path $PSScriptRoot 'dist\main\main.exe'
    if (-not (Test-Path $exePath)) {
        if (Test-Path (Join-Path $PSScriptRoot 'build_release.ps1')) {
            Write-Host "[info] Building via build_release.ps1 (onedir)" -ForegroundColor Yellow
            & (Join-Path $PSScriptRoot 'build_release.ps1') | Out-Host
        } else {
            $py = Resolve-Python $Python
            Write-Host "[info] Building via PyInstaller main.spec" -ForegroundColor Yellow
            if ($py -eq 'py') {
                & py -3 -m PyInstaller (Join-Path $PSScriptRoot 'main.spec') | Out-Host
            } else {
                & $py -m PyInstaller (Join-Path $PSScriptRoot 'main.spec') | Out-Host
            }
        }
    }
    if (-not (Test-Path $exePath)) { throw 'PyInstaller build not found after attempt.' }
    Write-Host "[2/3] Copying onedir build to OneDrive..." -ForegroundColor Cyan
    $destApp = Join-Path $dest 'main'
    if (Test-Path $destApp) { Remove-Item -Recurse -Force $destApp }
    Copy-Item (Join-Path $PSScriptRoot 'dist\main') $dest -Recurse -Force
    Copy-IfExists (Join-Path $PSScriptRoot 'README.md') $dest
    # Create a small runner
    $runner = @"
# Runs the packaged app from OneDrive
Start-Process -FilePath "`"$(Join-Path $PSScriptRoot 'main\main.exe')`""
"@
    Set-Content -Path (Join-Path $dest 'run_app.ps1') -Value $runner -Encoding UTF8
    Write-Host "[3/3] Done. To run: $($dest)\run_app.ps1" -ForegroundColor Green
}
