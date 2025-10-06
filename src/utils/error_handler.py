"""
エラーハンドリング基盤
要件 8.1: エラーが発生時にシステムはユーザーフレンドリーなエラーメッセージを表示する
要件 8.3: ネットワークエラーが発生時にシステムは再試行オプションを提供する
"""
import logging
import traceback
from typing import Optional, Dict, Any, List, Callable
from enum import Enum


class ErrorType(Enum):
    """エラータイプ分類"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    CONFIGURATION_ERROR = "config_error"
    UNKNOWN_ERROR = "unknown_error"


class AsanaExporterError(Exception):
    """アプリケーション基底例外クラス"""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR, 
                 details: Optional[Dict[str, Any]] = None, original_error: Optional[Exception] = None):
        """
        エラーを初期化
        
        Args:
            message: エラーメッセージ
            error_type: エラータイプ
            details: エラー詳細情報
            original_error: 元の例外
        """
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = None


class APIError(AsanaExporterError):
    """API関連エラー"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict] = None, original_error: Optional[Exception] = None):
        details = {
            'status_code': status_code,
            'response_data': response_data
        }
        super().__init__(message, ErrorType.API_ERROR, details, original_error)


class NetworkError(AsanaExporterError):
    """ネットワーク関連エラー"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.NETWORK_ERROR, original_error=original_error)


class AuthenticationError(AsanaExporterError):
    """認証関連エラー"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.AUTHENTICATION_ERROR, original_error=original_error)


class ValidationError(AsanaExporterError):
    """バリデーション関連エラー"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {
            'field': field,
            'value': value
        }
        super().__init__(message, ErrorType.VALIDATION_ERROR, details)


class DateValidationError(ValidationError):
    """日付バリデーション関連エラー"""
    
    def __init__(self, message: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None):
        details = {
            'start_date': start_date,
            'end_date': end_date
        }
        super().__init__(message, 'date_range', details)


class FileError(AsanaExporterError):
    """ファイル操作関連エラー"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, original_error: Optional[Exception] = None):
        details = {'file_path': file_path}
        super().__init__(message, ErrorType.FILE_ERROR, details, original_error)


