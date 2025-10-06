"""
設定ファイル構造定義

Asana Task Exporter の設定ファイルの構造とスキーマを定義します。
"""

from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AsanaConfig:
    """Asana API 関連の設定"""
    access_token: str = ""
    selected_project_id: str = ""
    selected_project_name: str = ""


@dataclass
class ExportConfig:
    """エクスポート関連の設定"""
    default_date_range: int = 30
    selected_fields: List[str] = None
    output_directory: str = ""
    
    def __post_init__(self):
        if self.selected_fields is None:
            self.selected_fields = [
                "name",
                "created_at",
                "assignee", 
                "completed",
                "due_date"
            ]
        
        if not self.output_directory:
            self.output_directory = str(Path.home() / "Documents")


@dataclass
class UIConfig:
    """UI 関連の設定"""
    window_size: str = "800x600"
    last_export_path: str = ""


@dataclass
class AppConfig:
    """アプリケーション全体の設定"""
    asana: AsanaConfig = None
    export: ExportConfig = None
    ui: UIConfig = None
    
    def __post_init__(self):
        if self.asana is None:
            self.asana = AsanaConfig()
        if self.export is None:
            self.export = ExportConfig()
        if self.ui is None:
            self.ui = UIConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書形式に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """辞書から設定オブジェクトを作成"""
        asana_data = data.get('asana', {})
        export_data = data.get('export', {})
        ui_data = data.get('ui', {})
        
        return cls(
            asana=AsanaConfig(**asana_data),
            export=ExportConfig(**export_data),
            ui=UIConfig(**ui_data)
        )


# 利用可能なタスクフィールドの定義
AVAILABLE_TASK_FIELDS = {
    "name": "タスク名",
    "created_at": "作成日時",
    "modified_at": "更新日時",
    "completed": "完了状態",
    "assignee": "担当者",
    "due_date": "期限",
    "notes": "メモ",
    "tags": "タグ",
    "projects": "プロジェクト",
    "parent": "親タスク",
    "subtasks": "サブタスク数",
    "dependencies": "依存関係",
    "custom_fields": "カスタムフィールド"
}

# 必須フィールド（選択解除できないフィールド）
REQUIRED_FIELDS = ["name", "created_at"]

# デフォルトで選択されるフィールド
DEFAULT_SELECTED_FIELDS = [
    "name",
    "created_at", 
    "assignee",
    "completed",
    "due_date"
]


def get_field_display_name(field_name: str) -> str:
    """フィールド名の表示名を取得
    
    Args:
        field_name: フィールド名
        
    Returns:
        表示用の日本語名
    """
    return AVAILABLE_TASK_FIELDS.get(field_name, field_name)


def is_required_field(field_name: str) -> bool:
    """フィールドが必須かどうかを判定
    
    Args:
        field_name: フィールド名
        
    Returns:
        必須フィールドの場合 True
    """
    return field_name in REQUIRED_FIELDS


def validate_selected_fields(selected_fields: List[str]) -> List[str]:
    """選択されたフィールドを検証し、必須フィールドを追加
    
    Args:
        selected_fields: 選択されたフィールドのリスト
        
    Returns:
        検証済みのフィールドリスト（必須フィールドを含む）
    """
    if not selected_fields:
        return DEFAULT_SELECTED_FIELDS.copy()
    
    # 必須フィールドを追加
    validated_fields = list(selected_fields)
    for required_field in REQUIRED_FIELDS:
        if required_field not in validated_fields:
            validated_fields.insert(0, required_field)
    
    # 利用可能なフィールドのみを残す
    validated_fields = [
        field for field in validated_fields 
        if field in AVAILABLE_TASK_FIELDS
    ]
    
    return validated_fields