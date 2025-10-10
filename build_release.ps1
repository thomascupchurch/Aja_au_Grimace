<#!
.SYNOPSIS
  Build and package a timestamped release archive for the Project Planner.
.DESCRIPTION
  Performs a clean PyInstaller build using main.spec, copies optional extras (cli.py, project_data.db, README.md),
  optionally generates a manifest.json with SHA256 hashes of all packaged files, and creates a zip archive named:
    release_yyyyMMdd_HHmmss[_channel][_gitHash].zip
.PARAMETER IncludeCLI
  Include cli.py utility in the packaged dist prior to zipping.
.PARAMETER IncludeDBTemplate
  Include project_data.db (current state) in the archive (use cautiously if DB contains real data).
.PARAMETER IncludeManifest
  Generate a manifest.json (file list + SHA256 hashes) inside the dist/main folder before zipping.
.PARAMETER Channel
  Optional channel tag (e.g. dev, beta, stable) appended to archive filename.
.PARAMETER Python
  Override path to Python executable (defaults to .venv/Scripts/python.exe).
.EXAMPLE
  ./build_release.ps1
.EXAMPLE
  ./build_release.ps1 -IncludeCLI -Channel dev -IncludeManifest
.EXAMPLE
  ./build_release.ps1 -IncludeCLI -IncludeDBTemplate -Channel stable
.NOTES
  Requires PowerShell 5+ and PyInstaller installed in the selected Python environment.
#>
param(
  [switch]$IncludeCLI,
  [switch]$IncludeDBTemplate,
  [switch]$IncludeManifest,
  [string]$Channel = "",
  [string]$Python = ".venv/Scripts/python.exe",
  [switch]$ForceKill,
  [switch]$SkipClean,
  [switch]$OneFile,
  [string]$Version = "",
  [int]$Keep = 0,
  [string]$IconSizes = "16,24,32,48,64,128,256",
  [switch]$ForceIcon,
  [switch]$MacBundle
  , [switch]$DryRun
)
$ErrorActionPreference = 'Stop'

function Resolve-PythonPath {
  param([string]$PathCandidate)
  if (Test-Path $PathCandidate) { return (Resolve-Path $PathCandidate).Path }
  $alt = @('.venv/Scripts/python.exe','venv/Scripts/python.exe','python.exe','py.exe')
  foreach ($p in $alt) { if (Test-Path $p) { return (Resolve-Path $p).Path } }
  throw "Python executable not found. Specify -Python explicitly."
}

function Get-GitShortHash {
  try { (git rev-parse --short HEAD) 2>$null } catch { return $null }
}

function Write-Section($title) {
  Write-Host "`n=== $title ===" -ForegroundColor Cyan
}

$pythonExe = Resolve-PythonPath ($Python -replace ' ','')
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$hash = Get-GitShortHash
$channelTag = if ($Channel) { "_" + $Channel } else { '' }
$hashTag = if ($hash) { "_" + $hash } else { '' }
$versionTag = if ($Version) { "_v" + ($Version -replace '[^0-9A-Za-z._-]','') } else { '' }
$archiveName = "release_${stamp}${versionTag}${channelTag}${hashTag}.zip"

if (-not $SkipClean) {
  Write-Section "Clean previous build artifacts"
  if ($DryRun) {
    Write-Host "[dryrun] Would remove build/, dist/" -ForegroundColor DarkGray
  } else {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
  }
} else {
  Write-Section "Skip clean (user requested)"
}

# After determining $pythonExe and before invoking PyInstaller:
Write-Host "=== Ensure PyInstaller present ==="
if ($DryRun) {
  Write-Host "[dryrun] Would check for PyInstaller (import PyInstaller) and install if missing" -ForegroundColor DarkGray
} else {
  & $pythonExe -c "import PyInstaller" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[build] Installing PyInstaller..." -ForegroundColor Cyan
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install PyInstaller
  }
}

Write-Section "Run PyInstaller build"

$specFile = if ($OneFile) { 'main_onefile.spec' } else { 'main.spec' }
if (-not (Test-Path $specFile)) { throw "Spec file '$specFile' not found." }
Write-Host "Using spec: $specFile" -ForegroundColor DarkYellow

