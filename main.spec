# -*- mode: python ; coding: utf-8 -*-


import os

# Build datas list dynamically so missing optional folders don't break build
datas_list = [('project_data.db', '.'), ('images/*', 'images')]
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
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression (ensure UPX is installed & on PATH)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
