import logging
from unittest.mock import Mock, call, patch

from service.clipboard_manager import ClipboardManager
from tests.conftest import dict_to_app_config


def _make_manager(replacements: dict | None = None, paste_delay: float = 0.1):
    config = dict_to_app_config({'CLIPBOARD': {'PASTE_DELAY': str(paste_delay)}})
    return ClipboardManager(config, replacements or {})


class TestClipboardManagerInitialize:
    """ClipboardManager.initialize()のテストクラス"""

    @patch('service.clipboard_manager.is_paste_available')
    @patch('service.clipboard_manager.pyperclip.paste')
    @patch('service.clipboard_manager.pyperclip.copy', new=Mock())
    @patch('service.clipboard_manager.time.sleep', new=Mock())
    def test_initialize_success(self, mock_paste, mock_is_available):
        """正常系: 初期化成功"""
        mock_is_available.return_value = True
        mock_paste.return_value = 'クリップボード初期化テスト'

        manager = _make_manager()
        result = manager.initialize()

        assert result is True
        mock_is_available.assert_called_once()

    @patch('service.clipboard_manager.is_paste_available')
    @patch('service.clipboard_manager.pyperclip.paste')
    @patch('service.clipboard_manager.pyperclip.copy', new=Mock())
    @patch('service.clipboard_manager.time.sleep', new=Mock())
    def test_initialize_paste_unavailable(self, mock_paste, mock_is_available, caplog):
        """異常系: ペースト機能が利用不可の場合 False を返しエラーログを出力する"""
        caplog.set_level(logging.ERROR)
        mock_is_available.return_value = False
        mock_paste.return_value = 'test'

        manager = _make_manager()
        result = manager.initialize()

        assert result is False
        assert "貼り付け機能初期化失敗" in caplog.text

    @patch('service.clipboard_manager.is_paste_available')
    @patch('service.clipboard_manager.pyperclip.paste')
    @patch('service.clipboard_manager.pyperclip.copy', new=Mock())
    @patch('service.clipboard_manager.time.sleep', new=Mock())
    def test_initialize_recovery_failure(self, mock_paste, mock_is_available, caplog):
        """異常系: クリップボード復旧失敗"""
        caplog.set_level(logging.WARNING)
        mock_is_available.return_value = True
        mock_paste.return_value = 'unexpected'  # 期待値と一致しない

        manager = _make_manager()
        result = manager.initialize()

        assert result is False
        assert "クリップボード初期化テストに失敗しました" in caplog.text

    @patch('service.clipboard_manager.is_paste_available', new=Mock(side_effect=Exception("初期化エラー")))
    def test_initialize_exception(self, caplog):
        """異常系: 例外発生"""
        caplog.set_level(logging.ERROR)

        manager = _make_manager()
        result = manager.initialize()

        assert result is False
        assert "クリップボード初期化中にエラー" in caplog.text


