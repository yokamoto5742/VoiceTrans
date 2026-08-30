import io
import logging
import os
import traceback
import wave
from dataclasses import dataclass, field
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from utils.app_config import AppConfig
from utils.env_loader import load_env_variables

# 録音は pyaudio.paInt16 固定のため 16bit = 2バイト
SAMPLE_WIDTH_BYTES = 2
# カスタム語彙の上限。推奨は100語程度
MAX_CUSTOM_VOCABULARY = 1000
RECOMMENDED_CUSTOM_VOCABULARY = 100

# 文字起こし精度を安定させるため生成のばらつきを抑える
TEMPERATURE = 0.0
# 書き起こしに推論は不要。レイテンシを最小化する
THINKING_LEVEL = types.ThinkingLevel.MINIMAL

MODE_INSTRUCTIONS = {
    'verbatim': '音声を一字一句そのまま書き起こしてください。フィラーや言い直しも省略しないでください。',
    'smart': '音声を書き起こし、意味を変えずに読みやすく整えてください。フィラーや言い直しは削除してください。',
}
COMMON_INSTRUCTIONS = (
    '書き起こしたテキストのみを出力し、前置き・説明・引用符・装飾は一切付けないでください。'
    '単語間に不要な空白を入れないでください。'
)


@dataclass
class GeminiTranscribeClient:
    genai_client: genai.Client
    model: str
    language_codes: tuple[str, ...] = field(default_factory=tuple)
    custom_vocabulary: tuple[str, ...] = field(default_factory=tuple)
    mode: str = 'verbatim'


def _load_custom_vocabulary(file_path: str) -> tuple[str, ...]:
    """専門用語ファイルを読み込みカスタム語彙として返す"""
    if not file_path or not os.path.exists(file_path):
        return ()
    try:
        with open(file_path, encoding='utf-8') as f:
            lines = [
                line.strip()
                for line in f
                if line.strip() and not line.lstrip().startswith('#')
            ]
    except OSError as e:
        logging.error(f'専門用語ファイル読込エラー: {e}')
        return ()

    # $OOV_CLASS_DIGIT_SEQUENCE などはChirp固有のクラストークン。
    # Geminiではリテラル文字列として扱われ認識精度を下げるため除外する
    words = [word for word in lines if not word.startswith('$')]
    if len(words) < len(lines):
        logging.info(f'旧STT用クラストークンを除外しました: {len(lines) - len(words)}件')

    if len(words) > MAX_CUSTOM_VOCABULARY:
        logging.warning(
            f'カスタム語彙がAPI上限を超えたため先頭{MAX_CUSTOM_VOCABULARY}件のみ使用します'
            f' (登録{len(words)}件)'
        )
        words = words[:MAX_CUSTOM_VOCABULARY]
    elif len(words) > RECOMMENDED_CUSTOM_VOCABULARY:
        logging.info(
            f'カスタム語彙が推奨件数を超えています: {len(words)}件'
            f' (推奨{RECOMMENDED_CUSTOM_VOCABULARY}件以下)'
        )

    logging.info(f'カスタム語彙読込: {len(words)}件 ({file_path})')
    return tuple(words)


def setup_gemini_client(config: Optional[AppConfig] = None) -> GeminiTranscribeClient:
    env_vars = load_env_variables()

    api_key = env_vars.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError('GEMINI_API_KEYが未設定です')

    genai_client = genai.Client(api_key=api_key)

    if config is None:
        return GeminiTranscribeClient(genai_client=genai_client, model='gemini-3.5-flash')

    return GeminiTranscribeClient(
        genai_client=genai_client,
        model=config.gemini_model,
        language_codes=tuple(config.gemini_language_codes),
        custom_vocabulary=_load_custom_vocabulary(config.gemini_custom_vocabulary_file),
        mode=config.gemini_mode,
    )


def validate_audio_file(file_path: str) -> tuple[bool, Optional[str]]:
    if not file_path:
        return False, '音声ファイルパスが未指定です'

    if not os.path.exists(file_path):
        return False, f'音声ファイルが存在しません: {file_path}'

    if os.path.getsize(file_path) == 0:
        return False, '音声ファイルサイズが0バイトです'

    return True, None


