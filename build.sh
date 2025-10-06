#!/bin/bash
# Asana Task Exporter ビルドスクリプト (Linux/Mac)
# 要件 7.1, 7.2: 単一exe ファイルの生成と依存関係の設定

echo "========================================"
echo "Asana Task Exporter ビルドスクリプト"
echo "========================================"
echo

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Python環境の確認
echo "Python環境を確認しています..."
python3 --version
if [ $? -ne 0 ]; then
    echo "エラー: Python3が見つかりません"
    echo "Python 3.9以上をインストールしてください"
    exit 1
fi

# PyInstallerの確認
echo "PyInstallerを確認しています..."
python3 -c "import PyInstaller; print(f'PyInstaller {PyInstaller.__version__}')"
if [ $? -ne 0 ]; then
    echo "エラー: PyInstallerが見つかりません"
    echo "pip install pyinstaller でインストールしてください"
    exit 1
fi

# 依存関係の確認
echo "依存関係を確認しています..."
python3 -c "import requests, openpyxl, cryptography, tkinter; print('依存関係OK')"
if [ $? -ne 0 ]; then
    echo "エラー: 必要な依存関係が不足しています"
    echo "pip install -r requirements.txt を実行してください"
    exit 1
fi

# 既存のビルドファイルをクリーンアップ
echo "既存のビルドファイルをクリーンアップしています..."
rm -rf build dist *.spec

# build.specをコピー
cp build.spec AsanaTaskExporter.spec

# PyInstallerでビルド実行
echo
echo "========================================"
echo "PyInstallerでビルドを開始します..."
echo "========================================"
echo

python3 -m PyInstaller --clean --noconfirm AsanaTaskExporter.spec

# ビルド結果の確認
if [ $? -ne 0 ]; then
    echo
    echo "========================================"
    echo "ビルドに失敗しました"
    echo "========================================"
    echo "ログを確認してエラーを修正してください"
    exit 1
fi

# 実行ファイルの確認
if [ -f "dist/AsanaTaskExporter" ]; then
    echo
    echo "========================================"
    echo "ビルドが正常に完了しました！"
    echo "========================================"
    
    # ファイルサイズを表示
    size=$(du -m "dist/AsanaTaskExporter" | cut -f1)
    echo "実行ファイル: dist/AsanaTaskExporter"
    echo "ファイルサイズ: ${size} MB"
    
    # 実行権限を付与
    chmod +x "dist/AsanaTaskExporter"
    
    echo
    echo "次のステップ:"
    echo "1. dist/AsanaTaskExporter の動作確認"
    echo "2. 配布パッケージの作成"
    echo "3. 他の環境での動作テスト"
    
else
    echo
    echo "========================================"
    echo "エラー: 実行ファイルが生成されませんでした"
    echo "========================================"
    echo "build.spec の設定を確認してください"
fi

# 一時ファイルのクリーンアップ
rm -f AsanaTaskExporter.spec

echo