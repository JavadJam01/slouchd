# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

datas = [
    ('assets', 'assets'),
]
binaries = []
hiddenimports = [
    'src.startup',
    'src.logging_config',
    'src.ui.window_utils',
]

if sys.platform == "win32":
    hiddenimports += [
        'winsound',
        'winreg',
        'ctypes',
        'ctypes.wintypes',
    ]

# bundle binaries and data for offline use
packages_to_collect = ['mediapipe', 'bleak', 'cv2']
if sys.platform == "win32":
    packages_to_collect.append('winrt')

for package_name in packages_to_collect:
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package_name)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

if sys.platform.startswith("linux"):
    # Avoid bundling opencv's outdated xkb/xcb libraries that conflict with system Qt and Wayland/X11
    system_conflicts = ('libxkbcommon', 'libxcb-xkb')
    binaries = [b for b in binaries if not any(c in b[0] for c in system_conflicts)]

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

if sys.platform.startswith("linux"):
    system_conflicts = ('libxkbcommon', 'libxcb-xkb')
    a.binaries = [b for b in a.binaries if not any(c in b[0] for c in system_conflicts)]

pyz = PYZ(a.pure)

exe_kwargs = {
    'name': 'slouchd',
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': False,	# avoid upx packing so antivirus heuristics dont trigger
    'console': False,	# windowed daemon, no terminal window
    'disable_windowed_traceback': False,
    'argv_emulation': False,
    'target_arch': None,
    'codesign_identity': None,
    'entitlements_file': None,
}

if sys.platform == "win32":
    exe_kwargs['icon'] = 'assets/icon.ico'
    exe_kwargs['version'] = 'version_info.txt'

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    **exe_kwargs,
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
