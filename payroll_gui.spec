# -*- mode: python ; coding: utf-8 -*-
import sys, os

# Auto-detect python DLL
python_dll = os.path.join(sys.base_exec_prefix, 'python311.dll')
if not os.path.exists(python_dll):
    python_dll = os.path.join(sys.exec_prefix, 'python311.dll')

a = Analysis(
    ['payroll_gui.py'],
    pathex=[],
    binaries=[(python_dll, '.')] if os.path.exists(python_dll) else [],
    datas=[],
    hiddenimports=['tkinter', 'tkinter.ttk', 'sqlite3', 'csv', 'json', 'datetime'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'PIL', 'cv2', 'scipy'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PayrollPro',
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