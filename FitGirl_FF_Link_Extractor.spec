# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Collect all selenium submodules and driver tools
tmp_ret = collect_all('selenium')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Dynamically bundle abi3t-compat DLLs if present (required for cryptography / _rust on Python 3.15+)
python_dir = os.path.dirname(sys.executable)
abi3t_dll = os.path.join(python_dir, 'abi3t-compat', 'python3t.dll')
if os.path.exists(abi3t_dll):
    binaries.append((abi3t_dll, '.'))

python3_dll = os.path.join(python_dir, 'python3.dll')
if os.path.exists(python3_dll):
    binaries.append((python3_dll, '.'))


a = Analysis(
    ['ff_grabber.py'],
    pathex=[],
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
    a.binaries,
    a.datas,
    [],
    name='FitGirl_FF_Link_Extractor',
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
)
