# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for Asana Task Exporter (Python 3.13 対応版)
要件 7.1: 単一の exe ファイルとして提供される
要件 7.2: 追加のランタイムやライブラリなしで動作する

Python 3.13 特有の対応:
- tkinter の完全なバンドル
- TCL/TK ライブラリの明示的な追加
- すべてのDLLファイルの包含
"""

import os
import sys
import glob
from pathlib import Path

# プロジェクトのルートディレクトリを取得
project_root = Path.cwd()
src_path = project_root / 'src'

# Python インストールディレクトリ
if hasattr(sys, 'base_prefix'):
    python_dir = Path(sys.base_prefix)
else:
    python_dir = Path(sys.prefix)

print(f"Python directory: {python_dir}")
print(f"Python version: {sys.version}")

# TCL/TK ライブラリのパスを取得
tcl_dir = python_dir / 'tcl'
tk_lib_dir = python_dir / 'Lib' / 'tkinter'

# DLLファイルを収集
dll_dir = python_dir / 'DLLs'
dll_files = []
if dll_dir.exists():
    # tkinter関連のDLLを優先的に追加
    for pattern in ['tcl*.dll', 'tk*.dll', '_tkinter*.pyd']:
        dll_files.extend(glob.glob(str(dll_dir / pattern)))

    # その他の必要なDLL
    for pattern in ['*.dll', '*.pyd']:
        for dll in glob.glob(str(dll_dir / pattern)):
            if dll not in dll_files:
                dll_files.append(dll)

print(f"Found {len(dll_files)} DLL files")

# バイナリファイルとしてDLLを追加
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

# データファイルの収集
datas = [
    (str(project_root / 'config_template.json'), '.'),
] + cert_datas

# TCL/TKディレクトリが存在する場合は追加
if tcl_dir.exists():
    datas.append((str(tcl_dir), 'tcl'))
    print(f"Added TCL directory: {tcl_dir}")

if tk_lib_dir.exists():
    datas.append((str(tk_lib_dir), 'tkinter'))
    print(f"Added TK library directory: {tk_lib_dir}")

# 分析設定
a = Analysis(
    # メインスクリプト
    [str(src_path / 'main_windows.py')],

    # パス設定
    pathex=[str(project_root), str(src_path)],

    # バイナリファイル
    binaries=binaries,

    # データファイル
    datas=datas,

    # 隠れたインポート（Python 3.13 対応強化版）
    hiddenimports=[
        # pkg_resources 関連（PyInstallerのランタイムフックで必要）
        'pkg_resources',
        'pkg_resources.py2_warn',
        'pkg_resources._vendor',
        'pkg_resources.extern',
        'jaraco.text',
        'jaraco.functools',
        'jaraco.context',
        'more_itertools',

        # tkinter関連 - Python 3.13では明示的に必要
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.simpledialog',
        'tkinter.colorchooser',
        'tkinter.commondialog',
        'tkinter.constants',
        'tkinter.dialog',
        'tkinter.dnd',
        'tkinter.font',
        '_tkinter',  # C拡張モジュール

        # Excel処理
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.styles.alignment',
        'openpyxl.styles.borders',
        'openpyxl.styles.colors',
        'openpyxl.styles.fills',
        'openpyxl.styles.fonts',
        'openpyxl.styles.numbers',
        'openpyxl.styles.protection',
        'openpyxl.utils',
        'openpyxl.utils.cell',
        'openpyxl.utils.datetime',
        'openpyxl.workbook',
        'openpyxl.workbook.workbook',
        'openpyxl.worksheet',
        'openpyxl.worksheet.worksheet',
        'openpyxl.cell',
        'openpyxl.cell.cell',
        'openpyxl.chart',
        'openpyxl.drawing',
        'openpyxl.xml',
        'openpyxl.xml.functions',

        # HTTP通信
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'requests.structures',
        'requests.utils',
        'certifi',  # SSL証明書
        'urllib3',
        'urllib3.connection',
        'urllib3.connectionpool',
        'urllib3.contrib',
        'urllib3.exceptions',
        'urllib3.fields',
        'urllib3.filepost',
        'urllib3.poolmanager',
        'urllib3.request',
        'urllib3.response',
        'urllib3.util',
        'urllib3.util.connection',
        'urllib3.util.request',
        'urllib3.util.response',
        'urllib3.util.retry',
        'urllib3.util.ssl_',
        'urllib3.util.timeout',
        'urllib3.util.url',

        # 暗号化
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.backends.openssl.backend',
        '_cffi_backend',

        # 標準ライブラリ（Python 3.13で明示的に必要）
        'json',
        'datetime',
        'pathlib',
        'logging',
        'logging.handlers',
        'logging.config',
        'configparser',
        'threading',
        'queue',
        'base64',
        'hashlib',
        'os',
        'sys',
        'traceback',
        'platform',
        'psutil',
        'tempfile',
        'shutil',
        'io',
        'typing',
        'dataclasses',
        'enum',
        'collections',
        'collections.abc',
        'functools',
        'itertools',
        're',
        'copy',
        'weakref',

        # プロジェクト内モジュール
        'src',
        'src.gui',
        'src.gui.main_window',
        'src.gui.settings_window',
        'src.business',
        'src.business.config_manager',
        'src.business.task_manager',
        'src.business.excel_exporter',
        'src.business.config_initializer',
        'src.business.config_schema',
        'src.business.config_example',
        'src.data',
        'src.data.asana_client',
        'src.data.models',
        'src.utils',
        'src.utils.logger',
        'src.utils.error_handler',
        'src.utils.debug_info',
    ],

    # フック設定
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    # 除外するモジュール
    excludes=[
        # 開発用ツール
        'pytest',
        'pytest_mock',
        'black',
        'flake8',
        'mypy',
        'pylint',
        'setuptools',  # pkg_resources問題を回避

        # 不要なGUIライブラリ
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'gtk',

        # 不要な科学計算ライブラリ
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'sklearn',

        # 開発用モジュール
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'setuptools',
    ],

    # Windows設定
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ（Python Zip）アーカイブ
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 実行ファイル設定
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],

    # 実行ファイル名
    name='AsanaTaskExporter',

    # デバッグ設定
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,

    # UPX圧縮（Python 3.13では問題が起きる可能性があるため無効化）
    upx=False,
    upx_exclude=[],

    # 実行時設定
    runtime_tmpdir=None,

    # コンソール表示設定（最初はTrue、動作確認後にFalseに変更）
    console=True,
    disable_windowed_traceback=False,

    # その他設定
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # アイコンファイル（存在する場合）
    icon=None,

    # Windows固有設定
    version=None,
    uac_admin=False,
    uac_uiaccess=False,
)

# ビルド後の処理
def post_build():
    """ビルド後の処理"""
    print("=" * 80)
    print("PyInstaller ビルドが完了しました (Python 3.13)")
    print("=" * 80)

    exe_path = project_root / 'dist' / 'AsanaTaskExporter.exe'
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
        print(f"実行ファイル: {exe_path}")
        print(f"ファイルサイズ: {file_size:.1f} MB")
        print()
        print("次のステップ:")
        print("1. dist\\AsanaTaskExporter.exe を実行してテスト")
        print("2. コンソールウィンドウでエラーがないか確認")
        print("3. GUIが正常に表示されることを確認")
        print("4. 動作確認後、console=False に変更して再ビルド")
    else:
        print("エラー: 実行ファイルが生成されませんでした")

    print("=" * 80)

# ビルド完了時に実行
import atexit
atexit.register(post_build)
