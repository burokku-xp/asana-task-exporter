"""
メインウィンドウクラス - Asana Task Exporter のメイン GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
from typing import Optional, Callable
import threading
import os

from ..business.config_manager import ConfigManager
from ..business.task_manager import TaskManager
from ..business.excel_exporter import ExcelExporter
from ..data.asana_client import AsanaClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow:
    """メインウィンドウクラス"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        self.task_manager: Optional[TaskManager] = None
        self.excel_exporter = ExcelExporter()
        
        # UI コンポーネント
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.project_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.completion_filter_var = tk.StringVar(value="both")  # both/completed/incomplete
        
        # プログレスバーとステータス表示用
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.status_label: Optional[tk.Label] = None
        
        self.setup_ui()
        self.load_initial_settings()
        
    def setup_ui(self):
        """UI の初期設定"""
        self.root.title("Asana Task Exporter")
        self.root.geometry("800x650")
        self.root.resizable(True, True)
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ウィンドウのリサイズ設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # タイトル
        title_label = tk.Label(main_frame, text="Asana Task Exporter", 
                              font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # プロジェクト選択セクション
        self._create_project_section(main_frame, row=1)
        
        # 期間選択セクション
        self._create_date_section(main_frame, row=2)
        
        # エクスポートボタンセクション
        self._create_export_section(main_frame, row=3)
        
        # 進捗表示セクション
        self._create_progress_section(main_frame, row=4)
        
        # ステータス表示セクション
        self._create_status_section(main_frame, row=5)
        
        # 設定ボタンセクション
        self._create_settings_section(main_frame, row=6)
        
    def _create_project_section(self, parent, row):
        """プロジェクト選択セクションの作成"""
        # プロジェクト選択
        project_frame = ttk.LabelFrame(parent, text="プロジェクト", padding="10")
        project_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        project_frame.columnconfigure(1, weight=1)
        
        tk.Label(project_frame, text="選択中のプロジェクト:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        project_label = tk.Label(project_frame, textvariable=self.project_var, 
                                relief="sunken", anchor="w", bg="white")
        project_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        refresh_btn = ttk.Button(project_frame, text="更新", command=self.refresh_project_info)
        refresh_btn.grid(row=0, column=2)
        
    def _create_date_section(self, parent, row):
        """期間選択セクションの作成"""
        date_frame = ttk.LabelFrame(parent, text="エクスポート期間", padding="10")
        date_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        date_frame.columnconfigure(1, weight=1)
        date_frame.columnconfigure(3, weight=1)
        
        # 開始日
        tk.Label(date_frame, text="開始日:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        start_date_entry = ttk.Entry(date_frame, textvariable=self.start_date_var, width=12)
        start_date_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 終了日
        tk.Label(date_frame, text="終了日:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        end_date_entry = ttk.Entry(date_frame, textvariable=self.end_date_var, width=12)
        end_date_entry.grid(row=0, column=3, sticky=tk.W)
        
        # 日付形式の説明
        date_format_label = tk.Label(date_frame, text="※ 日付形式: YYYY-MM-DD", 
                                    font=("Arial", 8), fg="gray")
        date_format_label.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
        
        # 期間プリセットボタン
        preset_frame = ttk.Frame(date_frame)
        preset_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(preset_frame, text="過去7日",
                  command=lambda: self.set_date_preset(7)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preset_frame, text="過去30日",
                  command=lambda: self.set_date_preset(30)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preset_frame, text="過去90日",
                  command=lambda: self.set_date_preset(90)).pack(side=tk.LEFT)

        # 完了状態フィルタ
        completion_frame = ttk.Frame(date_frame)
        completion_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))

        tk.Label(completion_frame, text="完了状態:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(completion_frame, text="すべて", variable=self.completion_filter_var,
                       value="both").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(completion_frame, text="完了のみ", variable=self.completion_filter_var,
                       value="completed").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(completion_frame, text="未完了のみ", variable=self.completion_filter_var,
                       value="incomplete").pack(side=tk.LEFT)

    def _create_export_section(self, parent, row):
        """エクスポートボタンセクションの作成"""
        export_frame = ttk.Frame(parent)
        export_frame.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        
        self.export_btn = ttk.Button(export_frame, text="Excel にエクスポート", 
                                    command=self.on_export_click, 
                                    style="Accent.TButton")
        self.export_btn.pack()
        
    def _create_progress_section(self, parent, row):
        """進捗表示セクションの作成"""
        progress_frame = ttk.LabelFrame(parent, text="進捗状況", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_label = tk.Label(progress_frame, text="待機中...", font=("Arial", 9))
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
        
    def _create_status_section(self, parent, row):
        """ステータス表示セクションの作成"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                   relief="sunken", anchor="w", bg="white", height=2)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
    def _create_settings_section(self, parent, row):
        """設定ボタンセクションの作成"""
        settings_frame = ttk.Frame(parent)
        settings_frame.grid(row=row, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(settings_frame, text="設定", 
                  command=self.on_settings_click).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(settings_frame, text="ヘルプ", 
                  command=self.show_help).pack(side=tk.LEFT)
        
    def load_initial_settings(self):
        """初期設定の読み込み"""
        try:
            config = self.config_manager.load_config()
            
            # プロジェクト情報の表示
            project_name = config.get('asana', {}).get('selected_project_name', '未設定')
            self.project_var.set(project_name)
            
            # デフォルト期間の設定（過去30日）
            self.set_date_preset(30)
            
            # ステータス更新
            if project_name == '未設定':
                self.status_var.set("設定ボタンから Asana API トークンとプロジェクトを設定してください。")
            else:
                self.status_var.set("エクスポート準備完了")
                
        except Exception as e:
            logger.error(f"初期設定読み込みエラー: {e}")
            self.show_message(f"設定の読み込みに失敗しました: {str(e)}", "error")
            
    def set_date_preset(self, days: int):
        """期間プリセットの設定"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))
        
    def refresh_project_info(self):
        """プロジェクト情報の更新"""
        try:
            config = self.config_manager.load_config()
            project_name = config.get('asana', {}).get('selected_project_name', '未設定')
            self.project_var.set(project_name)
            
            if project_name != '未設定':
                self.status_var.set("プロジェクト情報を更新しました")
            else:
                self.status_var.set("プロジェクトが設定されていません")
                
        except Exception as e:
            logger.error(f"プロジェクト情報更新エラー: {e}")
            self.show_message(f"プロジェクト情報の更新に失敗しました: {str(e)}", "error")
            
    def on_export_click(self):
        """エクスポートボタンクリック時の処理"""
        # 入力検証
        if not self._validate_inputs():
            return
            
        # ファイル保存先の選択
        filename = filedialog.asksaveasfilename(
            title="Excel ファイルの保存先を選択",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"asana_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if not filename:
            return
            
        # 非同期でエクスポート処理を実行
        self._start_export_process(filename)
        
    def _validate_inputs(self) -> bool:
        """入力値の検証"""
        try:
            # 設定確認
            config = self.config_manager.load_config()
            if not config.get('asana', {}).get('access_token'):
                self.show_message("API トークンが設定されていません。設定画面で設定してください。", "error")
                return False
                
            if not config.get('asana', {}).get('selected_project_id'):
                self.show_message("プロジェクトが選択されていません。設定画面で選択してください。", "error")
                return False
            
            # 日付検証
            start_date_str = self.start_date_var.get().strip()
            end_date_str = self.end_date_var.get().strip()
            
            if not start_date_str or not end_date_str:
                self.show_message("開始日と終了日を入力してください。", "error")
                return False
                
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                self.show_message("日付形式が正しくありません。YYYY-MM-DD 形式で入力してください。", "error")
                return False
                
            if start_date > end_date:
                self.show_message("開始日は終了日より前の日付を指定してください。", "error")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"入力検証エラー: {e}")
            self.show_message(f"入力検証でエラーが発生しました: {str(e)}", "error")
            return False
            
    def _start_export_process(self, filename: str):
        """エクスポート処理の開始（非同期）"""
        # UI を無効化
        self.export_btn.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("エクスポート処理を開始しています...")
        
        # 別スレッドでエクスポート処理を実行
        thread = threading.Thread(target=self._export_worker, args=(filename,))
        thread.daemon = True
        thread.start()
        
    def _export_worker(self, filename: str):
        """エクスポート処理のワーカー（別スレッド）"""
        try:
            # 設定読み込み
            config = self.config_manager.load_config()
            
            # API クライアント初期化
            api_client = AsanaClient(config['asana']['access_token'])
            self.task_manager = TaskManager(api_client)
            
            # 日付解析
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d").date()
            project_id = config['asana']['selected_project_id']
            
            # 進捗更新
            self.root.after(0, lambda: self._update_progress(10, "タスクを取得中..."))
            
            # タスク取得
            tasks = self.task_manager.get_tasks(project_id, start_date, end_date)

            self.root.after(0, lambda: self._update_progress(40, f"{len(tasks)} 件のタスクを取得しました"))

            # プロジェクトのフィールド情報を取得（カスタムフィールド含む）
            self.root.after(0, lambda: self._update_progress(50, "フィールド情報を取得中..."))
            fields = api_client.get_task_fields(project_id)

            # フィールド選択
            selected_fields = config.get('export', {}).get('selected_fields', [
                'name', 'created_at', 'assignee', 'completed', 'due_date'
            ])

            # 完了状態フィルタを適用
            completion_filter = self.completion_filter_var.get()
            if completion_filter == "completed":
                tasks = [t for t in tasks if t.completed]
                self.root.after(0, lambda: self._update_progress(45, f"完了タスクのみ: {len(tasks)} 件"))
            elif completion_filter == "incomplete":
                tasks = [t for t in tasks if not t.completed]
                self.root.after(0, lambda: self._update_progress(45, f"未完了タスクのみ: {len(tasks)} 件"))

            # データフィルタリング（利用可能フィールドを渡す）
            filtered_data = self.task_manager.filter_tasks_by_fields(tasks, selected_fields, fields)

            self.root.after(0, lambda: self._update_progress(70, "Excel ファイルを生成中..."))

            # フィールド名マッピング（key -> label）
            field_labels = {f['key']: f['label'] for f in fields}

            # Excel エクスポート（フィールド名マッピングを渡す）
            self.excel_exporter.export_to_excel(filtered_data, filename, selected_fields, field_labels)
            
            # 完了
            self.root.after(0, lambda: self._export_completed(filename, len(tasks)))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"エクスポート処理エラー: {error_msg}")
            self.root.after(0, lambda msg=error_msg: self._export_failed(msg))
            
    def _update_progress(self, progress: float, message: str):
        """進捗更新（メインスレッド）"""
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        self.status_var.set(message)
        
    def _export_completed(self, filename: str, task_count: int):
        """エクスポート完了処理（メインスレッド）"""
        self.progress_var.set(100)
        self.progress_label.config(text="完了")
        self.status_var.set(f"エクスポート完了: {task_count} 件のタスクを出力しました")
        
        # UI を有効化
        self.export_btn.config(state="normal")
        
        # 成功メッセージ
        result = messagebox.askyesno(
            "エクスポート完了",
            f"Excel ファイルの出力が完了しました。\n\n"
            f"ファイル: {filename}\n"
            f"タスク数: {task_count} 件\n\n"
            f"ファイルを開きますか？"
        )
        
        if result:
            try:
                os.startfile(filename)  # Windows
            except AttributeError:
                import subprocess
                subprocess.run(['open', filename])  # macOS
            except Exception as e:
                logger.warning(f"ファイルオープンエラー: {e}")
                
    def _export_failed(self, error_message: str):
        """エクスポート失敗処理（メインスレッド）"""
        self.progress_var.set(0)
        self.progress_label.config(text="エラー")
        self.status_var.set(f"エクスポートに失敗しました: {error_message}")
        
        # UI を有効化
        self.export_btn.config(state="normal")
        
        # エラーメッセージ
        self.show_message(f"エクスポートに失敗しました:\n{error_message}", "error")
        
    def show_progress(self, progress: int):
        """進捗表示（外部から呼び出し可能）"""
        self.progress_var.set(progress)
        
    def show_message(self, message: str, msg_type: str = "info"):
        """メッセージ表示"""
        self.status_var.set(message)
        
        if msg_type == "error":
            messagebox.showerror("エラー", message)
        elif msg_type == "warning":
            messagebox.showwarning("警告", message)
        elif msg_type == "info":
            messagebox.showinfo("情報", message)
            
    def on_settings_click(self):
        """設定ボタンクリック時の処理"""
        from .settings_window import SettingsWindow
        
        try:
            settings_window = SettingsWindow(
                parent=self.root,
                config_manager=self.config_manager,
                on_settings_saved=self.on_settings_saved
            )
            settings_window.show()
        except Exception as e:
            logger.error(f"設定ウィンドウ表示エラー: {e}")
            self.show_message(f"設定ウィンドウの表示に失敗しました: {str(e)}", "error")
            
    def on_settings_saved(self):
        """設定保存後のコールバック"""
        try:
            # 設定を再読み込み
            self.load_initial_settings()
            self.show_message("設定が更新されました", "info")
        except Exception as e:
            logger.error(f"設定更新エラー: {e}")
            self.show_message(f"設定の更新に失敗しました: {str(e)}", "error")
        
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
Asana Task Exporter ヘルプ

【使用方法】
1. 設定ボタンから API トークンとプロジェクトを設定
2. エクスポートする期間を選択
3. 「Excel にエクスポート」ボタンをクリック
4. 保存先を選択してエクスポート実行

【日付形式】
YYYY-MM-DD (例: 2024-01-15)

【プリセット期間】
- 過去7日、30日、90日のボタンで簡単設定

【サポート】
問題が発生した場合は、ログファイルを確認してください。
        """
        messagebox.showinfo("ヘルプ", help_text)
        
    def run(self):
        """アプリケーション実行"""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"アプリケーション実行エラー: {e}")
            self.show_message(f"アプリケーションエラー: {str(e)}", "error")