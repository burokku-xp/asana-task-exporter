# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification - pkg_resources問題を回避
ランタイムフックを無効化してjaraco.textエラーを回避
"""

import os
import sys
import glob
from pathlib import Path

project_root = Path.cwd()
src_path = project_root / 'src'

if hasattr(sys, 'base_prefix'):
    python_dir = Path(sys.base_prefix)
else:
    python_dir = Path(sys.prefix)

print(f"Python directory: {python_dir}")
print(f"Python version: {sys.version}")

# TCL/TK libraries
tcl_dir = python_dir / 'tcl'
tk_lib_dir = python_dir / 'Lib' / 'tkinter'

# DLL files
dll_dir = python_dir / 'DLLs'
dll_files = []
if dll_dir.exists():
    for pattern in ['tcl*.dll', 'tk*.dll', '_tkinter*.pyd']:
        dll_files.extend(glob.glob(str(dll_dir / pattern)))
    for pattern in ['*.dll', '*.pyd']:
        for dll in glob.glob(str(dll_dir / pattern)):
            if dll not in dll_files:
                dll_files.append(dll)

print(f"Found {len(dll_files)} DLL files")

binaries = [(dll, '.') for dll in dll_files]

# certifi証明書の場所を取得
try:
    import certifi
    cert_file = certifi.where()
    cert_datas = [(cert_file, 'certifi')]
    print(f"Added certifi certificates: {cert_file}")
except ImportError:
    cert_datas = []
    print("Warning: certifi not found")

datas = [
    (str(project_root / 'config_template.json'), '.'),
] + cert_datas

if tcl_dir.exists():
    datas.append((str(tcl_dir), 'tcl'))
if tk_lib_dir.exists():
    datas.append((str(tk_lib_dir), 'tkinter'))

a = Analysis(
    [str(src_path / 'main_windows.py')],
    pathex=[str(project_root), str(src_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # Core modules only - no pkg_resources
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        '_tkinter',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'requests',
        'requests.adapters',
        'requests.exceptions',
        'urllib3',
        'certifi',  # SSL証明書
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends.openssl',
        '_cffi_backend',
        'json',
        'datetime',
        'pathlib',
        'logging',
        'logging.handlers',
        'configparser',
        'threading',
        'queue',
        'base64',
        'hashlib',
        'traceback',
        'platform',
        'psutil',
        'tempfile',
        'typing',
        'dataclasses',
        'src.gui.main_window',
        'src.gui.settings_window',
        'src.business.config_manager',
        'src.business.task_manager',
        'src.business.excel_exporter',
        'src.data.asana_client',
        'src.data.models',
        'src.utils.logger',
        'src.utils.error_handler',
        'src.utils.debug_info',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],  # No runtime hooks to avoid pkg_resources
    excludes=[
        'setuptools',
        'pkg_resources',
        'jaraco',
        'pytest',
        'black',
        'PyQt5',
        'PyQt6',
        'numpy',
        'pandas',
        'matplotlib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AsanaTaskExporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,  # コンソールウィンドウを非表示
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version=None,
    uac_admin=False,
    uac_uiaccess=False,
)

print("=" * 80)
print("Build complete (no runtime hooks)")
print("=" * 80)