class TestClipboardManagerCopyAndPaste:
    """ClipboardManager.copy_and_paste()のテストクラス"""

    @patch('service.clipboard_manager.threading.Thread')
    def test_copy_and_paste_starts_thread(self, mock_thread_class):
        """正常系: Paste-Threadを起動する"""
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        manager = _make_manager({"テスト": "試験"})
        manager.copy_and_paste("テスト文字列")

        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    def test_copy_and_paste_empty_text(self, caplog):
        """境界値: 空テキストは処理しない"""
        caplog.set_level(logging.WARNING)

        with patch('service.clipboard_manager.threading.Thread') as mock_thread_class:
            _make_manager().copy_and_paste("")
            mock_thread_class.assert_not_called()

    @patch('service.clipboard_manager.replace_text')
    @patch('service.clipboard_manager.safe_clipboard_copy')
    @patch('service.clipboard_manager.safe_paste_text')
    @patch('service.clipboard_manager.time.sleep')
    def test_paste_in_thread_success(self, mock_sleep, mock_paste, mock_copy, mock_replace):
        """正常系: スレッド内の処理が成功"""
        mock_replace.return_value = "試験文字列"
        mock_copy.return_value = True
        mock_paste.return_value = True

        manager = _make_manager({"テスト": "試験"})
        manager._paste_in_thread("テスト文字列")

        mock_replace.assert_called_once_with("テスト文字列", {"テスト": "試験"})
        mock_copy.assert_called_once_with("試験文字列")
        mock_sleep.assert_called_once_with(0.1)
        mock_paste.assert_called_once()

    @patch('service.clipboard_manager.replace_text')
    @patch('service.clipboard_manager.safe_clipboard_copy')
    def test_paste_in_thread_copy_failure(self, mock_copy, mock_replace, caplog):
        """異常系: クリップボードコピー失敗"""
        caplog.set_level(logging.ERROR)
        mock_replace.return_value = "置換後テキスト"
        mock_copy.return_value = False

        manager = _make_manager()
        manager._paste_in_thread("テスト")

        assert "_paste_in_thread中にエラー" in caplog.text

    @patch('service.clipboard_manager.replace_text')
    @patch('service.clipboard_manager.safe_clipboard_copy')
    @patch('service.clipboard_manager.safe_paste_text')
    @patch('service.clipboard_manager.time.sleep', new=Mock())
    def test_paste_in_thread_paste_failure_logs_error(
        self, mock_paste, mock_copy, mock_replace, caplog
    ):
        """異常系: ペースト実行失敗時にエラーログが出力される"""
        caplog.set_level(logging.ERROR)
        mock_replace.return_value = "置換後テキスト"
        mock_copy.return_value = True
        mock_paste.return_value = False  # ペースト失敗

        manager = _make_manager()
        manager._paste_in_thread("テスト")

        assert "貼り付け実行に失敗しました" in caplog.text

    @patch('service.clipboard_manager.replace_text')
    def test_paste_in_thread_empty_replaced_text(self, mock_replace, caplog):
        """境界値: 置換結果が空文字列"""
        caplog.set_level(logging.ERROR)
        mock_replace.return_value = ""

        manager = _make_manager()
        manager._paste_in_thread("テスト")

        assert "テキスト置換結果が空です" in caplog.text


class TestClipboardManagerEmergencyRecovery:
    """ClipboardManager.emergency_recovery()のテストクラス"""

    @patch('service.clipboard_manager.pyperclip.copy')
    @patch('service.clipboard_manager.pyperclip.paste')
    @patch('service.clipboard_manager.time.sleep', new=Mock())
    def test_emergency_recovery_success(self, mock_paste, mock_copy):
        """正常系: クリップボード復旧成功"""
        test_text = 'クリップボード初期化テスト'
        mock_paste.return_value = test_text

        manager = _make_manager()
        result = manager.emergency_recovery()

        assert result is True
        assert mock_copy.call_count == 2
        mock_copy.assert_has_calls([call(''), call(test_text)])
        mock_paste.assert_called_once()

    @patch('service.clipboard_manager.pyperclip.paste')
    @patch('service.clipboard_manager.pyperclip.copy', new=Mock())
    @patch('service.clipboard_manager.time.sleep', new=Mock())
    def test_emergency_recovery_paste_mismatch(self, mock_paste):
        """異常系: ペースト結果が期待値と異なる"""
        mock_paste.return_value = 'unexpected'

        manager = _make_manager()
        result = manager.emergency_recovery()

        assert result is False

    @patch('service.clipboard_manager.pyperclip.copy')
    def test_emergency_recovery_exception(self, mock_copy, caplog):
        """異常系: クリップボード操作での例外"""
        caplog.set_level(logging.ERROR)
        mock_copy.side_effect = Exception("クリップボードエラー")

        manager = _make_manager()
        result = manager.emergency_recovery()

        assert result is False
        assert "クリップボード復旧中にエラー" in caplog.text
