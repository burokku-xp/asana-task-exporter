"""
Asana Task Exporter メインエントリーポイント (Windows用)
要件 7.1: exe ファイルを実行時にシステムは追加のランタイムやライブラリなしで動作する
要件 7.3: 初回実行時にシステムは必要な設定画面を自動表示する
"""
import sys
import os
from pathlib import Path

# PyInstallerでビルドされた場合のSSL証明書パスを設定
_ssl_configured = False
if getattr(sys, 'frozen', False):
    # exeとして実行されている場合
    # PyInstallerが展開した一時ディレクトリ内の証明書パスを取得
    if hasattr(sys, '_MEIPASS'):
        # PyInstallerの一時展開ディレクトリ
        bundle_dir = Path(sys._MEIPASS)
        cert_path = str(bundle_dir / 'certifi' / 'cacert.pem')
    else:
        # フォールバック: certifiのデフォルトパス
        import certifi
        cert_path = certifi.where()

    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    _ssl_configured = True
    _ssl_cert_path = cert_path
else:
    _ssl_cert_path = None

# 絶対パスでsrcディレクトリをPythonパスに追加
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent
src_path = current_dir

# パスを追加
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 絶対インポートに変更
try:
    from src.utils.logger import initialize_logging, get_logger
    from src.utils.error_handler import handle_error, AsanaExporterError, ErrorType
    from src.gui.main_window import MainWindow
except ImportError:
    # フォールバック: 直接インポート
    import utils.logger as logger_module
    import utils.error_handler as error_handler_module
    import gui.main_window as main_window_module
    
    initialize_logging = logger_module.initialize_logging
    get_logger = logger_module.get_logger
    handle_error = error_handler_module.handle_error
    AsanaExporterError = error_handler_module.AsanaExporterError
    ErrorType = error_handler_module.ErrorType
    MainWindow = main_window_module.MainWindow


def main():
    """メインアプリケーション実行関数"""
    logger = None
    
    try:
        # デバッグモードの判定（環境変数または起動引数）
        debug_mode = (
            os.getenv('ASANA_EXPORTER_DEBUG', '').lower() in ('1', 'true', 'yes') or
            '--debug' in sys.argv
        )
        
        # ログレベルの設定
        log_level = "DEBUG" if debug_mode else "INFO"
        if '--verbose' in sys.argv:
            log_level = "DEBUG"
        elif '--quiet' in sys.argv:
            log_level = "WARNING"
        
        # ログシステムを初期化
        logger = initialize_logging(level=log_level, debug_mode=debug_mode)
        logger.info("Asana Task Exporter を開始しています...")

        # SSL証明書設定のログ出力
        if _ssl_configured:
            logger.info(f"SSL証明書設定: frozen実行モード")
            logger.info(f"SSL_CERT_FILE: {_ssl_cert_path}")
            logger.info(f"REQUESTS_CA_BUNDLE: {_ssl_cert_path}")
            logger.info(f"証明書ファイル存在確認: {os.path.exists(_ssl_cert_path) if _ssl_cert_path else 'N/A'}")
        else:
            logger.info("SSL証明書設定: 通常実行モード（システムデフォルト使用）")

        # アプリケーション情報をログに記録
        logger.info(f"Python バージョン: {sys.version}")
        logger.info(f"実行ディレクトリ: {os.getcwd()}")
        logger.info(f"アプリケーションパス: {sys.executable}")
        logger.info(f"起動引数: {sys.argv}")
        logger.info(f"デバッグモード: {'有効' if debug_mode else '無効'}")
        
        # GUI の初期化とメインウィンドウの表示
        logger.info("メインウィンドウを初期化しています...")
        
        try:
            from src.utils.logger import PerformanceLogger
        except ImportError:
            from utils.logger import PerformanceLogger
        
        with PerformanceLogger("アプリケーション初期化"):
            main_window = MainWindow()
        
        logger.info("アプリケーションの初期化が完了しました")
        logger.info("メインウィンドウを表示します")
        
        # メインウィンドウを実行
        with PerformanceLogger("アプリケーション実行"):
            main_window.run()
        
        logger.info("アプリケーションが正常終了しました")
        
    except Exception as error:
        # エラーコンテキスト情報を収集
        try:
            from src.utils.debug_info import log_error_with_context
        except ImportError:
            from utils.debug_info import log_error_with_context
        
        log_error_with_context(error, "アプリケーション初期化")
        
        error_message = handle_error(error, "アプリケーション初期化")
        
        if logger:
            logger.critical(f"アプリケーション初期化に失敗しました: {error_message}")
            logger.critical("デバッグレポートを生成しています...")
            
            try:
                try:
                    from src.utils.debug_info import save_debug_report
                except ImportError:
                    from utils.debug_info import save_debug_report
                
                report_path = save_debug_report(include_packages=True)
                logger.critical(f"デバッグレポートを保存しました: {report_path}")
            except Exception as report_error:
                logger.error(f"デバッグレポート生成に失敗: {report_error}")
        else:
            print(f"ログシステム初期化前にエラーが発生しました: {error_message}")
        
        # エラー終了
        sys.exit(1)
    
    except KeyboardInterrupt:
        if logger:
            logger.info("ユーザーによりアプリケーションが中断されました")
        sys.exit(0)
    
    finally:
        # ログファイルのクリーンアップ
        try:
            try:
                from src.utils.logger import cleanup_old_logs
            except ImportError:
                from utils.logger import cleanup_old_logs
            cleanup_old_logs(days=30)
        except Exception:
            pass  # クリーンアップエラーは無視


if __name__ == "__main__":
    main()