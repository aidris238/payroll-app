# -*- mode: python ; coding: utf-8 -*-

import sys
import os

# Auto-detect Python DLL
python_dll = os.path.join(sys.base_exec_prefix, 'python311.dll')
if not os.path.exists(python_dll):
    python_dll = os.path.join(sys.exec_prefix, 'python311.dll')

a = Analysis(
    ['payroll.py'],
    pathex=[],
    binaries=[(python_dll, '.')] if os.path.exists(python_dll) else [],
    datas=[],
    hiddenimports=['rich', 'rich.console', 'rich.table', 'rich.panel', 'rich.prompt', 'rich.progress', 'rich.text', 'rich.align', 'rich.rule', 'rich.layout', 'rich.live', 'rich.box', 'rich.columns'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,  # Use 1 instead of 2 to avoid stripping issues
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='payroll',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Disable strip - can corrupt DLL
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)