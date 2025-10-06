"""
データモデル定義

Asana API から取得するデータの構造を定義するデータクラス
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import re


@dataclass
class Project:
    """Asana プロジェクトを表すデータクラス"""
    id: str
    name: str
    
    def __post_init__(self):
        """初期化後の検証処理"""
        self.validate()
    
    def validate(self):
        """プロジェクトデータの検証"""
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Project ID は空でない文字列である必要があります")
        
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Project name は空でない文字列である必要があります")
        
        # ID の形式チェック（Asana の ID は数字のみ）
        if not re.match(r'^\d+$', self.id):
            raise ValueError("Project ID は数字のみで構成される必要があります")


@dataclass
class Task:
    """Asana タスクを表すデータクラス"""
    id: str
    name: str
    created_at: datetime
    modified_at: datetime
    completed: bool
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    notes: str = ""
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の検証処理"""
        self.validate()
    
    def validate(self):
        """タスクデータの検証"""
        # 必須フィールドの検証
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Task ID は空でない文字列である必要があります")
        
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Task name は空でない文字列である必要があります")
        
        # ID の形式チェック（Asana の ID は数字のみ）
        if not re.match(r'^\d+$', self.id):
            raise ValueError("Task ID は数字のみで構成される必要があります")
        
        # 日時フィールドの検証
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at は datetime オブジェクトである必要があります")
        
        if not isinstance(self.modified_at, datetime):
            raise ValueError("modified_at は datetime オブジェクトである必要があります")
        
        # 論理的な日時チェック
        if self.created_at > self.modified_at:
            raise ValueError("作成日時は更新日時より前である必要があります")
        
        # completed フィールドの検証
        if not isinstance(self.completed, bool):
            raise ValueError("completed は boolean 値である必要があります")
        
        # オプショナルフィールドの検証
        if self.assignee is not None and not isinstance(self.assignee, str):
            raise ValueError("assignee は文字列または None である必要があります")
        
        if self.due_date is not None and not isinstance(self.due_date, date):
            raise ValueError("due_date は date オブジェクトまたは None である必要があります")
        
        if not isinstance(self.notes, str):
            raise ValueError("notes は文字列である必要があります")
        
        if not isinstance(self.custom_fields, dict):
            raise ValueError("custom_fields は辞書である必要があります")
    
    def to_dict(self, selected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        タスクを辞書形式に変換（Excel 出力用）
        
        Args:
            selected_fields: 出力するフィールドのリスト。None の場合は全フィールド
            
        Returns:
            タスクデータの辞書
        """
        base_data = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'completed': self.completed,
            'assignee': self.assignee,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'notes': self.notes
        }
        
        # カスタムフィールドを追加（キーは既にcustom_形式）
        for key, value in self.custom_fields.items():
            base_data[key] = value
        
        # 選択されたフィールドのみを返す
        if selected_fields:
            return {key: base_data.get(key) for key in selected_fields if key in base_data}
        
        return base_data
    
    def is_in_date_range(self, start_date: date, end_date: date) -> bool:
        """
        タスクが指定された日付範囲内にあるかチェック
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            日付範囲内の場合 True
        """
        task_date = self.created_at.date()
        return start_date <= task_date <= end_date


@dataclass
class TaskField:
    """タスクフィールドの定義を表すデータクラス"""
    name: str
    display_name: str
    field_type: str
    required: bool = False
    
    def __post_init__(self):
        """初期化後の検証処理"""
        self.validate()
    
    def validate(self):
        """フィールド定義の検証"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Field name は空でない文字列である必要があります")
        
        if not self.display_name or not isinstance(self.display_name, str):
            raise ValueError("Display name は空でない文字列である必要があります")
        
        if not self.field_type or not isinstance(self.field_type, str):
            raise ValueError("Field type は空でない文字列である必要があります")
        
        if not isinstance(self.required, bool):
            raise ValueError("required は boolean 値である必要があります")


# 利用可能なタスクフィールドの定義
DEFAULT_TASK_FIELDS = [
    TaskField("id", "タスクID", "string", True),
    TaskField("name", "タスク名", "string", True),
    TaskField("created_at", "作成日時", "datetime", True),
    TaskField("modified_at", "更新日時", "datetime", False),
    TaskField("completed", "完了状態", "boolean", False),
    TaskField("assignee", "担当者", "string", False),
    TaskField("due_date", "期限", "date", False),
    TaskField("notes", "メモ", "text", False),
]