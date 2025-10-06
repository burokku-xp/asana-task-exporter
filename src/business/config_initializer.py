"""
設定初期化ユーティリティ

アプリケーションの初回起動時の設定初期化処理を提供します。
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .config_manager import ConfigManager
from .config_schema import AppConfig, DEFAULT_SELECTED_FIELDS

logger = logging.getLogger(__name__)


class ConfigInitializer:
    """設定初期化クラス
    
    アプリケーションの初回起動時に必要な設定の初期化を行います。
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """ConfigInitializer を初期化
        
        Args:
            config_manager: 使用する ConfigManager インスタンス。
                          None の場合は新しいインスタンスを作成
        """
        self.config_manager = config_manager or ConfigManager()
        logger.info("ConfigInitializer initialized")
    
    def is_first_run(self) -> bool:
        """初回起動かどうかを判定
        
        Returns:
            初回起動の場合 True
        """
        return not self.config_manager.config_exists()
    
    def initialize_default_config(self) -> AppConfig:
        """デフォルト設定で初期化
        
        Returns:
            初期化された設定オブジェクト
        """
        logger.info("Initializing default configuration")
        
        # デフォルト設定を作成
        config = AppConfig()
        
        # デフォルトの出力ディレクトリを設定
        documents_path = Path.home() / "Documents"
        if documents_path.exists():
            config.export.output_directory = str(documents_path)
        else:
            # Documents フォルダが存在しない場合はホームディレクトリを使用
            config.export.output_directory = str(Path.home())
        
        # デフォルトのフィールド選択を設定
        config.export.selected_fields = DEFAULT_SELECTED_FIELDS.copy()
        
        try:
            # 設定を保存
            self.config_manager.save_config(config.to_dict())
            logger.info("Default configuration saved successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to save default configuration: {e}")
            raise RuntimeError(f"デフォルト設定の保存に失敗しました: {e}")
    
    def initialize_with_user_input(self, 
                                 access_token: str = "",
                                 output_directory: str = "",
                                 selected_fields: Optional[list] = None) -> AppConfig:
        """ユーザー入力を含む設定で初期化
        
        Args:
            access_token: Asana API アクセストークン
            output_directory: 出力ディレクトリパス
            selected_fields: 選択されたフィールドのリスト
            
        Returns:
            初期化された設定オブジェクト
        """
        logger.info("Initializing configuration with user input")
        
        # デフォルト設定から開始
        config = AppConfig()
        
        # ユーザー入力を反映
        if access_token:
            config.asana.access_token = access_token
        
        if output_directory:
            # ディレクトリの存在確認
            output_path = Path(output_directory)
            if output_path.exists() and output_path.is_dir():
                config.export.output_directory = str(output_path)
            else:
                logger.warning(f"Specified output directory does not exist: {output_directory}")
                # デフォルトディレクトリを使用
                config.export.output_directory = str(Path.home() / "Documents")
        
        if selected_fields:
            # フィールド選択の検証
            from .config_schema import validate_selected_fields
            config.export.selected_fields = validate_selected_fields(selected_fields)
        
        try:
            # 設定を保存
            self.config_manager.save_config(config.to_dict())
            logger.info("User configuration saved successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to save user configuration: {e}")
            raise RuntimeError(f"設定の保存に失敗しました: {e}")
    
    def migrate_config(self, old_config: Dict[str, Any]) -> AppConfig:
        """古い設定形式から新しい形式に移行
        
        Args:
            old_config: 古い形式の設定辞書
            
        Returns:
            移行された設定オブジェクト
        """
        logger.info("Migrating configuration to new format")
        
        try:
            # 新しい設定オブジェクトを作成
            config = AppConfig()
            
            # 古い設定から値を移行
            if "asana" in old_config:
                asana_config = old_config["asana"]
                config.asana.access_token = asana_config.get("access_token", "")
                config.asana.selected_project_id = asana_config.get("selected_project_id", "")
                config.asana.selected_project_name = asana_config.get("selected_project_name", "")
            
            if "export" in old_config:
                export_config = old_config["export"]
                config.export.default_date_range = export_config.get("default_date_range", 30)
                config.export.output_directory = export_config.get("output_directory", str(Path.home() / "Documents"))
                
                # フィールド選択の移行と検証
                old_fields = export_config.get("selected_fields", DEFAULT_SELECTED_FIELDS)
                from .config_schema import validate_selected_fields
                config.export.selected_fields = validate_selected_fields(old_fields)
            
            if "ui" in old_config:
                ui_config = old_config["ui"]
                config.ui.window_size = ui_config.get("window_size", "800x600")
                config.ui.last_export_path = ui_config.get("last_export_path", "")
            
            # 移行された設定を保存
            self.config_manager.save_config(config.to_dict())
            logger.info("Configuration migration completed successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to migrate configuration: {e}")
            raise RuntimeError(f"設定の移行に失敗しました: {e}")
    
    def setup_application(self, 
                         access_token: str = "",
                         output_directory: str = "",
                         selected_fields: Optional[list] = None) -> AppConfig:
        """アプリケーションの設定をセットアップ
        
        初回起動時の設定初期化を行います。既存の設定がある場合は読み込みます。
        
        Args:
            access_token: Asana API アクセストークン（初回設定時）
            output_directory: 出力ディレクトリパス（初回設定時）
            selected_fields: 選択されたフィールドのリスト（初回設定時）
            
        Returns:
            セットアップされた設定オブジェクト
        """
        logger.info("Setting up application configuration")
        
        try:
            if self.is_first_run():
                logger.info("First run detected, initializing configuration")
                if access_token or output_directory or selected_fields:
                    return self.initialize_with_user_input(
                        access_token=access_token,
                        output_directory=output_directory,
                        selected_fields=selected_fields
                    )
                else:
                    return self.initialize_default_config()
            else:
                logger.info("Loading existing configuration")
                config_dict = self.config_manager.load_config()
                return AppConfig.from_dict(config_dict)
                
        except Exception as e:
            logger.error(f"Failed to setup application configuration: {e}")
            # エラーが発生した場合はデフォルト設定で初期化
            logger.warning("Falling back to default configuration")
            return self.initialize_default_config()
    
    def reset_to_defaults(self) -> AppConfig:
        """設定をデフォルトにリセット
        
        Returns:
            リセットされた設定オブジェクト
        """
        logger.info("Resetting configuration to defaults")
        
        try:
            # 既存の設定をリセット
            self.config_manager.reset_config()
            
            # デフォルト設定で初期化
            return self.initialize_default_config()
            
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")
            raise RuntimeError(f"設定のリセットに失敗しました: {e}")
    
    def get_config_info(self) -> Dict[str, Any]:
        """設定情報を取得
        
        Returns:
            設定ファイルの情報
        """
        return {
            "config_path": self.config_manager.get_config_path(),
            "config_exists": self.config_manager.config_exists(),
            "is_first_run": self.is_first_run()
        }