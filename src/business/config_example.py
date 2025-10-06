"""
設定管理システムの使用例

ConfigManager と ConfigInitializer の基本的な使用方法を示します。
"""

import logging
from pathlib import Path

from .config_manager import ConfigManager
from .config_initializer import ConfigInitializer
from .config_schema import AppConfig

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """基本的な使用例"""
    print("=== 基本的な設定管理の例 ===")
    
    # ConfigManager を作成
    config_manager = ConfigManager()
    
    # デフォルト設定を取得
    default_config = config_manager.get_default_config()
    print(f"デフォルト設定: {default_config}")
    
    # 設定を保存
    config_manager.save_config(default_config)
    print("設定を保存しました")
    
    # 設定を読み込み
    loaded_config = config_manager.load_config()
    print(f"読み込んだ設定: {loaded_config}")


def example_encryption():
    """暗号化機能の例"""
    print("\n=== 暗号化機能の例 ===")
    
    config_manager = ConfigManager()
    
    # 機密データの暗号化
    sensitive_data = "my-secret-api-token"
    encrypted = config_manager.encrypt_sensitive_data(sensitive_data)
    print(f"暗号化前: {sensitive_data}")
    print(f"暗号化後: {encrypted}")
    
    # 復号化
    decrypted = config_manager.decrypt_sensitive_data(encrypted)
    print(f"復号化後: {decrypted}")
    
    assert sensitive_data == decrypted
    print("暗号化・復号化が正常に動作しました")


def example_initialization():
    """初期化機能の例"""
    print("\n=== 初期化機能の例 ===")
    
    # 一時的な設定ディレクトリを使用
    temp_config_dir = Path.cwd() / "temp_config"
    config_manager = ConfigManager(str(temp_config_dir))
    initializer = ConfigInitializer(config_manager)
    
    # 初回起動チェック
    is_first = initializer.is_first_run()
    print(f"初回起動: {is_first}")
    
    # アプリケーション設定のセットアップ
    config = initializer.setup_application(
        access_token="sample-token",
        output_directory=str(Path.home() / "Documents"),
        selected_fields=["name", "created_at", "assignee"]
    )
    
    print(f"セットアップされた設定: {config.to_dict()}")
    
    # 設定情報の取得
    config_info = initializer.get_config_info()
    print(f"設定情報: {config_info}")
    
    # クリーンアップ
    try:
        import shutil
        shutil.rmtree(temp_config_dir)
        print("一時ディレクトリを削除しました")
    except Exception as e:
        print(f"クリーンアップエラー: {e}")


def example_schema_usage():
    """設定スキーマの使用例"""
    print("\n=== 設定スキーマの例 ===")
    
    # AppConfig オブジェクトの作成
    config = AppConfig()
    print(f"デフォルト設定オブジェクト: {config}")
    
    # 設定の変更
    config.asana.access_token = "new-token"
    config.asana.selected_project_name = "テストプロジェクト"
    config.export.default_date_range = 60
    
    # 辞書形式に変換
    config_dict = config.to_dict()
    print(f"辞書形式: {config_dict}")
    
    # 辞書から設定オブジェクトを復元
    restored_config = AppConfig.from_dict(config_dict)
    print(f"復元された設定: {restored_config}")
    
    # フィールド関連の機能
    from .config_schema import (
        AVAILABLE_TASK_FIELDS, 
        get_field_display_name, 
        is_required_field,
        validate_selected_fields
    )
    
    print(f"利用可能フィールド: {list(AVAILABLE_TASK_FIELDS.keys())}")
    print(f"'name'の表示名: {get_field_display_name('name')}")
    print(f"'name'は必須: {is_required_field('name')}")
    
    # フィールド選択の検証
    test_fields = ["assignee", "due_date", "custom_fields"]
    validated = validate_selected_fields(test_fields)
    print(f"検証前: {test_fields}")
    print(f"検証後: {validated}")


if __name__ == "__main__":
    try:
        example_basic_usage()
        example_encryption()
        example_initialization()
        example_schema_usage()
        print("\n全ての例が正常に実行されました！")
        
    except Exception as e:
        logger.error(f"例の実行中にエラーが発生しました: {e}")
        raise