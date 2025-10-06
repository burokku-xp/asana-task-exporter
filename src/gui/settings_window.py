"""
設定ウィンドウクラス - Asana Task Exporter の設定画面

API トークン設定、プロジェクト選択、フィールド選択機能を提供します。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Callable
import threading

from ..business.config_manager import ConfigManager
from ..data.asana_client import AsanaClient, AsanaAPIError, AsanaAuthenticationError
from ..data.models import Project
from ..utils.logger import get_logger
from ..utils.error_handler import AuthenticationError, APIError, NetworkError

logger = get_logger(__name__)


class SettingsWindow:
    """設定ウィンドウクラス
    
    API トークン設定、プロジェクト選択、フィールド選択機能を提供
    """
    
    def __init__(self, parent: tk.Tk, config_manager: ConfigManager, 
                 on_settings_saved: Optional[Callable] = None):
        """
        SettingsWindow を初期化
        
        Args:
            parent: 親ウィンドウ
            config_manager: 設定管理インスタンス
            on_settings_saved: 設定保存時のコールバック関数
        """
        self.parent = parent
        self.config_manager = config_manager
        self.on_settings_saved = on_settings_saved
        
        # 現在の設定を読み込み
        self.current_config = self.config_manager.load_config()
        
        # UI 変数
        self.api_token_var = tk.StringVar()
        self.selected_project_var = tk.StringVar()
        self.connection_status_var = tk.StringVar()
        
        # データ
        self.projects: List[Project] = []
        self.available_fields: List[Dict[str, str]] = []
        self.field_vars: Dict[str, tk.BooleanVar] = {}
        self.current_api_client: Optional[AsanaClient] = None
        
        # UI コンポーネント
        self.window: Optional[tk.Toplevel] = None
        self.project_combobox: Optional[ttk.Combobox] = None
        self.test_button: Optional[ttk.Button] = None
        self.save_button: Optional[ttk.Button] = None
        self.fields_frame: Optional[ttk.Frame] = None
        
        self.create_window()
        self.load_current_settings()
        
    def create_window(self):
        """設定ウィンドウを作成"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("設定")
        self.window.geometry("750x800")
        self.window.resizable(True, True)
        
        # モーダルウィンドウに設定
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # ウィンドウを中央に配置
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (750 // 2)
        y = (self.window.winfo_screenheight() // 2) - (800 // 2)
        self.window.geometry(f"750x800+{x}+{y}")
        
        # メインフレーム
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # スクロール可能なフレーム
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 設定セクションを作成
        self._create_api_section(scrollable_frame)
        self._create_project_section(scrollable_frame)
        self._create_fields_section(scrollable_frame)
        self._create_log_section(scrollable_frame)
        self._create_buttons_section(scrollable_frame)
        
        # ウィンドウクローズ時の処理
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def _create_api_section(self, parent):
        """API トークン設定セクションを作成"""
        api_frame = ttk.LabelFrame(parent, text="Asana API 設定", padding="15")
        api_frame.pack(fill=tk.X, pady=(0, 20))
        
        # API トークン入力
        tk.Label(api_frame, text="API トークン:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        token_frame = ttk.Frame(api_frame)
        token_frame.pack(fill=tk.X, pady=(5, 10))
        
        token_entry = ttk.Entry(token_frame, textvariable=self.api_token_var, 
                               show="*", width=50)
        token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # トークン表示/非表示ボタン
        self.show_token_var = tk.BooleanVar()
        show_token_btn = ttk.Checkbutton(token_frame, text="表示", 
                                        variable=self.show_token_var,
                                        command=self._toggle_token_visibility)
        show_token_btn.pack(side=tk.RIGHT)
        
        self.token_entry = token_entry
        
        # API トークン取得方法の説明
        help_text = """
API トークンの取得方法:
1. Asana にログインし、右上のプロフィール画像をクリック
2. 「My Settings」→「Apps」→「Manage Developer Apps」
3. 「Create New Personal Access Token」をクリック
4. トークン名を入力し、「Create token」をクリック
5. 表示されたトークンをコピーして上記に貼り付け
        """
        
        help_label = tk.Label(api_frame, text=help_text.strip(), 
                             justify=tk.LEFT, font=("Arial", 8), 
                             fg="gray", wraplength=550)
        help_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 接続テストボタンと結果表示
        test_frame = ttk.Frame(api_frame)
        test_frame.pack(fill=tk.X)
        
        self.test_button = ttk.Button(test_frame, text="接続テスト", 
                                     command=self.test_connection)
        self.test_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.connection_status_label = tk.Label(test_frame, 
                                               textvariable=self.connection_status_var,
                                               font=("Arial", 9))
        self.connection_status_label.pack(side=tk.LEFT)
        
    def _create_project_section(self, parent):
        """プロジェクト選択セクションを作成"""
        project_frame = ttk.LabelFrame(parent, text="プロジェクト選択", padding="15")
        project_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(project_frame, text="プロジェクト:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        project_select_frame = ttk.Frame(project_frame)
        project_select_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.project_combobox = ttk.Combobox(project_select_frame,
                                           textvariable=self.selected_project_var,
                                           width=50)
        self.project_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        refresh_projects_btn = ttk.Button(project_select_frame, text="更新", 
                                         command=self.refresh_projects)
        refresh_projects_btn.pack(side=tk.RIGHT)

        # プロジェクト選択のヘルプ
        help_text = "※接続テスト後、「更新」ボタンでプロジェクト一覧を取得できます。\n  または、プロジェクトIDを直接入力することもできます。"
        help_label = tk.Label(project_frame, text=help_text,
                            justify=tk.LEFT, font=("Arial", 8),
                            fg="gray", wraplength=700)
        help_label.pack(anchor=tk.W, pady=(5, 5))

        # プロジェクト情報表示
        self.project_info_var = tk.StringVar()
        self.project_info_label = tk.Label(project_frame,
                                          textvariable=self.project_info_var,
                                          font=("Arial", 8), fg="blue")
        self.project_info_label.pack(anchor=tk.W)
        
    def _create_fields_section(self, parent):
        """フィールド選択セクションを作成"""
        self.fields_frame = ttk.LabelFrame(parent, text="エクスポートフィールド選択", padding="15")
        self.fields_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(self.fields_frame, text="出力するフィールドを選択:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # フィールド選択エリア（後で動的に作成）
        self.fields_container = ttk.Frame(self.fields_frame)
        self.fields_container.pack(fill=tk.X)
        
        # 全選択/全解除ボタン
        select_buttons_frame = ttk.Frame(self.fields_frame)
        select_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(select_buttons_frame, text="全選択", 
                  command=self.select_all_fields).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(select_buttons_frame, text="全解除",
                  command=self.deselect_all_fields).pack(side=tk.LEFT)

    def _create_log_section(self, parent):
        """ログ表示セクションを作成"""
        log_frame = ttk.LabelFrame(parent, text="デバッグログ（リアルタイム）", padding="15")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # ログテキストエリア
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        # スクロールバー
        log_scrollbar = ttk.Scrollbar(log_container)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # テキストウィジェット
        self.log_text = tk.Text(log_container, height=10, width=80,
                               wrap=tk.WORD, font=("Consolas", 9),
                               yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)

        # ログクリアボタン
        ttk.Button(log_frame, text="ログクリア",
                  command=self.clear_log).pack(anchor=tk.E, pady=(5, 0))

    def _create_buttons_section(self, parent):
        """ボタンセクションを作成"""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 右寄せでボタンを配置
        button_container = ttk.Frame(buttons_frame)
        button_container.pack(side=tk.RIGHT)
        
        ttk.Button(button_container, text="キャンセル", 
                  command=self.on_close).pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_button = ttk.Button(button_container, text="保存", 
                                     command=self.save_settings,
                                     style="Accent.TButton")
        self.save_button.pack(side=tk.LEFT)
        
    def _toggle_token_visibility(self):
        """API トークンの表示/非表示を切り替え"""
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
            
    def load_current_settings(self):
        """現在の設定を UI に読み込み"""
        try:
            self.add_log("=== 設定ウィンドウを起動しました ===", "INFO")

            # API トークンを設定
            api_token = self.current_config.get('asana', {}).get('access_token', '')
            self.api_token_var.set(api_token)

            if api_token:
                self.add_log(f"APIトークンが設定されています (長さ: {len(api_token)}文字)", "INFO")
            else:
                self.add_log("APIトークンが未設定です", "WARNING")

            # プロジェクト情報を設定
            project_name = self.current_config.get('asana', {}).get('selected_project_name', '')
            if project_name:
                self.selected_project_var.set(project_name)
                self.project_info_var.set(f"現在選択中: {project_name}")
                self.add_log(f"前回選択されたプロジェクト: {project_name}", "INFO")

            # フィールド選択を設定
            self._populate_default_fields()

            # API トークンがある場合は接続状態を表示
            if api_token:
                self.connection_status_var.set("未テスト")
                self.add_log("「接続テスト」ボタンをクリックして接続を確認してください", "INFO")
            else:
                self.connection_status_var.set("API トークンを入力してください")

        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            self.add_log(f"設定の読み込みに失敗しました: {str(e)}", "ERROR")
            messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {str(e)}")
            
    def _populate_default_fields(self):
        """デフォルトフィールドを設定"""
        # 利用可能なフィールド一覧（基本フィールド）
        default_fields = [
            {'key': 'id', 'label': 'タスク ID', 'type': 'text', 'required': False},
            {'key': 'name', 'label': 'タスク名', 'type': 'text', 'required': True},
            {'key': 'created_at', 'label': '作成日時', 'type': 'datetime', 'required': True},
            {'key': 'modified_at', 'label': '更新日時', 'type': 'datetime', 'required': False},
            {'key': 'completed', 'label': '完了状態', 'type': 'boolean', 'required': False},
            {'key': 'assignee', 'label': '担当者', 'type': 'text', 'required': False},
            {'key': 'due_date', 'label': '期限日', 'type': 'date', 'required': False},
            {'key': 'notes', 'label': 'メモ', 'type': 'text', 'required': False}
        ]
        
        self.available_fields = default_fields
        
        # 現在選択されているフィールド
        selected_fields = self.current_config.get('export', {}).get('selected_fields', [
            'name', 'created_at', 'assignee', 'completed', 'due_date'
        ])
        
        # フィールドチェックボックスを作成
        self._create_field_checkboxes(selected_fields)
        
    def _create_field_checkboxes(self, selected_fields: List[str]):
        """フィールドチェックボックスを作成"""
        # 既存のチェックボックスをクリア
        for widget in self.fields_container.winfo_children():
            widget.destroy()
        self.field_vars.clear()
        
        if not self.available_fields:
            no_fields_label = tk.Label(self.fields_container, 
                                     text="フィールド情報を取得できませんでした",
                                     font=("Arial", 9), fg="gray")
            no_fields_label.pack(pady=10)
            return
        
        # フィールドをカテゴリ別に分類
        basic_fields = [f for f in self.available_fields if not f['key'].startswith('custom_')]
        custom_fields = [f for f in self.available_fields if f['key'].startswith('custom_')]
        
        current_row = 0
        
        # 基本フィールドセクション
        if basic_fields:
            basic_label = tk.Label(self.fields_container, text="基本フィールド:", 
                                 font=("Arial", 9, "bold"))
            basic_label.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
            current_row += 1
            
            for i, field in enumerate(basic_fields):
                row = current_row + (i // 2)
                col = i % 2
                
                var = tk.BooleanVar()
                var.set(field['key'] in selected_fields)
                self.field_vars[field['key']] = var
                
                # 必須フィールドの表示
                display_text = field['label']
                if field.get('required', False):
                    display_text += " *"
                
                checkbox = ttk.Checkbutton(self.fields_container, 
                                         text=display_text,
                                         variable=var)
                checkbox.grid(row=row, column=col, sticky=tk.W, padx=(0, 20), pady=2)
                
                # 必須フィールドは無効化
                if field.get('required', False):
                    checkbox.config(state="disabled")
                    var.set(True)  # 必須フィールドは常に選択状態
            
            current_row += (len(basic_fields) + 1) // 2
        
        # カスタムフィールドセクション
        if custom_fields:
            custom_label = tk.Label(self.fields_container, text="カスタムフィールド:", 
                                  font=("Arial", 9, "bold"))
            custom_label.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
            current_row += 1
            
            for i, field in enumerate(custom_fields):
                row = current_row + (i // 2)
                col = i % 2
                
                var = tk.BooleanVar()
                var.set(field['key'] in selected_fields)
                self.field_vars[field['key']] = var
                
                checkbox = ttk.Checkbutton(self.fields_container, 
                                         text=field['label'],
                                         variable=var)
                checkbox.grid(row=row, column=col, sticky=tk.W, padx=(0, 20), pady=2)
            
            current_row += (len(custom_fields) + 1) // 2
        
        # 必須フィールドの説明
        required_info = tk.Label(self.fields_container, 
                               text="* 必須フィールド（常に出力されます）",
                               font=("Arial", 8), fg="gray")
        required_info.grid(row=current_row, column=0, columnspan=2, 
                          sticky=tk.W, pady=(10, 0))     
   
    def test_connection(self):
        """API 接続をテスト"""
        api_token = self.api_token_var.get().strip()

        self.add_log("接続テストを開始します", "INFO")

        if not api_token:
            self.add_log("APIトークンが入力されていません", "ERROR")
            self.connection_status_var.set("API トークンを入力してください")
            messagebox.showwarning("警告", "API トークンを入力してください")
            return

        self.add_log(f"APIトークン: {api_token[:10]}... (長さ: {len(api_token)}文字)", "DEBUG")

        # UI を無効化
        self.test_button.config(state="disabled")
        self.connection_status_var.set("接続テスト中...")
        self.add_log("Asana APIに接続中...", "INFO")

        # 別スレッドで接続テストを実行
        thread = threading.Thread(target=self._test_connection_worker, args=(api_token,))
        thread.daemon = True
        thread.start()
        
    def _test_connection_worker(self, api_token: str):
        """接続テストのワーカー（別スレッド）"""
        try:
            # トークンの詳細をログ出力（デバッグ用）
            self.window.after(0, lambda: self.add_log(f"トークン検証開始 - 長さ: {len(api_token)}", "DEBUG"))
            self.window.after(0, lambda: self.add_log(f"トークン先頭20文字: {api_token[:20]}", "DEBUG"))
            self.window.after(0, lambda: self.add_log(f"トークン末尾20文字: {api_token[-20:]}", "DEBUG"))
            self.window.after(0, lambda: self.add_log(f"トークンに空白含む: {' ' in api_token}", "DEBUG"))
            self.window.after(0, lambda: self.add_log(f"トークンに改行含む: {'\\n' in api_token or '\\r' in api_token}", "DEBUG"))

            # 暗号化チェック
            if api_token.startswith('gAAAAAB'):
                self.window.after(0, lambda: self.add_log("⚠️ 警告: トークンが暗号化されたままです！", "ERROR"))
                raise ValueError("トークンが暗号化された状態です。復号化されていません。")

            self.window.after(0, lambda: self.add_log("AsanaClientインスタンスを作成中...", "DEBUG"))
            client = AsanaClient(api_token)

            self.window.after(0, lambda: self.add_log("test_connection()を呼び出し中...", "DEBUG"))
            result = client.test_connection()

            self.window.after(0, lambda: self.add_log(f"接続テスト成功: {result}", "SUCCESS"))

            # 成功時の処理
            self.window.after(0, lambda: self._connection_test_success())

        except (AuthenticationError, AsanaAuthenticationError) as e:
            error_msg = f"認証エラー: {str(e)}"
            self.window.after(0, lambda msg=error_msg: self.add_log(msg, "ERROR"))
            self.window.after(0, lambda msg=error_msg: self._connection_test_failed(msg))
        except (APIError, AsanaAPIError) as e:
            error_msg = f"API エラー: {str(e)}"
            self.window.after(0, lambda msg=error_msg: self.add_log(msg, "ERROR"))
            self.window.after(0, lambda msg=error_msg: self._connection_test_failed(msg))
        except NetworkError as e:
            error_msg = f"ネットワークエラー: {str(e)}"
            self.window.after(0, lambda msg=error_msg: self.add_log(msg, "ERROR"))
            self.window.after(0, lambda msg=error_msg: self._connection_test_failed(msg))
        except Exception as e:
            error_msg = f"接続エラー: {str(e)}"
            import traceback
            tb = traceback.format_exc()
            self.window.after(0, lambda msg=error_msg: self.add_log(msg, "ERROR"))
            self.window.after(0, lambda t=tb: self.add_log(f"詳細:\n{t}", "ERROR"))
            self.window.after(0, lambda msg=error_msg: self._connection_test_failed(msg))
            
    def _connection_test_success(self):
        """接続テスト成功時の処理（メインスレッド）"""
        self.add_log("接続テストに成功しました！", "SUCCESS")
        self.connection_status_var.set("✓ 接続成功")
        self.connection_status_label.config(fg="green")
        self.test_button.config(state="normal")

        # API クライアントを保存
        api_token = self.api_token_var.get().strip()
        self.current_api_client = AsanaClient(api_token)
        self.add_log("APIクライアントを保存しました", "INFO")

        # プロジェクト一覧を自動取得
        self.add_log("プロジェクト一覧の自動取得を開始します", "INFO")
        self.refresh_projects()
        
    def _connection_test_failed(self, error_message: str):
        """接続テスト失敗時の処理（メインスレッド）"""
        self.connection_status_var.set(f"✗ 接続失敗")
        self.connection_status_label.config(fg="red")
        self.test_button.config(state="normal")
        
        messagebox.showerror("接続エラー", error_message)
        
    def refresh_projects(self):
        """プロジェクト一覧を更新"""
        api_token = self.api_token_var.get().strip()

        self.add_log("プロジェクト一覧の更新を開始", "INFO")

        if not api_token:
            self.add_log("APIトークンが設定されていません", "WARNING")
            messagebox.showwarning("警告", "先に API トークンを設定し、接続テストを行ってください")
            return

        # UI を無効化
        self.project_combobox.config(state="disabled")
        self.project_info_var.set("プロジェクト一覧を取得中...")
        self.add_log("Asana APIからプロジェクト一覧を取得中...", "INFO")

        # 別スレッドでプロジェクト取得を実行
        thread = threading.Thread(target=self._refresh_projects_worker, args=(api_token,))
        thread.daemon = True
        thread.start()
        
    def _refresh_projects_worker(self, api_token: str):
        """プロジェクト取得のワーカー（別スレッド）"""
        try:
            self.window.after(0, lambda: self.add_log("AsanaClientでプロジェクトを取得中...", "DEBUG"))
            client = AsanaClient(api_token)
            projects = client.get_projects()

            self.window.after(0, lambda: self.add_log(f"プロジェクト取得成功: {len(projects)}件", "SUCCESS"))

            # 成功時の処理
            self.window.after(0, lambda: self._projects_loaded(projects))

        except Exception as e:
            error_msg = f"プロジェクト取得エラー: {str(e)}"
            logger.error(error_msg)
            self.window.after(0, lambda msg=error_msg: self.add_log(msg, "ERROR"))
            self.window.after(0, lambda msg=error_msg: self._projects_load_failed(msg))
            
    def _projects_loaded(self, projects: List[Project]):
        """プロジェクト読み込み成功時の処理（メインスレッド）"""
        self.projects = projects
        self.add_log(f"プロジェクト一覧をUIに反映: {len(projects)}件", "INFO")

        # コンボボックスに項目を設定
        project_names = [project.name for project in projects]
        self.project_combobox['values'] = project_names
        self.project_combobox.config(state="normal")  # 手動入力も可能にする
        
        # プロジェクト選択時のイベントハンドラを設定
        self.project_combobox.bind('<<ComboboxSelected>>', self._on_project_selected)
        
        # 現在選択されているプロジェクトがあれば設定
        current_project_id = self.current_config.get('asana', {}).get('selected_project_id', '')
        if current_project_id:
            for project in projects:
                if project.id == current_project_id:
                    self.selected_project_var.set(project.name)
                    self._update_available_fields()
                    break
        
        self.project_info_var.set(f"{len(projects)} 個のプロジェクトが利用可能です")
            
    def _projects_load_failed(self, error_message: str):
        """プロジェクト読み込み失敗時の処理（メインスレッド）"""
        self.add_log("プロジェクト一覧の取得に失敗しました", "ERROR")
        self.project_combobox.config(state="readonly")
        self.project_info_var.set("プロジェクトの取得に失敗しました")

        messagebox.showerror("エラー", f"プロジェクト一覧の取得に失敗しました:\n{error_message}")
        
    def _on_project_selected(self, event=None):
        """プロジェクト選択時の処理"""
        self._update_available_fields()
        
    def _update_available_fields(self):
        """選択されたプロジェクトの利用可能フィールドを更新"""
        if not self.current_api_client or not self.selected_project_var.get():
            return
        
        # 選択されたプロジェクトの ID を取得
        selected_project_name = self.selected_project_var.get()
        selected_project_id = ""
        
        for project in self.projects:
            if project.name == selected_project_name:
                selected_project_id = project.id
                break
        
        if not selected_project_id:
            return
        
        # フィールド情報を取得中の表示
        self.project_info_var.set("フィールド情報を取得中...")
        
        # 別スレッドでフィールド取得を実行
        thread = threading.Thread(target=self._update_fields_worker, args=(selected_project_id,))
        thread.daemon = True
        thread.start()
        
    def _update_fields_worker(self, project_id: str):
        """フィールド取得のワーカー（別スレッド）"""
        try:
            fields = self.current_api_client.get_task_fields(project_id)
            
            # 成功時の処理
            self.window.after(0, lambda: self._fields_loaded(fields))
            
        except Exception as e:
            logger.error(f"フィールド取得エラー: {e}")
            self.window.after(0, lambda: self._fields_load_failed(str(e)))
            
    def _fields_loaded(self, fields: List[Dict[str, str]]):
        """フィールド読み込み成功時の処理（メインスレッド）"""
        self.available_fields = fields

        # 現在選択されているフィールドを取得
        # 保存された設定から復元（プロジェクト更新後も維持される）
        selected_fields = self.current_config.get('export', {}).get('selected_fields', [
            'name', 'created_at', 'assignee', 'completed', 'due_date'
        ])

        self.add_log(f"保存されたフィールド設定を復元: {len(selected_fields)}個", "DEBUG")

        # フィールドチェックボックスを再作成（保存された選択状態を反映）
        self._create_field_checkboxes(selected_fields)
        
        # カスタムフィールド数を表示
        custom_count = len([f for f in fields if f['key'].startswith('custom_')])
        if custom_count > 0:
            self.project_info_var.set(f"基本フィールド + {custom_count} 個のカスタムフィールド")
        else:
            self.project_info_var.set("基本フィールドのみ利用可能")
            
    def _fields_load_failed(self, error_message: str):
        """フィールド読み込み失敗時の処理（メインスレッド）"""
        self.project_info_var.set("フィールド情報の取得に失敗しました")
        logger.warning(f"フィールド取得失敗、デフォルトフィールドを使用: {error_message}")
        
        # デフォルトフィールドを使用
        self._populate_default_fields()
        
    def select_all_fields(self):
        """全フィールドを選択"""
        for var in self.field_vars.values():
            var.set(True)
            
    def deselect_all_fields(self):
        """全フィールドを解除"""
        for field_key, var in self.field_vars.items():
            # 必須フィールドは解除しない
            field_info = next((f for f in self.available_fields if f['key'] == field_key), None)
            if not field_info or not field_info.get('required', False):
                var.set(False)
                
    def save_settings(self):
        """設定を保存"""
        try:
            self.add_log("設定の保存を開始します", "INFO")

            # 入力検証
            if not self._validate_settings():
                self.add_log("設定の検証に失敗しました", "WARNING")
                return

            self.add_log("設定の検証に成功しました", "SUCCESS")

            # 選択されたプロジェクトの ID を取得
            selected_project_name = self.selected_project_var.get()
            selected_project_id = ""

            for project in self.projects:
                if project.name == selected_project_name:
                    selected_project_id = project.id
                    break

            self.add_log(f"選択されたプロジェクト: {selected_project_name} (ID: {selected_project_id})", "DEBUG")

            # 選択されたフィールドを取得
            selected_fields = []
            for field_key, var in self.field_vars.items():
                if var.get():
                    selected_fields.append(field_key)

            self.add_log(f"選択されたフィールド数: {len(selected_fields)}個", "DEBUG")

            # 設定を更新
            updated_config = self.current_config.copy()

            # Asana 設定
            updated_config['asana']['access_token'] = self.api_token_var.get().strip()
            updated_config['asana']['selected_project_id'] = selected_project_id
            updated_config['asana']['selected_project_name'] = selected_project_name

            # エクスポート設定
            updated_config['export']['selected_fields'] = selected_fields

            # 設定を保存
            self.config_manager.save_config(updated_config)
            self.add_log("設定ファイルに保存しました", "SUCCESS")

            # 成功メッセージ
            messagebox.showinfo("成功", "設定を保存しました")

            # コールバック実行
            if self.on_settings_saved:
                self.on_settings_saved()

            # ウィンドウを閉じる
            self.on_close()

        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            self.add_log(f"設定の保存に失敗しました: {str(e)}", "ERROR")
            messagebox.showerror("エラー", f"設定の保存に失敗しました:\n{str(e)}")
            
    def _validate_settings(self) -> bool:
        """設定の妥当性を検証"""
        # API トークンの検証
        api_token = self.api_token_var.get().strip()
        if not api_token:
            messagebox.showerror("エラー", "API トークンを入力してください")
            return False
        
        # プロジェクト選択の検証
        if not self.selected_project_var.get():
            messagebox.showerror("エラー", "プロジェクトを選択してください")
            return False
        
        # フィールド選択の検証
        selected_fields = [key for key, var in self.field_vars.items() if var.get()]
        if not selected_fields:
            messagebox.showerror("エラー", "少なくとも1つのフィールドを選択してください")
            return False
        
        # 必須フィールドの確認
        required_fields = [f['key'] for f in self.available_fields if f.get('required', False)]
        missing_required = [field for field in required_fields if field not in selected_fields]
        if missing_required:
            # 必須フィールドの表示名を取得
            missing_labels = []
            for field_key in missing_required:
                field_info = next((f for f in self.available_fields if f['key'] == field_key), None)
                if field_info:
                    missing_labels.append(field_info['label'])
                else:
                    missing_labels.append(field_key)
            
            result = messagebox.askyesno(
                "確認",
                f"必須フィールド（{', '.join(missing_labels)}）が選択されていません。\n"
                "これらのフィールドを自動的に追加しますか？"
            )
            if result:
                for field in missing_required:
                    if field in self.field_vars:
                        self.field_vars[field].set(True)
            else:
                return False
        
        return True
        
    def on_close(self):
        """ウィンドウクローズ時の処理"""
        # APIクライアントのセッションをクローズしてリソース解放
        if self.current_api_client:
            try:
                self.current_api_client.close()
                self.add_log("APIクライアントのセッションをクローズしました", "DEBUG")
            except Exception as e:
                logger.warning(f"APIクライアントのクローズでエラー: {e}")

        self.window.grab_release()
        self.window.destroy()
        
    def show(self):
        """ウィンドウを表示"""
        if self.window:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_set()

    def add_log(self, message: str, level: str = "INFO"):
        """ログメッセージを追加"""
        if not hasattr(self, 'log_text'):
            return

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        # ログレベルに応じた色付け
        color_map = {
            "INFO": "black",
            "SUCCESS": "green",
            "WARNING": "orange",
            "ERROR": "red",
            "DEBUG": "blue"
        }

        color = color_map.get(level, "black")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        # テキストウィジェットに追加
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)

        # タグで色付け
        last_line_start = self.log_text.index("end-2c linestart")
        last_line_end = self.log_text.index("end-1c")
        tag_name = f"level_{level}"

        if tag_name not in self.log_text.tag_names():
            self.log_text.tag_config(tag_name, foreground=color)

        self.log_text.tag_add(tag_name, last_line_start, last_line_end)
        self.log_text.config(state=tk.DISABLED)

        # 自動スクロール
        self.log_text.see(tk.END)

    def clear_log(self):
        """ログをクリア"""
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.add_log("ログをクリアしました", "INFO")