# --- Pillow Self-Test (pre Icon Generation) ----------------------------------
if (-not $DryRun) {
  Write-Host "Performing Pillow self-test..." -ForegroundColor DarkCyan
  $selfTestCode = @'
import sys
try:
    from PIL import Image, ImageFilter  # noqa: F401
    im = Image.new('RGBA', (2,2), (255,0,0,255))
    im.filter(ImageFilter.BLUR)
except Exception as e:
    print('[pillow-selftest] FAIL:', repr(e))
    sys.exit(3)
else:
    print('[pillow-selftest] OK')
'@
  $tmpSelfTest = [System.IO.Path]::GetTempFileName() + '.py'
  Set-Content -Path $tmpSelfTest -Value $selfTestCode -Encoding UTF8
  & $pythonExe $tmpSelfTest
  $selfTestExit = $LASTEXITCODE
  Remove-Item $tmpSelfTest -Force -ErrorAction SilentlyContinue
  if ($selfTestExit -eq 3) {
    Write-Host "[pillow-selftest] Attempting repair (force reinstall Pillow)..." -ForegroundColor Yellow
    & $pythonExe -m pip install --no-cache-dir --force-reinstall Pillow
    if ($LASTEXITCODE -eq 0) {
      $retestCode = @'
import sys
try:
    from PIL import Image
    Image.new('RGB',(1,1))
except Exception as e:
    print('[pillow-selftest] Still failing:', repr(e))
    sys.exit(3)
else:
    print('[pillow-selftest] OK after repair')
'@
      $tmpRetest = [System.IO.Path]::GetTempFileName() + '.py'
      Set-Content -Path $tmpRetest -Value $retestCode -Encoding UTF8
      & $pythonExe $tmpRetest
      Remove-Item $tmpRetest -Force -ErrorAction SilentlyContinue
    } else {
      Write-Host "[pillow-selftest] Repair failed; continuing (icon generation may fall back)." -ForegroundColor Yellow
    }
  }
} else {
  Write-Host "[dryrun] Would perform Pillow self-test" -ForegroundColor DarkGray
}

# --- Auto Icon Generation -----------------------------------------------------
try {
  $iconScript = Join-Path (Get-Location) 'tools/make_icons.py'
  if (Test-Path $iconScript) {
    $argsList = @()
    if ($ForceIcon) { $argsList += '--force' }
    if ($IconSizes) { $argsList += @('--sizes', $IconSizes) }
    # Auto-generate macOS ICNS if platform is Darwin (when script executed under PowerShell Core on macOS)
    try {
      $isMac = $false
      if ($PSVersionTable.Platform -eq 'Unix') {
        # Check uname for Darwin (avoid relying solely on $IsMacOS which older Windows PowerShell lacks)
        $uname = (uname 2>$null)
        if ($uname -match 'Darwin') { $isMac = $true }
      }
      if ($isMac) { $argsList += '--icns' }
    } catch { }
    Write-Host "Icon generation: python tools/make_icons.py $($argsList -join ' ')" -ForegroundColor DarkCyan
    if ($DryRun) {
      Write-Host "[dryrun] Would invoke icon generation script" -ForegroundColor DarkGray
    } else {
      & $pythonExe $iconScript @argsList
      if ($LASTEXITCODE -ne 0) {
          Write-Host "[warn] Icon generation returned $LASTEXITCODE (continuing build)." -ForegroundColor Yellow
          if ($LASTEXITCODE -eq 2) {
            Write-Host "[info] Attempting automatic Pillow install..." -ForegroundColor DarkYellow
            & $pythonExe -m pip install Pillow
            if ($LASTEXITCODE -eq 0) {
              Write-Host "[info] Retrying icon generation after Pillow install" -ForegroundColor DarkYellow
              & $pythonExe $iconScript @argsList
              if ($LASTEXITCODE -ne 0) {
                Write-Host "[warn] Retry icon generation still failed ($LASTEXITCODE)." -ForegroundColor Yellow
              }
            } else {
              Write-Host "[warn] Pillow auto-install failed; continuing without branded icon." -ForegroundColor Yellow
            }
          }
        } elseif (-not (Test-Path 'header.ico')) {
          Write-Host "[warn] header.ico still missing after icon generation (build will proceed without branded exe icon)." -ForegroundColor Yellow
        } else {
        Write-Host "Icon generation complete." -ForegroundColor Green
        if (Test-Path 'header.icns') { Write-Host "Detected header.icns (macOS app icon available)." -ForegroundColor Green }
      }
    }
  } else {
    Write-Host "[info] tools/make_icons.py not found; skipping icon pre-build." -ForegroundColor DarkGray
  }
} catch {
  Write-Host "[warn] Exception during icon generation: $($_.Exception.Message)" -ForegroundColor Yellow
}

