"""
タスク管理とフィルタリング機能

Asana API からのタスク取得、日付範囲フィルタリング、フィールド選択機能を提供
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from ..data.asana_client import AsanaClient, AsanaAPIError
from ..data.models import Task, DEFAULT_TASK_FIELDS
from ..utils.error_handler import (
    ErrorHandler, DateValidationError, ValidationError, 
    handle_errors, ErrorContext, retry_on_error
)


class TaskManagerError(Exception):
    """TaskManager 固有のエラー"""
    pass


class TaskManager:
    """
    タスク管理クラス
    
    Asana API からのタスク取得、日付範囲とフィールドフィルタリング機能を提供
    """
    
    DEFAULT_DATE_RANGE_DAYS = 30
    MAX_DATE_RANGE_DAYS = 365
    
    def __init__(self, api_client: AsanaClient):
        """
        TaskManager を初期化
        
        Args:
            api_client: Asana API クライアント
        """
        if not isinstance(api_client, AsanaClient):
            raise ValueError("api_client は AsanaClient のインスタンスである必要があります")
        
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
    
    @retry_on_error(max_retries=2, delay=1.0, retry_on=[AsanaAPIError])
    def get_tasks(self, project_id: str, start_date: Optional[date] = None, 
                  end_date: Optional[date] = None) -> List[Task]:
        """
        指定されたプロジェクトから期間内のタスクを取得
        
        Args:
            project_id: プロジェクト ID
            start_date: 開始日（None の場合はデフォルト期間を使用）
            end_date: 終了日（None の場合はデフォルト期間を使用）
            
        Returns:
            タスクのリスト
            
        Raises:
            TaskManagerError: タスク取得に失敗した場合
            DateValidationError: 日付バリデーションに失敗した場合
        """
        with ErrorContext("タスク取得処理", reraise=True) as ctx:
            # プロジェクト ID の検証
            self.validate_project_id(project_id)
            
            # 日付範囲の設定とバリデーション
            start_date, end_date = self._prepare_date_range(start_date, end_date)
            
            self.logger.info(f"タスク取得開始: プロジェクト={project_id}, 期間={start_date} - {end_date}")
            
            try:
                # API からタスクを取得
                tasks = self.api_client.get_project_tasks(project_id, start_date, end_date)
                
                self.logger.info(f"タスク取得完了: {len(tasks)}件")
                return tasks
                
            except AsanaAPIError as e:
                error_msg = f"Asana API からのタスク取得に失敗しました: {e}"
                self.logger.error(error_msg)
                raise TaskManagerError(error_msg) from e
                
            except Exception as e:
                error_msg = f"タスク取得中に予期しないエラーが発生しました: {e}"
                self.logger.error(error_msg)
                raise TaskManagerError(error_msg) from e
    
    @handle_errors("タスクフィルタリング処理", reraise=True)
    def filter_tasks_by_fields(self, tasks: List[Task], selected_fields: List[str],
                               available_field_definitions: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        タスクリストを指定されたフィールドでフィルタリング

        Args:
            tasks: タスクのリスト
            selected_fields: 出力するフィールド名のリスト
            available_field_definitions: 利用可能なフィールド定義（カスタムフィールド含む）

        Returns:
            フィルタリングされたタスクデータの辞書リスト

        Raises:
            TaskManagerError: フィルタリングに失敗した場合
        """
        # 入力パラメータの検証
        if not isinstance(tasks, list):
            raise ValidationError("tasks はリストである必要があります", field="tasks", value=type(tasks))

        if not isinstance(selected_fields, list):
            raise ValidationError("selected_fields はリストである必要があります",
                                field="selected_fields", value=type(selected_fields))

        if not tasks:
            self.logger.warning("フィルタリング対象のタスクが空です")
            return []

        if not selected_fields:
            raise ValidationError("選択されたフィールドが空です", field="selected_fields", value=selected_fields)

        with ErrorContext("フィールドフィルタリング", reraise=True) as ctx:
            # 利用可能なフィールド名を取得
            if available_field_definitions:
                # カスタムフィールドを含む実際のフィールドリスト
                available_fields = [field['key'] for field in available_field_definitions]
                self.logger.info(f"プロジェクトから取得したフィールドを使用: {len(available_fields)}個")
            else:
                # デフォルトフィールドのみ
                available_fields = self.get_available_field_names()
                self.logger.info(f"デフォルトフィールドを使用: {len(available_fields)}個")

            # 選択されたフィールドの検証
            invalid_fields = [field for field in selected_fields if field not in available_fields]
            if invalid_fields:
                self.logger.warning(f"無効なフィールドを除外します: {invalid_fields}")
                # 無効なフィールドをフィルタリング（エラーにせず、警告のみ）
                selected_fields = [field for field in selected_fields if field in available_fields]

                if not selected_fields:
                    raise ValidationError("有効なフィールドが1つも選択されていません",
                                        field="selected_fields", value=selected_fields)
            
            # 必須フィールドのチェック
            required_fields = self.get_required_field_names()
            missing_required = [field for field in required_fields if field not in selected_fields]
            if missing_required:
                self.logger.warning(f"必須フィールドが選択されていません: {missing_required}")
                # 必須フィールドを自動追加
                selected_fields.extend(missing_required)
                selected_fields = list(set(selected_fields))  # 重複を除去
                self.logger.info(f"必須フィールドを自動追加しました: {missing_required}")
            
            self.logger.info(f"フィールドフィルタリング開始: {len(tasks)}件のタスク, {len(selected_fields)}個のフィールド")
            
            # タスクをフィルタリング
            filtered_tasks = []
            failed_tasks = []
            
            for i, task in enumerate(tasks):
                try:
                    filtered_data = task.to_dict(selected_fields)
                    filtered_tasks.append(filtered_data)
                except Exception as e:
                    failed_tasks.append((task.id, str(e)))
                    self.logger.warning(f"タスク {task.id} のフィルタリングに失敗: {e}")
                    continue
            
            # 失敗したタスクが多い場合は警告
            if failed_tasks and len(failed_tasks) > len(tasks) * 0.1:  # 10%以上失敗
                self.logger.warning(f"多数のタスクフィルタリングが失敗しました: {len(failed_tasks)}/{len(tasks)}件")
            
            self.logger.info(f"フィールドフィルタリング完了: {len(filtered_tasks)}件成功, {len(failed_tasks)}件失敗")
            
            if not filtered_tasks and tasks:
                raise TaskManagerError("すべてのタスクのフィルタリングに失敗しました")
            
            return filtered_tasks
    
    def validate_date_range(self, start_date: date, end_date: date) -> bool:
        """
        日付範囲の検証
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            検証成功の場合 True
            
        Raises:
            DateValidationError: 日付範囲が無効な場合
        """
        try:
            # 基本的な型チェック
            if not isinstance(start_date, date):
                raise DateValidationError("開始日は date オブジェクトである必要があります", start_date=start_date)
            
            if not isinstance(end_date, date):
                raise DateValidationError("終了日は date オブジェクトである必要があります", end_date=end_date)
            
            # 論理的な日付チェック
            if start_date > end_date:
                raise DateValidationError("開始日は終了日より前である必要があります", start_date=start_date, end_date=end_date)
            
            # 未来日のチェック
            today = date.today()
            if start_date > today:
                raise DateValidationError("開始日は今日以前である必要があります", start_date=start_date)
            
            if end_date > today:
                raise DateValidationError("終了日は今日以前である必要があります", end_date=end_date)
            
            # 期間の長さチェック
            date_range = (end_date - start_date).days
            if date_range > self.MAX_DATE_RANGE_DAYS:
                raise DateValidationError(f"日付範囲は{self.MAX_DATE_RANGE_DAYS}日以内である必要があります", 
                                        start_date=start_date, end_date=end_date)
            
            # 過去すぎる日付のチェック（1年前まで）
            one_year_ago = today - timedelta(days=365)
            if start_date < one_year_ago:
                raise DateValidationError("開始日は1年前以降である必要があります", start_date=start_date)
            
            self.logger.debug(f"日付範囲検証成功: {start_date} - {end_date} ({date_range}日間)")
            return True
            
        except DateValidationError:
            # DateValidationError はそのまま再発生
            raise
            
        except Exception as e:
            error_msg = f"日付範囲検証中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            raise DateValidationError(error_msg, start_date=start_date, end_date=end_date) from e
    
    def get_available_field_names(self) -> List[str]:
        """
        利用可能なタスクフィールド名のリストを取得
        
        Returns:
            フィールド名のリスト
        """
        return [field.name for field in DEFAULT_TASK_FIELDS]
    
    def get_required_field_names(self) -> List[str]:
        """
        必須タスクフィールド名のリストを取得
        
        Returns:
            必須フィールド名のリスト
        """
        return [field.name for field in DEFAULT_TASK_FIELDS if field.required]
    
    def get_field_display_names(self) -> Dict[str, str]:
        """
        フィールド名と表示名のマッピングを取得
        
        Returns:
            フィールド名をキー、表示名を値とする辞書
        """
        return {field.name: field.display_name for field in DEFAULT_TASK_FIELDS}
    
    def _prepare_date_range(self, start_date: Optional[date], end_date: Optional[date]) -> tuple[date, date]:
        """
        日付範囲の準備とデフォルト値の設定
        
        Args:
            start_date: 開始日（None の場合はデフォルト値を使用）
            end_date: 終了日（None の場合はデフォルト値を使用）
            
        Returns:
            (開始日, 終了日) のタプル
            
        Raises:
            DateValidationError: 日付バリデーションに失敗した場合
        """
        today = date.today()
        
        # デフォルト値の設定
        if start_date is None:
            start_date = today - timedelta(days=self.DEFAULT_DATE_RANGE_DAYS)
            self.logger.debug(f"開始日をデフォルト値に設定: {start_date}")
        
        if end_date is None:
            end_date = today
            self.logger.debug(f"終了日をデフォルト値に設定: {end_date}")
        
        # 日付範囲の検証
        self.validate_date_range(start_date, end_date)
        
        return start_date, end_date
    
    def get_task_count_estimate(self, project_id: str, start_date: Optional[date] = None, 
                               end_date: Optional[date] = None) -> int:
        """
        指定された条件でのタスク数の概算を取得（進捗表示用）
        
        Args:
            project_id: プロジェクト ID
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            タスク数の概算
            
        Note:
            実際の実装では API の制限により正確な数は取得困難なため、
            現在は固定値を返す。将来的に改善予定。
        """
        try:
            # 簡易的な概算（実際の API では正確な数の取得が困難）
            # 将来的には API の pagination 情報などを使用して改善
            return 100  # 暫定値
            
        except Exception as e:
            self.logger.warning(f"タスク数概算の取得に失敗: {e}")
            return 0
    
    def validate_project_id(self, project_id: str) -> bool:
        """
        プロジェクト ID の検証
        
        Args:
            project_id: プロジェクト ID
            
        Returns:
            検証成功の場合 True
            
        Raises:
            ValidationError: プロジェクト ID が無効な場合
        """
        if not project_id:
            raise ValidationError("プロジェクト ID は必須です", field="project_id", value=project_id)
        
        if not isinstance(project_id, str):
            raise ValidationError("プロジェクト ID は文字列である必要があります", field="project_id", value=project_id)
        
        # Asana の ID は数字のみで構成される
        if not project_id.isdigit():
            raise ValidationError("プロジェクト ID は数字のみで構成される必要があります", field="project_id", value=project_id)
        
        return True
    
    def get_date_range_suggestions(self) -> Dict[str, tuple[date, date]]:
        """
        よく使用される日付範囲の提案を取得
        
        Returns:
            日付範囲の提案辞書（キー: 表示名, 値: (開始日, 終了日)）
        """
        today = date.today()
        
        return {
            "過去7日間": (today - timedelta(days=7), today),
            "過去30日間": (today - timedelta(days=30), today),
            "過去90日間": (today - timedelta(days=90), today),
            "今月": (today.replace(day=1), today),
            "先月": self._get_last_month_range(),
            "過去1年間": (today - timedelta(days=365), today)
        }
    
    def _get_last_month_range(self) -> tuple[date, date]:
        """
        先月の日付範囲を取得
        
        Returns:
            (先月の開始日, 先月の終了日)
        """
        today = date.today()
        
        # 先月の最初の日
        if today.month == 1:
            last_month_start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            last_month_start = today.replace(month=today.month - 1, day=1)
        
        # 先月の最後の日
        if today.month == 1:
            last_month_end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            # 今月の最初の日の前日
            this_month_start = today.replace(day=1)
            last_month_end = this_month_start - timedelta(days=1)
        
        return last_month_start, last_month_end