class ConfigurationError(AsanaExporterError):
    """設定関連エラー"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {'config_key': config_key}
        super().__init__(message, ErrorType.CONFIGURATION_ERROR, details)


class ErrorHandler:
    """エラーハンドリング管理クラス"""
    
    def __init__(self):
        self.logger = logging.getLogger('asana_exporter.error_handler')
        
        # ユーザーフレンドリーなエラーメッセージマッピング
        self.user_messages = {
            ErrorType.API_ERROR: "Asana API との通信でエラーが発生しました。",
            ErrorType.NETWORK_ERROR: "ネットワーク接続でエラーが発生しました。インターネット接続を確認してください。",
            ErrorType.AUTHENTICATION_ERROR: "認証に失敗しました。API トークンを確認してください。",
            ErrorType.VALIDATION_ERROR: "入力データに問題があります。",
            ErrorType.FILE_ERROR: "ファイル操作でエラーが発生しました。",
            ErrorType.CONFIGURATION_ERROR: "設定に問題があります。",
            ErrorType.UNKNOWN_ERROR: "予期しないエラーが発生しました。"
        }
        
        # 再試行可能なエラーの設定
        self.retry_settings = {
            ErrorType.NETWORK_ERROR: {'max_retries': 3, 'delay': 2.0, 'backoff': 2.0},
            ErrorType.API_ERROR: {'max_retries': 2, 'delay': 1.0, 'backoff': 1.5}
        }
        
        # エラー統計情報
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'retry_attempts': 0,
            'successful_retries': 0
        }
    
    def handle_error(self, error: Exception, context: str = "") -> str:
        """
        エラーを処理してユーザーフレンドリーなメッセージを返す
        
        Args:
            error: 発生したエラー
            context: エラーが発生したコンテキスト
            
        Returns:
            ユーザー向けエラーメッセージ
        """
        # ログに詳細なエラー情報を記録
        self.log_error(error, context)
        
        if isinstance(error, AsanaExporterError):
            return self._handle_application_error(error)
        else:
            return self._handle_unknown_error(error)
    
    def _handle_application_error(self, error: AsanaExporterError) -> str:
        """アプリケーション定義エラーを処理"""
        base_message = self.user_messages.get(error.error_type, self.user_messages[ErrorType.UNKNOWN_ERROR])
        
        # エラータイプ別の詳細メッセージ追加
        if error.error_type == ErrorType.API_ERROR and error.details.get('status_code'):
            status_code = error.details['status_code']
            if status_code == 401:
                return f"{base_message} API トークンが無効です。設定を確認してください。"
            elif status_code == 403:
                return f"{base_message} プロジェクトへのアクセス権限がありません。"
            elif status_code == 429:
                return f"{base_message} API の利用制限に達しました。しばらく待ってから再試行してください。"
            else:
                return f"{base_message} (エラーコード: {status_code})"
        
        elif error.error_type == ErrorType.VALIDATION_ERROR and error.details.get('field'):
            field = error.details['field']
            if field == 'date_range':
                return self._handle_date_validation_error(error)
            return f"{base_message} フィールド '{field}' を確認してください。"
        
        elif error.error_type == ErrorType.FILE_ERROR and error.details.get('file_path'):
            file_path = error.details['file_path']
            return f"{base_message} ファイル: {file_path}"
        
        return f"{base_message} {str(error)}"
    
    def _handle_date_validation_error(self, error: DateValidationError) -> str:
        """日付バリデーションエラーを処理"""
        base_message = "日付の入力に問題があります。"
        
        error_msg = str(error).lower()
        
        if "開始日は終了日より前" in error_msg:
            return f"{base_message} 開始日は終了日より前の日付を入力してください。"
        elif "今日以前" in error_msg:
            return f"{base_message} 未来の日付は指定できません。"
        elif "日以内" in error_msg:
            return f"{base_message} 指定できる期間は最大365日です。"
        elif "1年前以降" in error_msg:
            return f"{base_message} 1年より前の日付は指定できません。"
        elif "date オブジェクト" in error_msg:
            return f"{base_message} 正しい日付形式で入力してください。"
        else:
            return f"{base_message} {str(error)}"
    
    def _handle_unknown_error(self, error: Exception) -> str:
        """未知のエラーを処理"""
        return f"{self.user_messages[ErrorType.UNKNOWN_ERROR]} 詳細: {str(error)}"
    
    def log_error(self, error: Exception, context: str = ""):
        """
        エラーをログに記録
        
        Args:
            error: 発生したエラー
            context: エラーが発生したコンテキスト
        """
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        if isinstance(error, AsanaExporterError):
            error_info.update({
                'application_error_type': error.error_type.value,
                'error_details': error.details
            })
        
        self.logger.error(f"エラーが発生しました: {error_info}")
    
    def should_retry(self, error: Exception) -> bool:
        """
        エラーが再試行可能かどうかを判定
        
        Args:
            error: 発生したエラー
            
        Returns:
            再試行可能な場合True
        """
        if isinstance(error, NetworkError):
            return True
        
        if isinstance(error, APIError):
            status_code = error.details.get('status_code')
            # 429 (Rate Limit) や 5xx (Server Error) は再試行可能
            return status_code in [429] or (status_code and 500 <= status_code < 600)
        
        return False
    
    def get_retry_settings(self, error: Exception) -> Dict[str, Any]:
        """
        エラーに対する再試行設定を取得
        
        Args:
            error: 発生したエラー
            
        Returns:
            再試行設定辞書
        """
        if isinstance(error, AsanaExporterError):
            return self.retry_settings.get(error.error_type, {})
        
        # 未知のエラーの場合はデフォルト設定
        return {'max_retries': 1, 'delay': 1.0, 'backoff': 1.0}
    
    def record_error_stats(self, error: Exception):
        """
        エラー統計情報を記録
        
        Args:
            error: 発生したエラー
        """
        self.error_stats['total_errors'] += 1
        
        if isinstance(error, AsanaExporterError):
            error_type = error.error_type.value
        else:
            error_type = type(error).__name__
        
        if error_type not in self.error_stats['errors_by_type']:
            self.error_stats['errors_by_type'][error_type] = 0
        self.error_stats['errors_by_type'][error_type] += 1
    
    def record_retry_attempt(self, success: bool = False):
        """
        再試行の統計情報を記録
        
        Args:
            success: 再試行が成功したかどうか
        """
        self.error_stats['retry_attempts'] += 1
        if success:
            self.error_stats['successful_retries'] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        エラー統計情報を取得
        
        Returns:
            エラー統計情報辞書
        """
        return self.error_stats.copy()
    
    def format_error_for_user(self, error: Exception, context: str = "") -> Dict[str, str]:
        """
        ユーザー向けのエラー情報を整形
        
        Args:
            error: 発生したエラー
            context: エラーコンテキスト
            
        Returns:
            ユーザー向けエラー情報辞書
        """
        user_message = self.handle_error(error, context)
        
        error_info = {
            'title': self._get_error_title(error),
            'message': user_message,
            'severity': self._get_error_severity(error),
            'can_retry': str(self.should_retry(error)),
            'context': context
        }
        
        # 解決策の提案
        suggestions = self._get_error_suggestions(error)
        if suggestions:
            error_info['suggestions'] = suggestions
        
        return error_info
    
    def _get_error_title(self, error: Exception) -> str:
        """エラータイトルを取得"""
        if isinstance(error, AsanaExporterError):
            titles = {
                ErrorType.API_ERROR: "API エラー",
                ErrorType.NETWORK_ERROR: "ネットワークエラー",
                ErrorType.AUTHENTICATION_ERROR: "認証エラー",
                ErrorType.VALIDATION_ERROR: "入力エラー",
                ErrorType.FILE_ERROR: "ファイルエラー",
                ErrorType.CONFIGURATION_ERROR: "設定エラー",
                ErrorType.UNKNOWN_ERROR: "システムエラー"
            }
            return titles.get(error.error_type, "エラー")
        return "システムエラー"
    
    def _get_error_severity(self, error: Exception) -> str:
        """エラーの重要度を取得"""
        if isinstance(error, AsanaExporterError):
            if error.error_type in [ErrorType.AUTHENTICATION_ERROR, ErrorType.CONFIGURATION_ERROR]:
                return "high"
            elif error.error_type in [ErrorType.API_ERROR, ErrorType.FILE_ERROR]:
                return "medium"
            else:
                return "low"
        return "medium"
    
    def _get_error_suggestions(self, error: Exception) -> List[str]:
        """エラーに対する解決策の提案を取得"""
        suggestions = []
        
        if isinstance(error, AsanaExporterError):
            if error.error_type == ErrorType.AUTHENTICATION_ERROR:
                suggestions = [
                    "API トークンが正しく設定されているか確認してください",
                    "Asana の設定画面で新しいトークンを生成してください",
                    "トークンの有効期限が切れていないか確認してください"
                ]
            elif error.error_type == ErrorType.NETWORK_ERROR:
                suggestions = [
                    "インターネット接続を確認してください",
                    "ファイアウォールの設定を確認してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            elif error.error_type == ErrorType.FILE_ERROR:
                suggestions = [
                    "ファイルの保存先に書き込み権限があるか確認してください",
                    "ディスクの空き容量を確認してください",
                    "別の保存先を選択してください"
                ]
            elif error.error_type == ErrorType.VALIDATION_ERROR:
                suggestions = [
                    "入力値を確認してください",
                    "必須項目がすべて入力されているか確認してください"
                ]
            elif error.error_type == ErrorType.API_ERROR:
                if isinstance(error, APIError) and error.details.get('status_code') == 429:
                    suggestions = [
                        "API の利用制限に達しました",
                        "しばらく時間をおいてから再試行してください"
                    ]
                else:
                    suggestions = [
                        "Asana API の状態を確認してください",
                        "プロジェクトへのアクセス権限を確認してください"
                    ]
        
        return suggestions


# グローバルエラーハンドラーインスタンス
_error_handler = ErrorHandler()


def handle_error(error: Exception, context: str = "") -> str:
    """
    グローバルエラーハンドラーを使用してエラーを処理
    
    Args:
        error: 発生したエラー
        context: エラーコンテキスト
        
    Returns:
        ユーザー向けエラーメッセージ
    """
    return _error_handler.handle_error(error, context)


def log_error(error: Exception, context: str = ""):
    """
    グローバルエラーハンドラーを使用してエラーをログに記録
    
    Args:
        error: 発生したエラー
        context: エラーコンテキスト
    """
    _error_handler.log_error(error, context)


def should_retry_error(error: Exception) -> bool:
    """
    エラーが再試行可能かどうかを判定
    
    Args:
        error: 発生したエラー
        
    Returns:
        再試行可能な場合True
    """
    return _error_handler.should_retry(error)


def format_error_for_user(error: Exception, context: str = "") -> Dict[str, str]:
    """
    ユーザー向けのエラー情報を整形
    
    Args:
        error: 発生したエラー
        context: エラーコンテキスト
        
    Returns:
        ユーザー向けエラー情報辞書
    """
    return _error_handler.format_error_for_user(error, context)


def get_error_stats() -> Dict[str, Any]:
    """
    エラー統計情報を取得
    
    Returns:
        エラー統計情報辞書
    """
    return _error_handler.get_error_stats()


# エラーハンドリングデコレータ
def handle_errors(context: str = "", reraise: bool = False, default_return=None):
    """
    エラーハンドリングデコレータ
    
    Args:
        context: エラーコンテキスト
        reraise: エラーを再発生させるかどうか
        default_return: エラー時のデフォルト戻り値
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _error_handler.record_error_stats(e)
                _error_handler.log_error(e, context or func.__name__)
                
                if reraise:
                    raise
                
                return default_return
        return wrapper
    return decorator


# エラーハンドリングコンテキストマネージャ
class ErrorContext:
    """エラーハンドリングコンテキストマネージャ"""
    
    def __init__(self, context: str, reraise: bool = True, 
                 on_error: Optional[Callable[[Exception], None]] = None):
        """
        エラーコンテキストを初期化
        
        Args:
            context: エラーコンテキスト
            reraise: エラーを再発生させるかどうか
            on_error: エラー発生時のコールバック関数
        """
        self.context = context
        self.reraise = reraise
        self.on_error = on_error
        self.error: Optional[Exception] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = exc_val
            _error_handler.record_error_stats(exc_val)
            _error_handler.log_error(exc_val, self.context)
            
            if self.on_error:
                try:
                    self.on_error(exc_val)
                except Exception as callback_error:
                    _error_handler.log_error(callback_error, f"{self.context} - error callback")
            
            if not self.reraise:
                return True  # エラーを抑制
        
        return False  # エラーを再発生


# 再試行機能付きエラーハンドリング
def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0,
                   retry_on: Optional[List[type]] = None):
    """
    再試行機能付きエラーハンドリングデコレータ
    
    Args:
        max_retries: 最大再試行回数
        delay: 初期待機時間（秒）
        backoff: 待機時間の倍率
        retry_on: 再試行対象のエラータイプリスト
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        _error_handler.record_retry_attempt(success=True)
                    return result
                    
                except Exception as e:
                    last_error = e
                    
                    # 再試行対象のエラーかチェック
                    should_retry = False
                    if retry_on:
                        should_retry = any(isinstance(e, error_type) for error_type in retry_on)
                    else:
                        should_retry = _error_handler.should_retry(e)
                    
                    if attempt < max_retries and should_retry:
                        _error_handler.record_retry_attempt(success=False)
                        _error_handler.logger.warning(
                            f"関数 {func.__name__} で再試行可能エラーが発生。"
                            f"試行 {attempt + 1}/{max_retries + 1}、{current_delay}秒後に再試行: {e}"
                        )
                        
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        break
            
            # 最終的にエラーを発生
            _error_handler.record_error_stats(last_error)
            _error_handler.log_error(last_error, func.__name__)
            raise last_error
            
        return wrapper
    return decorator