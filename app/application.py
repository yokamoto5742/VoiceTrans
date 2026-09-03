import logging
import tkinter as tk

from app import __version__
from app.main_window import VoiceInputManager
from app.notification_manager import NotificationManager
from app.ui_queue_processor import UIQueueProcessor
from external_service.gemini_transcribe_api import setup_gemini_client
from service.audio_file_manager import AudioFileManager
from service.audio_recorder import AudioRecorder
from service.clipboard_manager import ClipboardManager
from service.recording_lifecycle import RecordingLifecycle
from service.text_transformer import load_replacements
from service.transcription_handler import TranscriptionHandler
from utils.app_config import AppConfig
from utils.config_manager import load_config
from utils.log_rotation import setup_debug_logging, setup_logging


class Application:
    def __init__(self) -> None:
        self._voice_manager: VoiceInputManager | None = None

    def run(self) -> None:
        raw_config = load_config()
        config = AppConfig(raw_config)
        setup_logging(config.raw_config)
        setup_debug_logging(config.raw_config)

        logging.info('アプリケーションを開始します')

        recorder = AudioRecorder(config)
        client = setup_gemini_client(config)
        logging.info('Gemini Transcribe APIクライアントを初期化しました')

        replacements = load_replacements(config.replacements_file)
        clipboard_manager = ClipboardManager(config)
        clipboard_manager.initialize()

        audio_file_manager = AudioFileManager(config)

        root = tk.Tk()
        ui_processor = UIQueueProcessor(root)
        ui_processor.start()

        notification_manager = NotificationManager(root, config)

        transcription_handler = TranscriptionHandler(
            config, client, audio_file_manager, ui_processor,
            config.use_punctuation, replacements
        )

        recording_lifecycle = RecordingLifecycle(
            root, config, recorder, audio_file_manager,
            transcription_handler, clipboard_manager,
            ui_processor, notification_manager.show_timed_message
        )

        self._voice_manager = VoiceInputManager(
            root, config, recording_lifecycle, notification_manager, __version__
        )

        root.protocol('WM_DELETE_WINDOW', self.close)
        root.mainloop()

    def close(self) -> None:
        if self._voice_manager:
            self._voice_manager.close_application()
