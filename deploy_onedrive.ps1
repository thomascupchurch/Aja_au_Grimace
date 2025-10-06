param(
    [Parameter(Mandatory = $true)]
    [string]$OneDrivePath,
    [ValidateSet('source','onedir')]
    [string]$Mode = 'source',
    [switch]$CopyDB,
    [switch]$CreateSharedData,
    [switch]$IncludeRunApp,      # copy run_app.ps1 in source mode
    [switch]$IncludeDevReqs,     # copy requirements-dev.txt if present
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
                & py -3 -c "import sys" 2>$null
                if ($LASTEXITCODE -eq 0) { return 'py' }
            } else {
                & $c -c "import sys" 2>$null
                if ($LASTEXITCODE -eq 0) { return $c }
            }
        } catch {}
    }
    throw "No Python interpreter found."
}

function Copy-IfExists($src, $dst) {
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Recurse -Force
    }
}

if (-not (Test-Path $OneDrivePath)) {
    throw "OneDrivePath not found: $OneDrivePath"
}

$dest = Join-Path $OneDrivePath $AppFolderName
New-Item -ItemType Directory -Force -Path $dest | Out-Null

if ($Mode -eq 'source') {
    Write-Host '[1/3] Copying source files...' -ForegroundColor Cyan
    $include = @(
        'main.py','README.md','requirements.txt','header.png',
        'main.spec','main_onefile.spec','build_release.ps1','quickstart.ps1',
        'run_from_onedrive.ps1'
    )
    if ($IncludeRunApp -and (Test-Path (Join-Path $PSScriptRoot 'run_app.ps1'))) {
        $include += 'run_app.ps1'
    }
    if ($IncludeDevReqs -and (Test-Path (Join-Path $PSScriptRoot 'requirements-dev.txt'))) {
        $include += 'requirements-dev.txt'
    }
    foreach ($i in $include) { Copy-IfExists (Join-Path $PSScriptRoot $i) $dest }
    foreach ($folder in @('images','web')) {
        Copy-IfExists (Join-Path $PSScriptRoot $folder) (Join-Path $dest $folder)
    }

    if (Test-Path (Join-Path $dest '.venv')) {
        Write-Warning "A .venv exists in destination (remove it to reduce sync size)."
    }

    # Shared data (preferred for multi-user)
    if ($CreateSharedData) {
        Write-Host '[2/3] Creating shared data folder...' -ForegroundColor Cyan
        $shared = Join-Path $OneDrivePath $SharedDataName
        if (-not (Test-Path $shared)) {
            New-Item -ItemType Directory -Force -Path $shared | Out-Null
        }
        foreach ($sub in @('images','attachments','backups')) {
            New-Item -ItemType Directory -Force -Path (Join-Path $shared $sub) | Out-Null
        }
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\README_SHARED.md') $shared
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\GETTING_STARTED_SHARED.md') $shared
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\holidays.json') $shared

        if ($CopyDB -and (Test-Path (Join-Path $PSScriptRoot 'project_data.db'))) {
            Copy-Item (Join-Path $PSScriptRoot 'project_data.db') (Join-Path $shared 'project_data.db') -Force
            foreach ($ext in '-wal','-shm') {
                $side = Join-Path $PSScriptRoot ("project_data.db$ext")
                if (Test-Path $side) {
                    Copy-Item $side (Join-Path $shared ("project_data.db$ext")) -Force
                }
            }
        }
        Set-Content -Path (Join-Path $dest 'db_path.txt') -Value (Join-Path $shared 'project_data.db') -Encoding UTF8
        Write-Host '[3/3] Source deployment complete (shared data).' -ForegroundColor Green

    } elseif ($CopyDB) {
        Write-Host '[2/3] Copying local DB into app folder...' -ForegroundColor Cyan
        if (Test-Path (Join-Path $PSScriptRoot 'project_data.db')) {
            Copy-Item (Join-Path $PSScriptRoot 'project_data.db') (Join-Path $dest 'project_data.db') -Force
            foreach ($ext in '-wal','-shm') {
                $side = Join-Path $PSScriptRoot ("project_data.db$ext")
                if (Test-Path $side) {
                    Copy-Item $side (Join-Path $dest ("project_data.db$ext")) -Force
                }
            }
            Set-Content -Path (Join-Path $dest 'db_path.txt') -Value (Join-Path $dest 'project_data.db') -Encoding UTF8
        } else {
            Write-Warning 'No project_data.db found to copy.'
        }
        Write-Host '[3/3] Source deployment complete (local DB).' -ForegroundColor Green
    } else {
        Write-Host '[2/3] No DB action requested.' -ForegroundColor Yellow
        Write-Host '[3/3] Source deployment complete.' -ForegroundColor Green
    }

} else {
    Write-Host '[1/5] Preparing onedir build...' -ForegroundColor Cyan
    $exePath = Join-Path $PSScriptRoot 'dist\main\main.exe'
    if (-not (Test-Path $exePath)) {
        if (Test-Path (Join-Path $PSScriptRoot 'build_release.ps1')) {
            Write-Host '[info] Building via build_release.ps1 (onedir)' -ForegroundColor Yellow
            & (Join-Path $PSScriptRoot 'build_release.ps1') | Out-Host
        } else {
            $py = Resolve-Python $Python
            Write-Host '[info] Ensuring PyInstaller installed...' -ForegroundColor Cyan
            if ($py -eq 'py') {
                & py -3 -m pip show PyInstaller 1>$null 2>$null; if ($LASTEXITCODE -ne 0) { & py -3 -m pip install PyInstaller }
                & py -3 -m PyInstaller (Join-Path $PSScriptRoot 'main.spec') | Out-Host
            } else {
                & $py -m pip show PyInstaller 1>$null 2>$null; if ($LASTEXITCODE -ne 0) { & $py -m pip install PyInstaller }
                & $py -m PyInstaller (Join-Path $PSScriptRoot 'main.spec') | Out-Host
            }
        }
    }
    if (-not (Test-Path $exePath)) { throw 'PyInstaller build not found after attempt.' }

    Write-Host '[2/5] Copying onedir build...' -ForegroundColor Cyan
    $destApp = Join-Path $dest 'main'
    if (Test-Path $destApp) { Remove-Item -Recurse -Force $destApp }
    Copy-Item (Join-Path $PSScriptRoot 'dist\main') $dest -Recurse -Force

    Write-Host '[3/5] Copying supplemental files...' -ForegroundColor Cyan
    Copy-IfExists (Join-Path $PSScriptRoot 'README.md') $dest
    if ($IncludeDevReqs -and (Test-Path (Join-Path $PSScriptRoot 'requirements-dev.txt'))) {
        Copy-Item (Join-Path $PSScriptRoot 'requirements-dev.txt') $dest -Force
    }
    if (Test-Path (Join-Path $PSScriptRoot 'requirements.txt')) {
        Copy-Item (Join-Path $PSScriptRoot 'requirements.txt') $dest -Force
    }

    if ($CreateSharedData) {
        Write-Host '[4/5] Creating shared data folder...' -ForegroundColor Cyan
        $shared = Join-Path $OneDrivePath $SharedDataName
        if (-not (Test-Path $shared)) { New-Item -ItemType Directory -Force -Path $shared | Out-Null }
        foreach ($sub in @('images','attachments','backups')) {
            New-Item -ItemType Directory -Force -Path (Join-Path $shared $sub) | Out-Null
        }
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\README_SHARED.md') $shared
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\GETTING_STARTED_SHARED.md') $shared
        Copy-IfExists (Join-Path $PSScriptRoot 'shared_template\holidays.json') $shared
        if ($CopyDB -and (Test-Path (Join-Path $PSScriptRoot 'project_data.db'))) {
            Copy-Item (Join-Path $PSScriptRoot 'project_data.db') (Join-Path $shared 'project_data.db') -Force
            foreach ($ext in '-wal','-shm') {
                $side = Join-Path $PSScriptRoot ("project_data.db$ext")
                if (Test-Path $side) { Copy-Item $side (Join-Path $shared ("project_data.db$ext")) -Force }
            }
        }
        Set-Content -Path (Join-Path $dest 'db_path.txt') -Value (Join-Path $shared 'project_data.db') -Encoding UTF8
    } elseif ($CopyDB) {
        Write-Host '[4/5] Copying DB locally into onedir app data...' -ForegroundColor Cyan
        $data = Join-Path $dest 'data'
        New-Item -ItemType Directory -Force -Path $data | Out-Null
        if (Test-Path (Join-Path $PSScriptRoot 'project_data.db')) {
            Copy-Item (Join-Path $PSScriptRoot 'project_data.db') (Join-Path $data 'project_data.db') -Force
            foreach ($ext in '-wal','-shm') {
                $side = Join-Path $PSScriptRoot ("project_data.db$ext")
                if (Test-Path $side) { Copy-Item $side (Join-Path $data ("project_data.db$ext")) -Force }
            }
            Set-Content -Path (Join-Path $dest 'db_path.txt') -Value (Join-Path $data 'project_data.db') -Encoding UTF8
        } else {
            Write-Warning 'No project_data.db found to copy.'
        }
        Copy-IfExists (Join-Path $PSScriptRoot 'holidays.json') $data
    } else {
        Write-Host '[4/5] Skipping DB handling.' -ForegroundColor Yellow
    }

    Write-Host '[5/5] Creating run_app.ps1 launcher...' -ForegroundColor Cyan
    $runner = @"
# Runs the packaged app from OneDrive (onedir)
Start-Process -FilePath "`"$(Join-Path $PSScriptRoot 'main\main.exe')`""
"@
    Set-Content -Path (Join-Path $dest 'run_app.ps1') -Value $runner -Encoding UTF8

    Write-Host "[done] Onedir deployment complete. Run: $(Join-Path $dest 'run_app.ps1')" -ForegroundColor Green
}