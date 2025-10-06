"""
ログ設定とログ管理機能
要件 8.2: 重要な操作を実行時にシステムは操作ログをファイルに記録する
"""
import logging
import logging.handlers
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict


class LoggerConfig:
    """ログ設定管理クラス"""
    
    def __init__(self, log_dir: Optional[str] = None, debug_mode: bool = False):
        """
        ログ設定を初期化
        
        Args:
            log_dir: ログファイル保存ディレクトリ（Noneの場合はデフォルト使用）
            debug_mode: デバッグモードの有効/無効
        """
        if log_dir is None:
            # デフォルトログディレクトリ（ユーザーのAppDataフォルダ）
            app_data = os.getenv('APPDATA', os.path.expanduser('~'))
            self.log_dir = Path(app_data) / 'AsanaTaskExporter' / 'logs'
        else:
            self.log_dir = Path(log_dir)
        
        # ログディレクトリを作成
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # ログファイル名の設定
        date_str = datetime.now().strftime('%Y%m%d')
        self.log_file = self.log_dir / f"asana_exporter_{date_str}.log"
        self.debug_log_file = self.log_dir / f"asana_exporter_debug_{date_str}.log"
        self.error_log_file = self.log_dir / f"asana_exporter_error_{date_str}.log"
        
        self.debug_mode = debug_mode
        
        # ログ設定ファイル
        self.config_file = self.log_dir / "logging_config.json"
        
        # デフォルトログ設定
        self.default_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "log_level": "DEBUG",  # DEBUGレベルに変更（一時的）
            "debug_mode": True,     # デバッグモードを有効化
            "max_file_size_mb": 10,
            "backup_count": 5,
            "console_log_level": "DEBUG",  # コンソールもDEBUGに
            "enable_performance_logging": True,
            "enable_api_request_logging": True,
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
        
    def load_config(self) -> dict:
        """ログ設定を読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # デフォルト設定とマージ
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
            except Exception as e:
                print(f"ログ設定ファイルの読み込みに失敗: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self, config: dict):
        """ログ設定を保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"ログ設定ファイルの保存に失敗: {e}")
    
    def setup_logging(self, level: Optional[str] = None, config: Optional[dict] = None) -> logging.Logger:
        """
        ログ設定をセットアップ
        
        Args:
            level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            config: ログ設定辞書
            
        Returns:
            設定済みのロガーインスタンス
        """
        # 設定を読み込み
        if config is None:
            config = self.load_config()
        
        # ログレベルを設定
        if level is None:
            level = config.get('log_level', 'INFO')
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        console_level = getattr(logging, config.get('console_log_level', 'WARNING').upper(), logging.WARNING)
        
        # ルートロガーを取得してすべてのログを受け取る
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # ルートロガーを最低レベルに設定

        # アプリケーション専用ロガーを取得
        logger = logging.getLogger('asana_exporter')
        logger.setLevel(logging.DEBUG)  # 最低レベルに設定し、ハンドラーでフィルタリング

        # 既存のハンドラーをクリア
        logger.handlers.clear()
        
        # フォーマッターを作成
        detailed_formatter = logging.Formatter(
            config.get('log_format', self.default_config['log_format']),
            datefmt=config.get('date_format', self.default_config['date_format'])
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # メインログファイルハンドラー（日次ローテーション）
        main_file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_file,
            when='midnight',
            interval=1,
            backupCount=config.get('backup_count', 30),
            encoding='utf-8'
        )
        main_file_handler.setLevel(log_level)
        main_file_handler.setFormatter(detailed_formatter)
        logger.addHandler(main_file_handler)
        
        # デバッグログファイルハンドラー（サイズローテーション）
        if config.get('debug_mode', False) or log_level <= logging.DEBUG:
            debug_file_handler = logging.handlers.RotatingFileHandler(
                filename=self.debug_log_file,
                maxBytes=config.get('max_file_size_mb', 10) * 1024 * 1024,
                backupCount=config.get('backup_count', 5),
                encoding='utf-8'
            )
            debug_file_handler.setLevel(logging.DEBUG)
            debug_file_handler.setFormatter(detailed_formatter)
            logger.addHandler(debug_file_handler)
        
        # エラーログファイルハンドラー
        error_file_handler = logging.handlers.RotatingFileHandler(
            filename=self.error_log_file,
            maxBytes=config.get('max_file_size_mb', 10) * 1024 * 1024,
            backupCount=config.get('backup_count', 5),
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_file_handler)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

        # ルートロガーにもハンドラーを追加（他のモジュールのログを出力）
        if not root_logger.handlers:
            root_logger.addHandler(main_file_handler)
            root_logger.addHandler(console_handler)
            if config.get('debug_mode', False) or log_level <= logging.DEBUG:
                root_logger.addHandler(debug_file_handler)

        # パフォーマンスログハンドラー（オプション）
        if config.get('enable_performance_logging', True):
            perf_log_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
            perf_handler = logging.handlers.TimedRotatingFileHandler(
                filename=perf_log_file,
                when='midnight',
                interval=1,
                backupCount=7,  # 1週間分
                encoding='utf-8'
            )
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(logging.Formatter(
                '%(asctime)s - PERF - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            
            # パフォーマンス専用ロガー
            perf_logger = logging.getLogger('asana_exporter.performance')
            perf_logger.setLevel(logging.INFO)
            perf_logger.addHandler(perf_handler)
            perf_logger.propagate = False
        
        # 初期化完了ログ
        logger.info("ログシステムが初期化されました")
        logger.info(f"ログレベル: {level}")
        logger.info(f"メインログファイル: {self.log_file}")
        logger.info(f"エラーログファイル: {self.error_log_file}")
        
        if config.get('debug_mode', False):
            logger.info(f"デバッグログファイル: {self.debug_log_file}")
            logger.debug("デバッグモードが有効です")
        
        return logger
    
    def set_debug_mode(self, enabled: bool):
        """デバッグモードの設定"""
        config = self.load_config()
        config['debug_mode'] = enabled
        if enabled:
            config['log_level'] = 'DEBUG'
        self.save_config(config)
        
        # ログレベルを動的に変更
        logger = logging.getLogger('asana_exporter')
        if enabled:
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                if hasattr(handler, 'baseFilename') and 'debug' in handler.baseFilename:
                    handler.setLevel(logging.DEBUG)
        
        logger.info(f"デバッグモードが{'有効' if enabled else '無効'}になりました")
    
    def get_log_files(self) -> Dict[str, str]:
        """ログファイルのパス一覧を取得"""
        return {
            'main': str(self.log_file),
            'debug': str(self.debug_log_file),
            'error': str(self.error_log_file),
            'config': str(self.config_file)
        }
    
    def cleanup_old_logs(self, days: int = 30):
        """古いログファイルをクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    print(f"古いログファイルを削除: {log_file}")
                    
        except Exception as e:
            print(f"ログファイルクリーンアップエラー: {e}")


def get_logger(name: str = 'asana_exporter') -> logging.Logger:
    """
    ロガーインスタンスを取得
    
    Args:
        name: ロガー名
        
    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)


# グローバルログ設定インスタンス
_logger_config = None


def initialize_logging(log_dir: Optional[str] = None, level: str = "INFO", 
                      debug_mode: bool = False) -> logging.Logger:
    """
    アプリケーション全体のログ設定を初期化
    
    Args:
        log_dir: ログディレクトリ
        level: ログレベル
        debug_mode: デバッグモードの有効/無効
        
    Returns:
        メインロガー
    """
    global _logger_config
    _logger_config = LoggerConfig(log_dir, debug_mode)
    return _logger_config.setup_logging(level)


def set_debug_mode(enabled: bool):
    """
    デバッグモードの設定
    
    Args:
        enabled: デバッグモードを有効にするかどうか
    """
    global _logger_config
    if _logger_config:
        _logger_config.set_debug_mode(enabled)
    else:
        print("ログシステムが初期化されていません")


def get_log_files() -> Dict[str, str]:
    """
    ログファイルのパス一覧を取得
    
    Returns:
        ログファイルパスの辞書
    """
    global _logger_config
    if _logger_config:
        return _logger_config.get_log_files()
    return {}


def cleanup_old_logs(days: int = 30):
    """
    古いログファイルをクリーンアップ
    
    Args:
        days: 保持する日数
    """
    global _logger_config
    if _logger_config:
        _logger_config.cleanup_old_logs(days)


# パフォーマンス測定用のデコレータとコンテキストマネージャ
class PerformanceLogger:
    """パフォーマンス測定用クラス"""
    
    def __init__(self, operation_name: str, logger_name: str = 'asana_exporter.performance'):
        self.operation_name = operation_name
        self.logger = logging.getLogger(logger_name)
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"開始: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"完了: {self.operation_name} - 実行時間: {duration:.3f}秒")
        else:
            self.logger.error(f"エラー終了: {self.operation_name} - 実行時間: {duration:.3f}秒 - エラー: {exc_val}")
    
    def log_checkpoint(self, checkpoint_name: str):
        """チェックポイントをログに記録"""
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(f"チェックポイント: {self.operation_name} - {checkpoint_name} - 経過時間: {elapsed:.3f}秒")


def performance_log(operation_name: str):
    """パフォーマンス測定デコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceLogger(f"{func.__name__}({operation_name})"):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# デバッグ情報ログ用のヘルパー関数
def log_system_info():
    """システム情報をログに記録"""
    logger = get_logger('asana_exporter.system')
    
    import sys
    import platform
    import psutil
    
    logger.info("=== システム情報 ===")
    logger.info(f"OS: {platform.system()} {platform.release()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"CPU: {platform.processor()}")
    logger.info(f"メモリ: {psutil.virtual_memory().total // (1024**3)} GB")
    logger.info(f"実行パス: {sys.executable}")
    logger.info(f"作業ディレクトリ: {os.getcwd()}")


def log_memory_usage(context: str = ""):
    """メモリ使用量をログに記録"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        logger = get_logger('asana_exporter.performance')
        logger.info(f"メモリ使用量{f' ({context})' if context else ''}: "
                   f"RSS={memory_info.rss // (1024**2)}MB, "
                   f"VMS={memory_info.vms // (1024**2)}MB")
    except ImportError:
        pass  # psutil がインストールされていない場合は無視


def log_api_request(method: str, url: str, status_code: int, duration: float, 
                   request_size: int = 0, response_size: int = 0):
    """API リクエスト情報をログに記録"""
    logger = get_logger('asana_exporter.api')
    logger.info(f"API: {method} {url} - {status_code} - {duration:.3f}s - "
               f"Req:{request_size}B Res:{response_size}B")