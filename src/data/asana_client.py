"""
Asana API クライアント

Asana API との通信を担当するクライアントクラス
"""

import requests
import time
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from .models import Project, Task
from ..utils.error_handler import (
    APIError, NetworkError, AuthenticationError,
    handle_errors, ErrorContext, retry_on_error
)
from ..utils.debug_info import log_api_metrics, log_performance_metrics
from ..utils.logger import PerformanceLogger


class AsanaAPIError(Exception):
    """Asana API エラーの基底クラス"""
    pass


class AsanaAuthenticationError(AsanaAPIError):
    """認証エラー"""
    pass


class AsanaRateLimitError(AsanaAPIError):
    """レート制限エラー"""
    pass


class AsanaClient:
    """
    Asana API クライアント
    
    API 認証、HTTP リクエスト処理、レート制限、エラーハンドリングを提供
    """
    
    BASE_URL = "https://app.asana.com/api/1.0/"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # 秒
    
    def __init__(self, access_token: str, timeout: int = DEFAULT_TIMEOUT):
        """
        AsanaClient を初期化

        Args:
            access_token: Asana API アクセストークン
            timeout: リクエストタイムアウト（秒）
        """
        if not access_token or not isinstance(access_token, str):
            raise ValueError("access_token は空でない文字列である必要があります")

        # トークンの前後の空白を削除
        self.access_token = access_token.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # デバッグ用：トークンの詳細情報をログに記録
        self.logger.debug(f"AsanaClient初期化 - トークン長: {len(self.access_token)}")
        self.logger.debug(f"トークン先頭10文字: {self.access_token[:10] if len(self.access_token) >= 10 else self.access_token}")
        self.logger.debug(f"トークン末尾10文字: {self.access_token[-10:] if len(self.access_token) >= 10 else self.access_token}")

        # ヘッダーを設定
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'AsanaTaskExporter/1.0 (Python/requests)'
        })

        self.logger.debug(f"セッションヘッダー設定完了: Authorization={self.session.headers['Authorization'][:30]}...")

    def close(self):
        """
        セッションを閉じてリソースを解放
        """
        if self.session:
            self.session.close()
            self.logger.debug("Asana API セッションをクローズしました")

    def __enter__(self):
        """コンテキストマネージャーのサポート"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのサポート - セッションを自動的にクローズ"""
        self.close()
        return False
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        HTTP リクエストを実行
        
        Args:
            method: HTTP メソッド
            endpoint: API エンドポイント
            params: クエリパラメータ
            data: リクエストボディ
            
        Returns:
            API レスポンスデータ
            
        Raises:
            AsanaAPIError: API エラーが発生した場合
        """
        url = urljoin(self.BASE_URL, endpoint)
        
        with ErrorContext(f"API リクエスト: {method} {endpoint}", reraise=True) as ctx:
            start_time = time.time()
            request_size = 0
            response_size = 0
            retry_count = 0
            
            # リクエストサイズの計算
            if data:
                import json
                request_size = len(json.dumps(data).encode('utf-8'))
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    self.logger.debug(f"API リクエスト: {method} {url} (試行 {attempt + 1}/{self.MAX_RETRIES})")
                    self.logger.debug(f"リクエストヘッダー: {dict(self.session.headers)}")

                    request_start = time.time()
                    response = self.session.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data,
                        timeout=self.timeout
                    )
                    request_duration = time.time() - request_start

                    self.logger.debug(f"レスポンスステータス: {response.status_code}")
                    self.logger.debug(f"レスポンスヘッダー: {dict(response.headers)}")
                    
                    # レスポンスサイズの計算
                    response_size = len(response.content) if response.content else 0
                    
                    # API メトリクスをログに記録
                    log_api_metrics(
                        method=method,
                        url=endpoint,  # フルURLではなくエンドポイントのみ
                        status_code=response.status_code,
                        duration=request_duration,
                        request_size=request_size,
                        response_size=response_size,
                        retry_count=retry_count
                    )
                    
                    # レート制限のチェック
                    if response.status_code == 429:
                        retry_count += 1
                        self._handle_rate_limit(response, attempt)
                        continue
                    
                    # エラーレスポンスのチェック
                    if not response.ok:
                        self._handle_error_response(response)
                    
                    # レスポンスの JSON 解析
                    try:
                        json_response = response.json()
                        
                        # 成功時のデバッグ情報
                        if self.logger.isEnabledFor(logging.DEBUG):
                            data_count = 0
                            if isinstance(json_response, dict) and 'data' in json_response:
                                if isinstance(json_response['data'], list):
                                    data_count = len(json_response['data'])
                                elif json_response['data']:
                                    data_count = 1
                            
                            self.logger.debug(f"API レスポンス成功: {method} {endpoint} - "
                                            f"データ件数: {data_count}, サイズ: {response_size}B")
                        
                        return json_response
                        
                    except ValueError as e:
                        raise AsanaAPIError(f"API レスポンスの JSON 解析に失敗しました: {e}")
                    
                except requests.exceptions.Timeout as e:
                    retry_count += 1
                    self.logger.warning(f"リクエストタイムアウト (試行 {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    if attempt == self.MAX_RETRIES - 1:
                        # 最終的なメトリクス記録
                        log_api_metrics(method, endpoint, 0, time.time() - start_time,
                                      request_size=request_size, response_size=0, retry_count=retry_count)
                        raise NetworkError("リクエストがタイムアウトしました", original_error=e)
                    time.sleep(self.RETRY_DELAY)

                except requests.exceptions.ConnectionError as e:
                    retry_count += 1
                    self.logger.warning(f"接続エラー (試行 {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    if attempt == self.MAX_RETRIES - 1:
                        # 最終的なメトリクス記録
                        log_api_metrics(method, endpoint, 0, time.time() - start_time,
                                      request_size=request_size, response_size=0, retry_count=retry_count)
                        raise NetworkError("Asana API への接続に失敗しました", original_error=e)
                    time.sleep(self.RETRY_DELAY)

                except requests.exceptions.RequestException as e:
                    self.logger.error(f"リクエストエラー: {e}")
                    # 最終的なメトリクス記録
                    log_api_metrics(method, endpoint, 0, time.time() - start_time,
                                  request_size=request_size, response_size=0, retry_count=retry_count)
                    raise NetworkError(f"リクエストエラーが発生しました: {e}", original_error=e)

                except (AuthenticationError, APIError, NetworkError, AsanaAPIError, AsanaAuthenticationError, AsanaRateLimitError):
                    # 既知のアプリケーションエラーはそのまま再発生
                    raise

                except Exception as e:
                    # 予期しないエラーは即座に投げる（再試行しない）
                    self.logger.error(f"予期しないエラー: {e}")
                    import traceback
                    self.logger.error(f"スタックトレース:\n{traceback.format_exc()}")
                    # 最終的なメトリクス記録
                    log_api_metrics(method, endpoint, 0, time.time() - start_time,
                                  request_size=request_size, response_size=0, retry_count=retry_count)
                    raise AsanaAPIError(f"予期しないエラーが発生しました: {e}")
            
            raise AsanaAPIError("最大再試行回数に達しました")
    
    def _handle_rate_limit(self, response: requests.Response, attempt: int):
        """
        レート制限の処理

        Args:
            response: HTTP レスポンス
            attempt: 現在の試行回数
        """
        if attempt >= self.MAX_RETRIES - 1:
            raise AsanaRateLimitError("レート制限により処理を継続できません")

        # Retry-After ヘッダーから待機時間を取得
        retry_after = response.headers.get('Retry-After')
        wait_time = None

        if retry_after:
            try:
                # まず秒数として解析を試みる（整数または小数）
                wait_time = float(retry_after)
            except ValueError:
                # 秒数として解析できない場合、HTTP日付形式の可能性があるのでデフォルトにフォールバック
                self.logger.warning(f"Retry-Afterヘッダーの解析に失敗: {retry_after}")
                wait_time = None

        if wait_time is None:
            # デフォルトの待機時間（指数バックオフ）
            wait_time = (2 ** attempt) * self.RETRY_DELAY

        self.logger.warning(f"レート制限に達しました。{wait_time}秒待機します...")
        time.sleep(wait_time)
    
    def _handle_error_response(self, response: requests.Response):
        """
        エラーレスポンスの処理

        Args:
            response: HTTP レスポンス

        Raises:
            AsanaAPIError: 適切なエラータイプ
        """
        error_data = {}  # デフォルト値を設定
        try:
            error_data = response.json()
            error_message = error_data.get('errors', [{}])[0].get('message', 'Unknown error')
            error_phrase = error_data.get('errors', [{}])[0].get('phrase', '')
        except Exception:
            error_message = f"HTTP {response.status_code}: {response.reason}"
            error_phrase = ""
            error_data = {}  # JSON解析失敗時も空の辞書を保証
        
        # 詳細なエラー情報を構築
        full_error_message = error_message
        if error_phrase:
            full_error_message += f" ({error_phrase})"
        
        # ステータスコード別のエラー処理
        if response.status_code == 401:
            raise AuthenticationError(f"認証エラー: {full_error_message}")
        elif response.status_code == 403:
            raise AuthenticationError(f"アクセス権限エラー: {full_error_message}")
        elif response.status_code == 404:
            raise APIError(f"リソースが見つかりません: {full_error_message}", 
                         status_code=response.status_code, response_data=error_data)
        elif response.status_code == 422:
            raise APIError(f"リクエストデータが無効です: {full_error_message}", 
                         status_code=response.status_code, response_data=error_data)
        elif response.status_code == 429:
            raise APIError(f"API 利用制限に達しました: {full_error_message}", 
                         status_code=response.status_code, response_data=error_data)
        elif 500 <= response.status_code < 600:
            raise APIError(f"サーバーエラー: {full_error_message}", 
                         status_code=response.status_code, response_data=error_data)
        else:
            raise APIError(f"API エラー: {full_error_message}", 
                         status_code=response.status_code, response_data=error_data)
    
    @handle_errors("API接続テスト", reraise=True)
    def test_connection(self) -> bool:
        """
        API 接続をテスト
        
        Returns:
            接続成功の場合 True
            
        Raises:
            AsanaAPIError: 接続に失敗した場合
        """
        with ErrorContext("API接続テスト", reraise=True) as ctx:
            self.logger.info("API 接続をテストしています...")
            
            try:
                response = self._make_request('GET', 'users/me')
                
                if 'data' in response and response['data']:
                    user_info = response['data']
                    self.logger.info(f"API 接続テストが成功しました - ユーザー: {user_info.get('name', 'Unknown')}")
                    return True
                else:
                    raise APIError("予期しないレスポンス形式です", response_data=response)
                    
            except (AuthenticationError, APIError, NetworkError):
                # 既知のエラーはそのまま再発生
                raise
            except Exception as e:
                self.logger.error(f"API 接続テストで予期しないエラー: {e}")
                raise APIError(f"API 接続テストに失敗しました: {e}", original_error=e)
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        アクセス可能なワークスペース一覧を取得

        Returns:
            ワークスペースのリスト
        """
        response = self._make_request('GET', 'workspaces')
        return response.get('data', [])

    @handle_errors("プロジェクト一覧取得", reraise=True)
    def get_projects(self, workspace_id: Optional[str] = None) -> List[Project]:
        """
        アクセス可能なプロジェクト一覧を取得

        Args:
            workspace_id: ワークスペースID（指定しない場合は最初のワークスペースを使用）

        Returns:
            プロジェクトのリスト

        Raises:
            AsanaAPIError: API エラーが発生した場合
        """
        with PerformanceLogger("プロジェクト一覧取得") as perf:
            try:
                # ワークスペースIDが指定されていない場合、最初のワークスペースを取得
                if not workspace_id:
                    self.logger.info("ワークスペースIDを取得しています...")
                    workspaces = self.get_workspaces()
                    if not workspaces:
                        raise APIError("アクセス可能なワークスペースがありません")
                    workspace_id = workspaces[0]['gid']
                    self.logger.info(f"ワークスペースを使用: {workspaces[0].get('name', workspace_id)}")

                self.logger.info("プロジェクト一覧を取得しています...")

                response = self._make_request('GET', 'projects', params={
                    'workspace': workspace_id,
                    'limit': 100,  # 一度に取得する最大数
                    'opt_fields': 'name'
                })
                
                perf.log_checkpoint("API レスポンス受信")
                
                projects = []
                failed_count = 0
                
                for project_data in response.get('data', []):
                    try:
                        project = Project(
                            id=str(project_data['gid']),
                            name=project_data['name']
                        )
                        projects.append(project)
                        
                        self.logger.debug(f"プロジェクト解析成功: {project.name} (ID: {project.id})")
                        
                    except (KeyError, ValueError) as e:
                        failed_count += 1
                        self.logger.warning(f"プロジェクトデータの解析に失敗: {e} - データ: {project_data}")
                        continue
                
                perf.log_checkpoint("データ解析完了")
                
                # パフォーマンスメトリクスを記録
                duration = (perf.end_time.timestamp() - perf.start_time.timestamp()) if perf.end_time else 0
                log_performance_metrics(
                    operation="get_projects",
                    duration=duration,
                    additional_metrics={
                        'projects_count': len(projects),
                        'failed_parsing_count': failed_count,
                        'api_response_size': len(str(response))
                    }
                )
                
                self.logger.info(f"{len(projects)}個のプロジェクトを取得しました")
                if failed_count > 0:
                    self.logger.warning(f"{failed_count}個のプロジェクトデータの解析に失敗しました")
                
                return projects
                
            except Exception as e:
                self.logger.error(f"プロジェクト一覧の取得に失敗: {e}")
                raise
    
    def get_project_tasks(self, project_id: str, start_date: date, end_date: date) -> List[Task]:
        """
        指定されたプロジェクトから期間内のタスクを取得
        
        Args:
            project_id: プロジェクト ID
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            タスクのリスト
            
        Raises:
            AsanaAPIError: API エラーが発生した場合
        """
        if not project_id:
            raise ValueError("project_id は必須です")
        
        if start_date > end_date:
            raise ValueError("開始日は終了日より前である必要があります")
        
        try:
            self.logger.info(f"プロジェクト {project_id} のタスクを取得しています...")
            
            # タスク一覧を取得（カスタムフィールドを含む）
            response = self._make_request('GET', f'projects/{project_id}/tasks', params={
                'limit': 100,
                'opt_fields': 'name,created_at,modified_at,completed,assignee.name,due_date,notes,custom_fields.name,custom_fields.type,custom_fields.text_value,custom_fields.number_value,custom_fields.enum_value.name,custom_fields.multi_enum_values.name,custom_fields.date_value,custom_fields.people_value.name,custom_fields.display_value'
            })
            
            tasks = []
            for task_data in response.get('data', []):
                try:
                    task = self._parse_task_data(task_data)
                    
                    # 日付範囲でフィルタリング
                    if task.is_in_date_range(start_date, end_date):
                        tasks.append(task)
                        
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"タスクデータの解析に失敗: {e}")
                    continue
            
            self.logger.info(f"{len(tasks)}個のタスクを取得しました")
            return tasks
            
        except Exception as e:
            self.logger.error(f"タスク一覧の取得に失敗: {e}")
            raise
    
    def _parse_task_data(self, task_data: Dict[str, Any]) -> Task:
        """
        API レスポンスからタスクオブジェクトを作成
        
        Args:
            task_data: API から取得したタスクデータ
            
        Returns:
            Task オブジェクト
        """
        # 日時文字列をパース
        created_at = datetime.fromisoformat(task_data['created_at'].replace('Z', '+00:00'))
        modified_at = datetime.fromisoformat(task_data['modified_at'].replace('Z', '+00:00'))
        
        # 期限日をパース
        due_date = None
        if task_data.get('due_date'):
            due_date = datetime.fromisoformat(task_data['due_date']).date()
        
        # 担当者名を取得
        assignee = None
        if task_data.get('assignee'):
            assignee = task_data['assignee'].get('name')
        
        return Task(
            id=str(task_data['gid']),
            name=task_data['name'],
            created_at=created_at,
            modified_at=modified_at,
            completed=task_data.get('completed', False),
            assignee=assignee,
            due_date=due_date,
            notes=task_data.get('notes', ''),
            custom_fields=self._extract_custom_fields(task_data)
        )
    
    def get_task_fields(self, project_id: str) -> List[Dict[str, str]]:
        """
        プロジェクトで利用可能なタスクフィールド一覧を取得
        
        Args:
            project_id: プロジェクト ID
            
        Returns:
            フィールド情報のリスト（key, label, type を含む辞書）
        """
        try:
            self.logger.info(f"プロジェクト {project_id} のフィールド一覧を取得しています...")
            
            # 基本フィールド
            basic_fields = [
                {'key': 'id', 'label': 'タスク ID', 'type': 'text', 'required': False},
                {'key': 'name', 'label': 'タスク名', 'type': 'text', 'required': True},
                {'key': 'created_at', 'label': '作成日時', 'type': 'datetime', 'required': True},
                {'key': 'modified_at', 'label': '更新日時', 'type': 'datetime', 'required': False},
                {'key': 'completed', 'label': '完了状態', 'type': 'boolean', 'required': False},
                {'key': 'assignee', 'label': '担当者', 'type': 'text', 'required': False},
                {'key': 'due_date', 'label': '期限日', 'type': 'date', 'required': False},
                {'key': 'notes', 'label': 'メモ', 'type': 'text', 'required': False}
            ]
            
            # カスタムフィールドを取得（将来の実装）
            custom_fields = self._get_custom_fields(project_id)
            
            all_fields = basic_fields + custom_fields
            self.logger.info(f"{len(all_fields)}個のフィールドを取得しました")
            
            return all_fields
            
        except Exception as e:
            self.logger.error(f"フィールド一覧の取得に失敗: {e}")
            # エラーが発生した場合は基本フィールドのみ返す
            return [
                {'key': 'id', 'label': 'タスク ID', 'type': 'text', 'required': False},
                {'key': 'name', 'label': 'タスク名', 'type': 'text', 'required': True},
                {'key': 'created_at', 'label': '作成日時', 'type': 'datetime', 'required': True},
                {'key': 'modified_at', 'label': '更新日時', 'type': 'datetime', 'required': False},
                {'key': 'completed', 'label': '完了状態', 'type': 'boolean', 'required': False},
                {'key': 'assignee', 'label': '担当者', 'type': 'text', 'required': False},
                {'key': 'due_date', 'label': '期限日', 'type': 'date', 'required': False},
                {'key': 'notes', 'label': 'メモ', 'type': 'text', 'required': False}
            ]
    
    def _extract_custom_fields(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        タスクデータからカスタムフィールドの値を抽出

        Args:
            task_data: AsanaAPIから返されたタスクデータ

        Returns:
            カスタムフィールドID(custom_123...)をキーとした辞書
        """
        custom_fields = {}
        raw_fields = task_data.get('custom_fields', [])

        if not raw_fields:
            self.logger.debug(f"タスク {task_data.get('gid', 'unknown')} にカスタムフィールドがありません")
            return custom_fields

        self.logger.debug(f"タスク {task_data.get('gid', 'unknown')}: {len(raw_fields)}個のカスタムフィールドを処理中")

        for field_data in raw_fields:
            field_gid = field_data.get('gid')
            field_name = field_data.get('name', '')

            if not field_gid:
                continue

            # フィールドタイプによって値を取得
            field_type = field_data.get('type', 'text')
            value = None

            if field_type == 'text':
                value = field_data.get('text_value') or field_data.get('display_value', '')
            elif field_type == 'number':
                value = field_data.get('number_value')
            elif field_type == 'enum':
                enum_value = field_data.get('enum_value')
                if enum_value:
                    value = enum_value.get('name', '')
            elif field_type == 'multi_enum':
                enum_values = field_data.get('multi_enum_values', [])
                value = ', '.join([ev.get('name', '') for ev in enum_values])
            elif field_type == 'date':
                value = field_data.get('date_value', '')
            elif field_type == 'people':
                people = field_data.get('people_value', [])
                value = ', '.join([p.get('name', '') for p in people])
            else:
                value = field_data.get('display_value', '')

            # custom_1234567890 形式のキーで保存
            key = f"custom_{field_gid}"
            custom_fields[key] = value
            self.logger.debug(f"  {field_name} ({key}): {value}")

        return custom_fields

    def _get_custom_fields(self, project_id: str) -> List[Dict[str, str]]:
        """
        プロジェクトのカスタムフィールドを取得

        Args:
            project_id: プロジェクト ID

        Returns:
            カスタムフィールド情報のリスト
        """
        try:
            # プロジェクトのカスタムフィールドを取得
            response = self._make_request('GET', f'projects/{project_id}/custom_field_settings')

            custom_fields = []
            for field_setting in response.get('data', []):
                custom_field = field_setting.get('custom_field', {})
                if custom_field:
                    field_info = {
                        'key': f"custom_{custom_field['gid']}",
                        'label': custom_field.get('name', 'カスタムフィールド'),
                        'type': custom_field.get('type', 'text'),
                        'required': False
                    }
                    custom_fields.append(field_info)

            self.logger.info(f"{len(custom_fields)}個のカスタムフィールドを取得しました")
            return custom_fields

        except Exception as e:
            self.logger.warning(f"カスタムフィールドの取得に失敗: {e}")
            return []