def _build_prompt(client: GeminiTranscribeClient) -> str:
    """モード・言語・カスタム語彙から文字起こし指示文を組み立てる"""
    lines = [MODE_INSTRUCTIONS.get(client.mode, MODE_INSTRUCTIONS['verbatim'])]
    if client.language_codes:
        lines.append(f'音声の言語: {", ".join(client.language_codes)}')
    if client.custom_vocabulary:
        lines.append(
            f'次の用語が現れた場合はこの表記を使ってください: {", ".join(client.custom_vocabulary)}'
        )
    lines.append(COMMON_INSTRUCTIONS)
    return '\n'.join(lines)


def _pcm_to_wav(audio_bytes: bytes, sample_rate: int, channels: int) -> bytes:
    """生PCMをメモリ上でWAVコンテナに包む。APIはaudio/l16を受け付けないため必須"""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH_BYTES)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)
    return buffer.getvalue()


def _transcribe_wav(wav_bytes: bytes, client: GeminiTranscribeClient) -> Optional[str]:
    """WAVバイト列をインライン送信して文字起こしする"""
    try:
        logging.info(f'文字起こしリクエスト送信: {len(wav_bytes)} bytes (mode={client.mode})')
        response = client.genai_client.models.generate_content(
            model=client.model,
            contents=[
                types.Part.from_bytes(data=wav_bytes, mime_type='audio/wav'),
                _build_prompt(client),
            ],
            config=types.GenerateContentConfig(
                temperature=TEMPERATURE,
                thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
            ),
        )

        text_result = (response.text or '').strip()

        if len(text_result) == 0:
            logging.warning('文字起こし結果が空です')
            return ''

        logging.info(f'文字起こし完了: {len(text_result)}文字')
        return text_result

    except genai_errors.APIError as e:
        logging.error(f'Gemini APIエラー: {str(e)}')
        logging.debug(f'詳細: {traceback.format_exc()}')
        return None
    except Exception as e:
        logging.error(f'文字起こしエラー: {str(e)}')
        logging.error(f'エラーのタイプ: {type(e).__name__}')
        logging.debug(f'詳細: {traceback.format_exc()}')
        return None


def transcribe_pcm(
        audio_bytes: bytes,
        sample_rate: int,
        config: AppConfig,
        client: GeminiTranscribeClient,
        channels: int = 1,
) -> Optional[str]:
    """PCM(LINEAR16)のバイト列を文字起こしする"""
    if not audio_bytes:
        logging.warning('音声データが空です')
        return None

    try:
        wav_bytes = _pcm_to_wav(audio_bytes, sample_rate, channels)
    except (OSError, wave.Error) as e:
        logging.error(f'WAV変換エラー: {str(e)}')
        return None

    return _transcribe_wav(wav_bytes, client)


def _read_pcm_from_wav(file_path: str) -> tuple[bytes, int, int]:
    with wave.open(file_path, 'rb') as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        pcm = wf.readframes(wf.getnframes())
    return pcm, sample_rate, channels


def transcribe_audio(
        audio_file_path: str,
        config: AppConfig,
        client: GeminiTranscribeClient
) -> Optional[str]:
    """保存済み音声ファイルを読み込んで文字起こしする"""
    is_valid, error_msg = validate_audio_file(audio_file_path)
    if not is_valid:
        logging.warning(error_msg) if '未指定' in str(error_msg) else logging.error(error_msg)
        return None

    try:
        pcm, sample_rate, channels = _read_pcm_from_wav(audio_file_path)
        logging.info(f'ファイル読み込み完了: {len(pcm)} bytes, {sample_rate}Hz, {channels}ch')
    except FileNotFoundError as e:
        logging.error(f'ファイルが見つかりません: {str(e)}')
        return None
    except PermissionError as e:
        logging.error(f'ファイルアクセス権限エラー: {str(e)}')
        return None
    except (OSError, wave.Error) as e:
        logging.error(f'音声ファイル読込エラー: {str(e)}')
        return None

    return transcribe_pcm(pcm, sample_rate, config, client, channels)
