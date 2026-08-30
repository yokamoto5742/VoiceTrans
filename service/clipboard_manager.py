import logging
import threading
import time
from typing import Dict

import pyperclip

from service.paste_backend import is_paste_available, safe_clipboard_copy, safe_paste_text
from service.text_transformer import remove_ja_en_spaces, replace_text
from utils.app_config import AppConfig


class ClipboardManager:
    """クリップボード操作とペースト処理を管理する"""

    def __init__(self, config: AppConfig, replacements: Dict[str, str]):
        self._config = config
        self._replacements = replacements
        self._clipboard_lock = threading.Lock()

    def initialize(self) -> bool:
        """クリップボード機能を初期化してテストする"""
        try:
            if not is_paste_available():
                logging.error('貼り付け機能初期化失敗')

            result = self.emergency_recovery()
            if not result:
                logging.warning('クリップボード初期化テストに失敗しました')
            return result

        except Exception as e:
            logging.error(f'クリップボード初期化中にエラー: {str(e)}')
            return False

    def copy_and_paste(self, text: str) -> None:
        """テキストを置換してクリップボードにコピーしバックグラウンドでペーストする"""
        if not text:
            logging.warning('空のテキスト')
            return

        thread = threading.Thread(
            target=self._paste_in_thread,
            args=(text,),
            daemon=True,
            name='Paste-Thread'
        )
        thread.start()

    def _paste_in_thread(self, text: str) -> None:
        """バックグラウンドスレッドで置換→クリップボードコピー→ペーストを実行"""
        try:
            logging.debug('_paste_in_thread開始')

            replaced_text = remove_ja_en_spaces(replace_text(text, self._replacements))
            if not replaced_text:
                logging.error('テキスト置換結果が空です')
                return

            logging.debug('クリップボードへコピー開始')
            if not safe_clipboard_copy(replaced_text):
                raise Exception('クリップボードへのコピーに失敗しました')
            logging.debug('クリップボードへコピー完了')

            logging.debug(f'ペースト待機: {self._config.paste_delay}秒')
            time.sleep(self._config.paste_delay)

            logging.debug('貼り付け実行開始')
            if not safe_paste_text():
                logging.error('貼り付け実行に失敗しました')
            else:
                logging.debug('貼り付け実行成功')

        except Exception as e:
            logging.error(f'_paste_in_thread中にエラー: {type(e).__name__}: {str(e)}')

    def emergency_recovery(self) -> bool:
        """クリップボードの動作を復旧する"""
        try:
            with self._clipboard_lock:
                pyperclip.copy('')
                time.sleep(0.1)

                test_text = 'クリップボード初期化テスト'
                pyperclip.copy(test_text)
                time.sleep(0.1)

                if pyperclip.paste() == test_text:
                    return True
                else:
                    logging.error('クリップボード復旧失敗')
                    return False

        except Exception as e:
            logging.error(f'クリップボード復旧中にエラー: {str(e)}')
            return False