# If ForceKill specified, attempt to terminate any running instance of prior exe (common cause of WinError 5)
if ($ForceKill) {
  $possibleExe = Join-Path (Get-Location) 'dist/Vols Signage.exe'
  $possibleExeOld = Join-Path (Get-Location) 'dist/main.exe'
  $possibleOneDirExe = Join-Path (Get-Location) 'dist/Vols Signage/Vols Signage.exe'
  $possibleOneDirExeOld = Join-Path (Get-Location) 'dist/main/main.exe'
  $targets = @($possibleExe,$possibleExeOld,$possibleOneDirExe,$possibleOneDirExeOld) | Where-Object { Test-Path $_ }
  if ($targets.Count -gt 0) {
    Write-Host "Attempting to terminate running processes locking previous build..." -ForegroundColor Yellow
    foreach ($t in $targets) {
      Get-Process | Where-Object { $_.Path -eq $t } | ForEach-Object { Write-Host "Killing PID $($_.Id) for $t"; $_ | Stop-Process -Force }
    }
    Start-Sleep -Milliseconds 300
  }
}

if ($DryRun) {
  Write-Host "[dryrun] Would run PyInstaller with spec $specFile" -ForegroundColor DarkGray
} else {
  Write-Host "Invoking PyInstaller..." -ForegroundColor DarkCyan
  $buildLogFile = Join-Path $env:TEMP "build_release_pyinstaller_$(Get-Random).log"
  $previousErrorPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    & $pythonExe -m PyInstaller --clean --noconfirm $specFile 2>&1 | Tee-Object -FilePath $buildLogFile
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
      Write-Host "Initial PyInstaller run failed (exit $exitCode). Retrying without --clean..." -ForegroundColor Yellow
      & $pythonExe -m PyInstaller --noconfirm $specFile 2>&1 | Tee-Object -FilePath $buildLogFile
      $exitCode = $LASTEXITCODE
    }
    if ($exitCode -ne 0) {
      Write-Host "PyInstaller failed. Last 40 log lines:" -ForegroundColor Red
      if (Test-Path $buildLogFile) { Get-Content $buildLogFile -Tail 40 | ForEach-Object { Write-Host $_ -ForegroundColor Red } }
      throw "PyInstaller build failed (exit $exitCode)"
    }
  } finally {
    $ErrorActionPreference = $previousErrorPreference
  }
  Write-Host "PyInstaller build succeeded." -ForegroundColor Green
}

$distRoot = Join-Path (Get-Location) 'dist'

# PyInstaller spec currently builds one-file (main.exe in dist) or one-dir (dist/main/). Detect.
$oneFileExeNew = Join-Path $distRoot 'Vols Signage.exe'
$oneFileExeOld = Join-Path $distRoot 'main.exe'
$oneDirFolderNew = Join-Path $distRoot 'Vols Signage'
$oneDirFolderOld = Join-Path $distRoot 'main'

$staging = Join-Path (Get-Location) "_stage_main"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

if ($DryRun) {
  Write-Host "[dryrun] Would detect build layout (expect dist/main or dist/main.exe)" -ForegroundColor DarkGray
}
if (-not $DryRun -and (Test-Path $oneDirFolderNew)) {
  Write-Host "Detected onedir build layout (dist/Vols Signage/)." -ForegroundColor Green
  Copy-Item (Join-Path $oneDirFolderNew '*') $staging -Recurse -Force
} elseif (-not $DryRun -and (Test-Path $oneDirFolderOld)) {
  Write-Host "Detected legacy onedir build layout (dist/main/)." -ForegroundColor Yellow
  Copy-Item (Join-Path $oneDirFolderOld '*') $staging -Recurse -Force
} elseif (-not $DryRun -and (Test-Path $oneFileExeNew)) {
  Write-Host "Detected one-file build layout (dist/Vols Signage.exe)." -ForegroundColor Green
  Copy-Item $oneFileExeNew (Join-Path $staging 'Vols Signage.exe')
} elseif (-not $DryRun -and (Test-Path $oneFileExeOld)) {
  Write-Host "Detected legacy one-file build layout (dist/main.exe)." -ForegroundColor Yellow
  Copy-Item $oneFileExeOld (Join-Path $staging 'main.exe')
} elseif (-not $DryRun) {
  throw "Neither dist/main folder nor dist/main.exe found. Build layout unexpected."
}

