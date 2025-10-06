# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for Asana Task Exporter (Windows)
要件 7.1: 単一の exe ファイルとして提供される
要件 7.2: 追加のランタイムやライブラリなしで動作する
"""

import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリを取得
project_root = Path.cwd()
src_path = project_root / 'src'

# 分析設定
a = Analysis(
    # メインスクリプト
    [str(src_path / 'main_windows.py')],
    
    # パス設定
    pathex=[str(project_root), str(src_path)],
    
    # バイナリファイル（通常は空）
    binaries=[],
    
    # データファイル（設定テンプレートなど）
    datas=[
        (str(project_root / 'config_template.json'), '.'),
    ],
    
    # 隠れたインポート（PyInstallerが自動検出できないモジュール）
    hiddenimports=[
        # GUI関連
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        
        # Excel処理
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        
        # HTTP通信
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.exceptions',
        'urllib3',
        
        # 暗号化
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        
        # 標準ライブラリ（明示的に指定）
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
        'os',
        'sys',
        'traceback',
        'platform',
        
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
        
        # 不要なGUIライブラリ
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        
        # 不要な科学計算ライブラリ
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        
        # 開発用モジュール
        'IPython',
        'jupyter',
        'notebook',
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
    
    # UPX圧縮（ファイルサイズ削減）
    upx=True,
    upx_exclude=[],
    
    # 実行時設定
    runtime_tmpdir=None,
    
    # コンソール表示設定（デバッグのためTrue）
    console=True,
    disable_windowed_traceback=False,
    
    # その他設定
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
    # アイコンファイル（存在する場合）
    icon=None,  # アイコンファイルがある場合は 'assets/icon.ico' などを指定
    
    # Windows固有設定
    version=None,  # バージョン情報ファイル
    uac_admin=False,  # 管理者権限不要
    uac_uiaccess=False,
)