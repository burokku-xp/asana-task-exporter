"""
設定管理システム - ConfigManager クラス

Asana Task Exporter の設定情報を暗号化して安全に保存・読み込みする機能を提供します。
API トークン、プロジェクト設定、UI設定などを管理します。
"""

import json
import os
import copy
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """設定管理クラス
    
    設定情報の暗号化保存・読み込み、デフォルト設定の管理、
    設定値のバリデーション機能を提供します。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """ConfigManager を初期化
        
        Args:
            config_dir: 設定ファイルを保存するディレクトリ。
                       None の場合はユーザーのホームディレクトリ下に作成
        """
        if config_dir is None:
            self.config_dir = Path.home() / ".asana_task_exporter"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / "key.key"
        
        # 暗号化キーの初期化
        self._encryption_key = self._get_or_create_key()
        self._fernet = Fernet(self._encryption_key)
        
        logger.info(f"ConfigManager initialized with config directory: {self.config_dir}")
    
    def _get_or_create_key(self) -> bytes:
        """暗号化キーを取得または作成
        
        Returns:
            暗号化キー
        """
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # 新しいキーを生成
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # キーファイルの権限を制限（Windows では効果が限定的）
            try:
                os.chmod(self.key_file, 0o600)
            except OSError:
                logger.warning("Could not set restrictive permissions on key file")
            return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """機密データを暗号化
        
        Args:
            data: 暗号化する文字列
            
        Returns:
            暗号化された文字列（base64エンコード済み）
        """
        if not data:
            return ""
        
        try:
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise ValueError("データの暗号化に失敗しました")
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """暗号化されたデータを復号化
        
        Args:
            encrypted_data: 暗号化された文字列（base64エンコード済み）
            
        Returns:
            復号化された文字列
        """
        if not encrypted_data:
            return ""
        
        try:
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise ValueError("データの復号化に失敗しました")
    
    def get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得
        
        Returns:
            デフォルト設定辞書
        """
        return {
            "asana": {
                "access_token": "",
                "selected_project_id": "",
                "selected_project_name": ""
            },
            "export": {
                "default_date_range": 30,
                "selected_fields": [
                    "name",
                    "created_at",
                    "assignee",
                    "completed",
                    "due_date"
                ],
                "output_directory": str(Path.home() / "Documents")
            },
            "ui": {
                "window_size": "800x600",
                "last_export_path": ""
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """設定の妥当性を検証
        
        Args:
            config: 検証する設定辞書
            
        Returns:
            設定が有効な場合 True
            
        Raises:
            ValueError: 設定が無効な場合
        """
        try:
            # 必須セクションの存在確認
            required_sections = ["asana", "export", "ui"]
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"必須セクション '{section}' が見つかりません")
            
            # asana セクションの検証
            asana_config = config["asana"]
            if not isinstance(asana_config.get("access_token", ""), str):
                raise ValueError("access_token は文字列である必要があります")
            if not isinstance(asana_config.get("selected_project_id", ""), str):
                raise ValueError("selected_project_id は文字列である必要があります")
            if not isinstance(asana_config.get("selected_project_name", ""), str):
                raise ValueError("selected_project_name は文字列である必要があります")
            
            # export セクションの検証
            export_config = config["export"]
            if not isinstance(export_config.get("default_date_range", 0), int):
                raise ValueError("default_date_range は整数である必要があります")
            if export_config.get("default_date_range", 0) <= 0:
                raise ValueError("default_date_range は正の整数である必要があります")
            
            selected_fields = export_config.get("selected_fields", [])
            if not isinstance(selected_fields, list):
                raise ValueError("selected_fields はリストである必要があります")
            
            output_dir = export_config.get("output_directory", "")
            if not isinstance(output_dir, str):
                raise ValueError("output_directory は文字列である必要があります")
            
            # ui セクションの検証
            ui_config = config["ui"]
            window_size = ui_config.get("window_size", "")
            if not isinstance(window_size, str):
                raise ValueError("window_size は文字列である必要があります")
            
            # window_size の形式チェック（例: "800x600"）
            if window_size and 'x' in window_size:
                try:
                    width, height = window_size.split('x')
                    int(width)
                    int(height)
                except ValueError:
                    raise ValueError("window_size の形式が無効です（例: '800x600'）")
            
            return True
            
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            raise
    
    def load_config(self) -> Dict[str, Any]:
        """設定ファイルから設定を読み込み
        
        Returns:
            設定辞書。ファイルが存在しない場合はデフォルト設定を返す
        """
        if not self.config_file.exists():
            logger.info("Config file not found, returning default config")
            return self.get_default_config()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 機密データの復号化
            if config.get("asana", {}).get("access_token"):
                config["asana"]["access_token"] = self.decrypt_sensitive_data(
                    config["asana"]["access_token"]
                )
            
            # 設定の妥当性を検証
            self.validate_config(config)
            
            logger.info("Config loaded successfully")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise ValueError("設定ファイルの形式が無効です")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # エラーが発生した場合はデフォルト設定を返す
            logger.warning("Returning default config due to load error")
            return self.get_default_config()
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """設定を暗号化してファイルに保存
        
        Args:
            config: 保存する設定辞書
            
        Raises:
            ValueError: 設定が無効な場合
            IOError: ファイル保存に失敗した場合
        """
        # 設定の妥当性を検証
        self.validate_config(config)
        
        # 保存用の設定を深いコピー（元の設定を変更しないため）
        # 浅いコピーだとネストした辞書が同じオブジェクトを参照してしまう
        config_to_save = copy.deepcopy(config)
        
        # 機密データの暗号化
        if config_to_save.get("asana", {}).get("access_token"):
            config_to_save["asana"]["access_token"] = self.encrypt_sensitive_data(
                config_to_save["asana"]["access_token"]
            )
        
        try:
            # 一時ファイルに書き込んでから移動（原子的操作）
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            
            # 一時ファイルを本来のファイルに移動
            temp_file.replace(self.config_file)
            
            logger.info("Config saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            # 一時ファイルが残っている場合は削除
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"設定ファイルの保存に失敗しました: {e}")
    
    def reset_config(self) -> None:
        """設定をデフォルトにリセット
        
        設定ファイルと暗号化キーを削除し、次回起動時にデフォルト設定で初期化されるようにします。
        """
        try:
            if self.config_file.exists():
                self.config_file.unlink()
                logger.info("Config file deleted")
            
            if self.key_file.exists():
                self.key_file.unlink()
                logger.info("Key file deleted")
            
            # 新しいキーを生成
            self._encryption_key = self._get_or_create_key()
            self._fernet = Fernet(self._encryption_key)
            
            logger.info("Config reset completed")
            
        except Exception as e:
            logger.error(f"Failed to reset config: {e}")
            raise IOError(f"設定のリセットに失敗しました: {e}")
    
    def get_config_path(self) -> str:
        """設定ファイルのパスを取得
        
        Returns:
            設定ファイルの絶対パス
        """
        return str(self.config_file.absolute())
    
    def config_exists(self) -> bool:
        """設定ファイルが存在するかチェック
        
        Returns:
            設定ファイルが存在する場合 True
        """
        return self.config_file.exists()