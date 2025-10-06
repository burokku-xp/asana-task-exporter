"""
Asana Task Exporter メインエントリーポイント
要件 7.1: exe ファイルを実行時にシステムは追加のランタイムやライブラリなしで動作する
要件 7.3: 初回実行時にシステムは必要な設定画面を自動表示する
"""
import sys
import os
from pathlib import Path

# src ディレクトリをPythonパスに追加
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.logger import initialize_logging, get_logger
from utils.error_handler import handle_error, AsanaExporterError, ErrorType
from gui.main_window import MainWindow


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

        # アプリケーション情報をログに記録
        logger.info(f"Python バージョン: {sys.version}")
        logger.info(f"実行ディレクトリ: {os.getcwd()}")
        logger.info(f"アプリケーションパス: {sys.executable}")
        logger.info(f"起動引数: {sys.argv}")
        logger.info(f"デバッグモード: {'有効' if debug_mode else '無効'}")
        
        # GUI の初期化とメインウィンドウの表示
        logger.info("メインウィンドウを初期化しています...")
        
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
        from utils.debug_info import log_error_with_context
        log_error_with_context(error, "アプリケーション初期化")
        
        error_message = handle_error(error, "アプリケーション初期化")
        
        if logger:
            logger.critical(f"アプリケーション初期化に失敗しました: {error_message}")
            logger.critical("デバッグレポートを生成しています...")
            
            try:
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
            from utils.logger import cleanup_old_logs
            cleanup_old_logs(days=30)
        except Exception:
            pass  # クリーンアップエラーは無視


if __name__ == "__main__":
    main()