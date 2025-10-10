# -*- mode: python ; coding: utf-8 -*-


import os
# NOTE (Icon Packaging):
# - Windows build: uses header.ico if present (auto-generated at runtime OR via tools/make_icons.py)
# - macOS build: generate header.icns (see README or run: python tools/make_icons.py --icns) then set icon='header.icns'.
# Manual macOS one-liner (requires rsvg-convert & iconutil):
#   mkdir AppIcon.iconset; for s in 16 32 64 128 256 512; do s2=$((s*2)); \
#     rsvg-convert -w $s -h $s header.svg > AppIcon.iconset/icon_${s}x${s}.png; \
#     rsvg-convert -w $s2 -h $s2 header.svg > AppIcon.iconset/icon_${s}x${s}@2x.png; done; \
#   iconutil -c icns AppIcon.iconset && mv AppIcon.icns header.icns
# Deterministic pre-build generation (Windows/Mac):
#   python tools/make_icons.py --force

# Build datas list dynamically so missing optional folders don't break build
datas_list = [('project_data.db', '.'), ('images/*', 'images'), ('header.svg', '.'), ('header.png', '.')]
if os.path.exists('header.ico'):
    datas_list.append(('header.ico', '.'))
if os.path.isdir('attachments'):
    datas_list.append(('attachments/*', 'attachments'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # Include database, images, and optionally attachments directory contents
    datas=datas_list,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # No binding exclusions required (pure PyQt6). If a stale hook reappears, temporarily re-add 'PyQt5'.
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Onedir build: produce a folder (dist/main/) instead of single exe.
# Auto-detect macOS to prefer header.icns if present
import platform
_icon_choice = None
if os.path.exists('header.icns') and platform.system() == 'Darwin':
    _icon_choice = 'header.icns'
elif os.path.exists('header.ico'):
    _icon_choice = 'header.ico'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Vols Signage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_choice,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Vols Signage'
)
