import logging
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional

from app.ui_queue_processor import UIQueueProcessor
from external_service.gemini_transcribe_api import transcribe_audio, transcribe_pcm
from service.audio_file_manager import AudioFileManager
from service.text_transformer import (
    load_replacements,
    process_punctuation,
    remove_ja_spaces,
    replace_text,
)
from utils.app_config import AppConfig


class TranscriptionHandler:

    def __init__(
            self,
            config: AppConfig,
            client: Any,
            audio_file_manager: AudioFileManager,
            ui_processor: UIQueueProcessor,
            use_punctuation: bool,
            replacements: Dict[str, str]
    ):
        self.config = config
        self.client = client
        self.audio_file_manager = audio_file_manager
        self.ui_processor = ui_processor
        self.use_punctuation = use_punctuation
        self.replacements = replacements

        self.cancel_processing = False
        self.processing_thread: Optional[threading.Thread] = None
        self.transcribe_audio_func = transcribe_audio
        self.transcribe_pcm_func = transcribe_pcm

    def transcribe_frames(
            self,
            frames: List[bytes],
            sample_rate: int,
            on_complete: Callable[[str], None],
            on_error: Callable[[str], None]
    ) -> None:
        """音声フレームを文字起こし処理"""
        try:
            logging.info('音声フレーム処理開始')

            if self.cancel_processing:
                logging.info('処理がキャンセルされました')
                return

            pcm_bytes = b''.join(frames)

            # 保存はアーカイブ用途。API呼び出しを待たせないため別スレッドで実行する
            threading.Thread(
                target=self.audio_file_manager.save_audio,
                args=(frames, sample_rate),
                daemon=True,
                name='SaveAudio-Thread'
            ).start()

            logging.info('文字起こし開始')
            transcription = self.transcribe_pcm_func(
                pcm_bytes,
                sample_rate,
                self.config,
                self.client,
                self.config.audio_channels,
            )

            if not transcription:
                raise ValueError('音声ファイルの文字起こしに失敗しました')

            logging.debug(f'テキスト整形開始: use_punctuation={self.use_punctuation}')
            transcription = self.transform_text(transcription)
            logging.debug('テキスト整形完了')

            if self.cancel_processing:
                logging.info('処理がキャンセルされました')
                return

            logging.debug('UI更新をスケジュール')
            self.ui_processor.schedule_callback(on_complete, transcription)
            logging.debug('UI更新スケジュール完了')

        except Exception as e:
            logging.error(f'文字起こし処理中にエラー: {str(e)}')
            logging.debug(f'詳細: {traceback.format_exc()}')
            self.ui_processor.schedule_callback(on_error, str(e))

    def handle_audio_file(
            self,
            file_path: str,
            on_complete: Callable[[str], None],
            on_error: Callable[[str], None]
    ) -> None:
        """保存した音声ファイルを文字起こしする"""
        try:
            transcription = self.transcribe_audio_func(
                file_path,
                self.config,
                self.client
            )
            if transcription:
                transcription = self.transform_text(transcription)
                on_complete(transcription)
            else:
                raise ValueError('音声ファイルの処理に失敗しました')
        except Exception as e:
            on_error(str(e))

    def transform_text(self, text: str) -> str:
        """空白除去→置換→句読点処理の順にテキストを整形する

        句読点処理を最後に置くことで、置換ルール（例: '？'→'。'）が
        句読点なし設定を打ち消さないようにする
        """
        replaced = replace_text(remove_ja_spaces(text), self.replacements)
        return process_punctuation(replaced, self.use_punctuation)

    def reload_replacements(self) -> None:
        """置換辞書ファイルを再読み込みする"""
        self.replacements = load_replacements(self.config.replacements_file)

    def set_transcription_mode(self, mode: str) -> None:
        """APIクライアントの文字起こしモードを切り替える"""
        self.client.mode = mode

    def wait_for_processing(self, timeout: float = 5.0) -> bool:
        """処理スレッドの完了を待機する"""
        if self.processing_thread and self.processing_thread.is_alive():
            logging.info('処理スレッドの完了を待機中...')
            self.processing_thread.join(timeout=timeout)
            return not self.processing_thread.is_alive()
        return True

    def cancel(self) -> None:
        """処理をキャンセルする"""
        self.cancel_processing = True

    def reset_cancel(self) -> None:
        """キャンセルフラグをリセットする"""
        self.cancel_processing = False
