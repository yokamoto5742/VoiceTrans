import configparser
import logging
import os
import sys

from utils.config_manager import get_config_value

# 文字起こしモードの選択肢
GEMINI_MODES = ('verbatim', 'smart')
DEFAULT_GEMINI_MODE = GEMINI_MODES[0]
DEFAULT_GEMINI_MODEL = 'gemini-3.5-transcribe'


class AppConfig:
    """設定ファイルへの型安全なアクセスを提供するファサード(窓口)"""

    def __init__(self, config: configparser.ConfigParser):
        self._config = config

    @property
    def raw_config(self) -> configparser.ConfigParser:
        """内部の ConfigParser インスタンスを返す"""
        return self._config

    # --- AUDIO ---
    @property
    def audio_sample_rate(self) -> int:
        return get_config_value(self._config, 'AUDIO', 'SAMPLE_RATE', 16000)

    @property
    def audio_channels(self) -> int:
        return get_config_value(self._config, 'AUDIO', 'CHANNELS', 1)

    @property
    def audio_chunk(self) -> int:
        return get_config_value(self._config, 'AUDIO', 'CHUNK', 1024)

    # --- PATHS ---
    @property
    def temp_dir(self) -> str:
        return get_config_value(self._config, 'PATHS', 'TEMP_DIR', 'temp')

    @property
    def cleanup_minutes(self) -> int:
        return get_config_value(self._config, 'PATHS', 'CLEANUP_MINUTES', 30)

    @property
    def replacements_file(self) -> str:
        """置換ルールファイルのパスを返す。相対パスはdataディレクトリから解決"""
        configured = get_config_value(self._config, 'PATHS', 'REPLACEMENTS_FILE', '')
        if not configured:
            return self._default_replacements_path()
        if os.path.isabs(configured):
            return configured
        return os.path.join(self._default_data_dir(), configured)

    def _default_replacements_path(self) -> str:
        if getattr(sys, 'frozen', False):
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        else:
            base_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        return os.path.join(base_path, 'replacements.txt')

    # --- CLIPBOARD ---
    @property
    def paste_delay(self) -> float:
        return get_config_value(self._config, 'CLIPBOARD', 'PASTE_DELAY', 0.3)

    # --- GEMINI ---
    @property
    def gemini_model(self) -> str:
        return get_config_value(self._config, 'GEMINI', 'MODEL', DEFAULT_GEMINI_MODEL)

    @property
    def gemini_language_codes(self) -> list[str]:
        """認識対象のBCP-47言語コード一覧。カンマ区切りで複数指定可"""
        raw = get_config_value(self._config, 'GEMINI', 'LANGUAGE_CODES', 'ja-JP')
        codes = [code.strip() for code in str(raw).split(',') if code.strip()]
        return codes if codes else ['ja-JP']

    @property
    def gemini_mode(self) -> str:
        """文字起こしモード。verbatim(発話どおり)かsmart(整形あり)"""
        raw = get_config_value(self._config, 'GEMINI', 'MODE', DEFAULT_GEMINI_MODE)
        mode = str(raw).strip().lower()
        if mode not in GEMINI_MODES:
            logging.warning(f'不正なmode設定のため{DEFAULT_GEMINI_MODE}を使用します: {raw}')
            return DEFAULT_GEMINI_MODE
        return mode

    @gemini_mode.setter
    def gemini_mode(self, value: str) -> None:
        mode = str(value).strip().lower()
        if mode not in GEMINI_MODES:
            raise ValueError(f'不正な文字起こしモードです: {value}')
        self._config['GEMINI']['MODE'] = mode

    @property
    def gemini_custom_vocabulary_file(self) -> str:
        """専門用語ファイル名。空文字なら無効"""
        configured = get_config_value(self._config, 'GEMINI', 'CUSTOM_VOCABULARY_FILE', '')
        if not configured:
            return ''
        if os.path.isabs(configured):
            return configured
        return os.path.join(self._default_data_dir(), configured)

    def _default_data_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            return getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))

    # --- FORMATTING ---
    @property
    def use_punctuation(self) -> bool:
        return get_config_value(self._config, 'FORMATTING', 'USE_PUNCTUATION', False)

    @use_punctuation.setter
    def use_punctuation(self, value: bool) -> None:
        self._config['FORMATTING']['USE_PUNCTUATION'] = str(value)

    @property
    def use_comma(self) -> bool:
        return get_config_value(self._config, 'FORMATTING', 'USE_COMMA', False)

    @use_comma.setter
    def use_comma(self, value: bool) -> None:
        self._config['FORMATTING']['USE_COMMA'] = str(value)

    # --- KEYS ---
    @property
    def toggle_recording_key(self) -> str:
        return get_config_value(self._config, 'KEYS', 'TOGGLE_RECORDING', 'pause')

    @property
    def exit_app_key(self) -> str:
        return get_config_value(self._config, 'KEYS', 'EXIT_APP', 'esc')

    @property
    def reload_audio_key(self) -> str:
        return get_config_value(self._config, 'KEYS', 'RELOAD_AUDIO', 'f8')

    @property
    def toggle_punctuation_key(self) -> str:
        return get_config_value(self._config, 'KEYS', 'TOGGLE_PUNCTUATION', 'f9')

    # --- RECORDING ---
    @property
    def auto_stop_timer(self) -> int:
        return get_config_value(self._config, 'RECORDING', 'AUTO_STOP_TIMER', 60)

    # --- WINDOW ---
    @property
    def window_width(self) -> int:
        return get_config_value(self._config, 'WINDOW', 'WIDTH', 300)

    @property
    def window_height(self) -> int:
        return get_config_value(self._config, 'WINDOW', 'HEIGHT', 450)

    # --- OPTIONS ---
    @property
    def start_minimized(self) -> bool:
        return get_config_value(self._config, 'OPTIONS', 'START_MINIMIZED', True)

    # --- EDITOR ---
    @property
    def editor_width(self) -> int:
        return get_config_value(self._config, 'EDITOR', 'WIDTH', 400)

    @property
    def editor_height(self) -> int:
        return get_config_value(self._config, 'EDITOR', 'HEIGHT', 700)

    @property
    def editor_font_name(self) -> str:
        return get_config_value(self._config, 'EDITOR', 'FONT_NAME', 'MS Gothic')

    @property
    def editor_font_size(self) -> int:
        return get_config_value(self._config, 'EDITOR', 'FONT_SIZE', 12)
