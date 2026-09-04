# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('assets', 'assets'),
]
binaries = []
hiddenimports = [
    'winsound',
    'winreg',
    'ctypes',
    'ctypes.wintypes',
    'src.startup',
    'src.logging_config',
]

# bundle binaries and data for offline use
for package_name in ['mediapipe', 'bleak', 'winrt', 'cv2']:
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package_name)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='slouchd',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,	# avoid upx packing so antivirus heuristics dont trigger
    console=False,	# windowed daemon, no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='slouchd',
)
