<#!
.SYNOPSIS
  Install project git hooks (currently pre-commit warning for outdated header.ico).
.DESCRIPTION
  Copies scripts from tools/git-hooks/* into .git/hooks and sets executable bit (on POSIX).
.EXAMPLE
  ./tools/install_git_hooks.ps1
#>
$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.git')) { throw 'No .git directory found (run from repo root).' }
$src = Join-Path (Get-Location) 'tools/git-hooks'
if (-not (Test-Path $src)) { throw "Source hook directory missing: $src" }
$dest = Join-Path (Get-Location) '.git/hooks'
Get-ChildItem -Path $src -File | ForEach-Object {
  $target = Join-Path $dest $_.Name
  Copy-Item $_.FullName $target -Force
  Write-Host "Installed hook: $($_.Name)" -ForegroundColor Green
  if ($IsLinux -or $IsMacOS) { chmod +x $target }
}
Write-Host 'Git hooks installed.' -ForegroundColor Cyan