# Standardize Windows app filename for distribution to "Vols Signage.exe"
if (-not $DryRun) {
  $stagedMainExe = Join-Path $staging 'main.exe'
  $desiredName = 'Vols Signage.exe'
  $stagedDesiredExe = Join-Path $staging $desiredName
  if (Test-Path $stagedMainExe) {
    try {
      if (Test-Path $stagedDesiredExe) { Remove-Item $stagedDesiredExe -Force }
      Rename-Item -Path $stagedMainExe -NewName $desiredName -Force
      Write-Host "Renamed staged executable to: $desiredName" -ForegroundColor Green
    } catch {
      Write-Host "[warn] Failed to rename main.exe to '$desiredName': $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }
}

if ($Version) {
  if ($DryRun) { Write-Host "[dryrun] Would write VERSION file ($Version)" -ForegroundColor DarkGray }
  else { Set-Content -Path (Join-Path $staging 'VERSION') -Value $Version -Encoding UTF8 }
}

if ($IncludeCLI) {
  if ($DryRun) { Write-Host "[dryrun] Would copy cli.py (if exists)" -ForegroundColor DarkGray }
  elseif (Test-Path 'cli.py') { Copy-Item 'cli.py' $staging } else { Write-Warning 'cli.py not found; skipping.' }
}
if ($IncludeDBTemplate) {
  if ($DryRun) { Write-Host "[dryrun] Would copy project_data.db" -ForegroundColor DarkGray }
  elseif (Test-Path 'project_data.db') { Copy-Item 'project_data.db' $staging } else { Write-Warning 'project_data.db not found; skipping DB template.' }
}
if ($DryRun) { Write-Host "[dryrun] Would copy README.md" -ForegroundColor DarkGray } elseif (Test-Path 'README.md') { Copy-Item 'README.md' $staging }

if ($IncludeManifest) {
  Write-Section "Generate manifest.json"
  if ($DryRun) {
    Write-Host "[dryrun] Would compute file hashes and write manifest.json" -ForegroundColor DarkGray
  } else {
    $manifest = @()
    Get-ChildItem -Path $staging -Recurse -File | ForEach-Object {
      $rel = $_.FullName.Substring($staging.Length+1)
      $hashObj = Get-FileHash -Algorithm SHA256 -Path $_.FullName
      $manifest += [PSCustomObject]@{
        path = $rel
        bytes = $_.Length
        sha256 = $hashObj.Hash.ToLower()
      }
    }
    $json = $manifest | ConvertTo-Json -Depth 4
    $json | Out-File -FilePath (Join-Path $staging 'manifest.json') -Encoding UTF8
  }
}

# --- Optional macOS .app bundle repackage ------------------------------------
if ($MacBundle) {
  Write-Section "macOS Bundle"
  $isMac = $false
  try {
    if ($PSVersionTable.Platform -eq 'Unix') {
      $uname = (uname 2>$null)
      if ($uname -match 'Darwin') { $isMac = $true }
    }
  } catch {}
  if (-not $isMac) {
    Write-Host "[warn] -MacBundle specified but host is not macOS (skipping)." -ForegroundColor Yellow
  } else {
    $appName = 'Vols Signage'
    # Sanitize bundle identifier component from app name (replace spaces with hyphen, strip invalid chars)
    $bundleIdName = (($appName -replace '\s+','-') -replace '[^A-Za-z0-9.-]','').ToLower()
    $bundleRoot = Join-Path (Get-Location) "$appName.app"
    if ($DryRun) {
      Write-Host "[dryrun] Would create bundle directories $bundleRoot/Contents/..." -ForegroundColor DarkGray
    } else {
      if (Test-Path $bundleRoot) { Remove-Item -Recurse -Force $bundleRoot }
      $contents = Join-Path $bundleRoot 'Contents'
      $macosDir = Join-Path $contents 'MacOS'
      $resources = Join-Path $contents 'Resources'
      New-Item -ItemType Directory -Path $macosDir,$resources | Out-Null
    }
    # Choose executable: if one-file build, main.exe in staging; else pick 'main' or first .exe
    $exeCandidate = Get-ChildItem -Path $staging -File | Where-Object { $_.Name -match 'main(.exe)?' } | Select-Object -First 1
    if (-not $exeCandidate) { $exeCandidate = Get-ChildItem -Path $staging -File | Select-Object -First 1 }
  if (-not $exeCandidate) { if (-not $DryRun) { throw 'No executable found in staging to place inside .app bundle.' } }
  if ($DryRun) { Write-Host "[dryrun] Would copy executable $($exeCandidate.Name) -> Contents/MacOS/$appName" -ForegroundColor DarkGray }
  elseif ($exeCandidate) { Copy-Item $exeCandidate.FullName (Join-Path $macosDir $appName) -Force }
    # Copy resources (everything else) simplistic approach
    if ($DryRun) { Write-Host "[dryrun] Would copy remaining staging files into Resources/" -ForegroundColor DarkGray }
    else {
      Get-ChildItem -Path $staging | Where-Object { $_.FullName -ne $exeCandidate.FullName } | ForEach-Object {
        if ($_.PSIsContainer) { Copy-Item $_.FullName (Join-Path $resources $_.Name) -Recurse -Force }
        else { Copy-Item $_.FullName (Join-Path $resources $_.Name) -Force }
      }
    }
    $plist = @(
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
      '<plist version="1.0">',
      '<dict>',
      '  <key>CFBundleName</key><string>' + $appName + '</string>',
      '  <key>CFBundleExecutable</key><string>' + $appName + '</string>',
      '  <key>CFBundleIdentifier</key><string>com.lsi.' + $bundleIdName + '</string>',
      '  <key>CFBundleVersion</key><string>' + ($Version -replace '"','') + '</string>',
      '  <key>CFBundleShortVersionString</key><string>' + ($Version -replace '"','') + '</string>',
      '  <key>LSMinimumSystemVersion</key><string>10.13</string>',
      '  <key>CFBundlePackageType</key><string>APPL</string>',
      '  <key>NSHighResolutionCapable</key><true/>',
      '  <key>NSPrincipalClass</key><string>NSApplication</string>',
      '</dict>',
      '</plist>'
    ) -join "`n"
    $plistPath = Join-Path $contents 'Info.plist'
  if ($DryRun) { Write-Host "[dryrun] Would write Info.plist" -ForegroundColor DarkGray } else { Set-Content -Path $plistPath -Value $plist -Encoding UTF8 }
    # Add icon if present
    if ($DryRun) { Write-Host "[dryrun] Would copy header.icns to Resources/AppIcon.icns (if exists)" -ForegroundColor DarkGray }
    elseif (Test-Path 'header.icns') { Copy-Item 'header.icns' (Join-Path $resources 'AppIcon.icns') }
    if (-not $DryRun) { Write-Host "Created macOS bundle: $bundleRoot" -ForegroundColor Green } else { Write-Host "[dryrun] Simulated macOS bundle creation" -ForegroundColor DarkGray }
  }
}

Write-Section "Create archive $archiveName"
if ($DryRun) {
  Write-Host "[dryrun] Would remove existing $archiveName (if present)" -ForegroundColor DarkGray
  Write-Host "[dryrun] Would zip staging contents into $archiveName" -ForegroundColor DarkGray
} else {
  if (Test-Path $archiveName) { Remove-Item $archiveName -Force }
  Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $archiveName -Force
}

if ($DryRun) {
  Write-Host "[dryrun] Would report archive size after creation" -ForegroundColor DarkGray
} else {
  $sizeKB = [math]::Round(((Get-Item $archiveName).Length / 1KB),2)
  Write-Host "Archive created: $archiveName (${sizeKB} KB)" -ForegroundColor Green
}

# Generate checksum file
Write-Section "Checksum"
if ($DryRun) {
  Write-Host "[dryrun] Would compute SHA256 and write $archiveName.sha256" -ForegroundColor DarkGray
} else {
  $sha = (Get-FileHash -Algorithm SHA256 -Path $archiveName).Hash.ToLower()
  $checksumLine = "$sha *$archiveName"
  Set-Content -Path "$archiveName.sha256" -Value $checksumLine -Encoding ASCII
  Write-Host "SHA256: $sha" -ForegroundColor Green
}

if ($Keep -gt 0) {
  Write-Section "Prune old releases (keep $Keep)"
  $releases = Get-ChildItem -File -Filter 'release_*.zip' | Sort-Object LastWriteTime -Descending
  $toRemove = $releases | Select-Object -Skip $Keep
  foreach ($r in $toRemove) {
    $hashFile = "$($r.Name).sha256"
    Write-Host "Deleting old release: $($r.Name)" -ForegroundColor DarkYellow
    Remove-Item $r.FullName -Force
    if (Test-Path $hashFile) { Remove-Item $hashFile -Force }
  }
}

Write-Section "Contents (staging top-level)"
if ($DryRun) {
  Write-Host "[dryrun] Would list staging directory contents" -ForegroundColor DarkGray
} else {
  Get-ChildItem $staging | Select-Object Name, Length | Format-Table -AutoSize
}

Write-Section "Done"
if ($DryRun) {
  Write-Host "[dryrun] Simulation complete. No files modified." -ForegroundColor Yellow
  Write-Host "[dryrun] Planned archive: $archiveName" -ForegroundColor DarkGray
  return
} else {
  Write-Host "Use: Expand-Archive $archiveName -DestinationPath test_release" -ForegroundColor Yellow
  Write-Host "(Temporary staging folder '$staging' retained; safe to delete.)" -ForegroundColor DarkGray
}
