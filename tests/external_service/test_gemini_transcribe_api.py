import io
import wave
from typing import Optional, cast
from unittest.mock import MagicMock, patch

import pytest
from google import genai

from external_service.gemini_transcribe_api import (
    GeminiTranscribeClient,
    _build_prompt,
    _load_custom_vocabulary,
    _pcm_to_wav,
    setup_gemini_client,
    transcribe_audio,
    transcribe_pcm,
    validate_audio_file,
)
from tests.conftest import dict_to_app_config

BASE_CONFIG = {
    'GEMINI': {
        'MODEL': 'gemini-3.5-flash',
        'LANGUAGE_CODES': 'ja-JP',
        'MODE': 'verbatim',
        'CUSTOM_VOCABULARY_FILE': '',
    },
    'AUDIO': {'SAMPLE_RATE': 16000, 'CHANNELS': 1},
}

PCM_SAMPLE = b'\x00\x01' * 800


def make_client(
        model: str = 'gemini-3.5-flash',
        language_codes: tuple[str, ...] = ('ja-JP',),
        custom_vocabulary: tuple[str, ...] = (),
        mode: str = 'verbatim',
) -> tuple[GeminiTranscribeClient, MagicMock]:
    """クライアントと models.generate_content のモックを返す"""
    genai_client = MagicMock()
    client = GeminiTranscribeClient(
        genai_client=cast(genai.Client, genai_client),
        model=model,
        language_codes=language_codes,
        custom_vocabulary=custom_vocabulary,
        mode=mode,
    )
    return client, genai_client.models.generate_content


def set_output_text(create: MagicMock, text: Optional[str]) -> None:
    """generate_content の戻り値の text を差し替える"""
    response = MagicMock()
    response.text = text
    create.return_value = response


class TestSetupGeminiClient:

    @patch('external_service.gemini_transcribe_api.genai.Client')
    @patch('external_service.gemini_transcribe_api.load_env_variables')
    def test_setup_without_config(self, mock_load_env, mock_genai_client):
        """正常系: 設定未指定でもAPIキーがあればクライアントを生成する"""
        mock_load_env.return_value = {'GEMINI_API_KEY': 'test-key'}

        result = setup_gemini_client()

        mock_genai_client.assert_called_once_with(api_key='test-key')
        assert result.model == 'gemini-3.5-flash'
        assert result.mode == 'verbatim'
        assert result.custom_vocabulary == ()

    @patch('external_service.gemini_transcribe_api._load_custom_vocabulary')
    @patch('external_service.gemini_transcribe_api.genai.Client')
    @patch('external_service.gemini_transcribe_api.load_env_variables')
    def test_setup_with_config(self, mock_load_env, mock_genai_client, mock_load_vocab):
        """正常系: 設定からモデル・言語・モード・カスタム語彙を取り込む"""
        mock_load_env.return_value = {'GEMINI_API_KEY': 'test-key'}
        mock_load_vocab.return_value = ('心房細動',)
        config = dict_to_app_config({
            'GEMINI': {
                'MODEL': 'gemini-3.5-flash',
                'LANGUAGE_CODES': 'ja-JP, en-US',
                'MODE': 'smart',
                'CUSTOM_VOCABULARY_FILE': 'technical_terms.txt',
            }
        })

        result = setup_gemini_client(config)

        assert result.language_codes == ('ja-JP', 'en-US')
        assert result.mode == 'smart'
        assert result.custom_vocabulary == ('心房細動',)

    @patch('external_service.gemini_transcribe_api.load_env_variables')
    def test_missing_api_key_raises(self, mock_load_env):
        """異常系: APIキー未設定ならValueErrorを送出する"""
        mock_load_env.return_value = {}

        with pytest.raises(ValueError, match='GEMINI_API_KEY'):
            setup_gemini_client()

    @patch('external_service.gemini_transcribe_api.load_env_variables')
    def test_empty_api_key_raises(self, mock_load_env):
        """異常系: APIキーが空文字でもValueErrorを送出する"""
        mock_load_env.return_value = {'GEMINI_API_KEY': ''}

        with pytest.raises(ValueError, match='GEMINI_API_KEY'):
            setup_gemini_client()


class TestLoadCustomVocabulary:

    def test_empty_path_returns_empty(self):
        """正常系: パス未指定なら空タプルを返す"""
        assert _load_custom_vocabulary('') == ()

    def test_missing_file_returns_empty(self, tmp_path):
        """正常系: ファイルが存在しなければ空タプルを返す"""
        assert _load_custom_vocabulary(str(tmp_path / 'none.txt')) == ()

    def test_skips_blank_and_comment_lines(self, tmp_path):
        """正常系: 空行とコメント行を除外する"""
        path = tmp_path / 'terms.txt'
        path.write_text('心房細動\n\n# コメント\n  心不全  \n', encoding='utf-8')

        assert _load_custom_vocabulary(str(path)) == ('心房細動', '心不全')

    def test_excludes_legacy_class_tokens(self, tmp_path):
        """正常系: Chirp固有のクラストークンを除外する"""
        path = tmp_path / 'terms.txt'
        path.write_text(
            '$OOV_CLASS_DIGIT_SEQUENCE\n$PERCENT\n加齢黄斑変性\n', encoding='utf-8'
        )

        assert _load_custom_vocabulary(str(path)) == ('加齢黄斑変性',)

    def test_truncates_at_api_limit(self, tmp_path):
        """正常系: API上限の1000件を超えたら先頭1000件に切り詰める"""
        path = tmp_path / 'terms.txt'
        path.write_text('\n'.join(f'word{i}' for i in range(1200)), encoding='utf-8')

        result = _load_custom_vocabulary(str(path))

        assert len(result) == 1000
        assert result[0] == 'word0'
        assert result[-1] == 'word999'

    def test_read_error_returns_empty(self, tmp_path):
        """異常系: 読込エラー時は空タプルを返す"""
        path = tmp_path / 'terms.txt'
        path.write_text('心房細動', encoding='utf-8')

        with patch('builtins.open', side_effect=OSError('読込失敗')):
            assert _load_custom_vocabulary(str(path)) == ()


class TestBuildPrompt:

    def test_verbatim_omits_empty_fields(self):
        """正常系: 言語・語彙が空なら該当行を含めない"""
        client, _ = make_client(language_codes=(), custom_vocabulary=())

        prompt = _build_prompt(client)

        assert '一字一句' in prompt
        assert '音声の言語' not in prompt
        assert '次の用語' not in prompt

    def test_smart_includes_all_fields(self):
        """正常系: smartモードで言語とカスタム語彙を指示文に含める"""
        client, _ = make_client(
            language_codes=('ja-JP', 'en-US'), custom_vocabulary=('心房細動',), mode='smart'
        )

        prompt = _build_prompt(client)

        assert '読みやすく整えて' in prompt
        assert '音声の言語: ja-JP, en-US' in prompt
        assert '心房細動' in prompt

    def test_unknown_mode_falls_back_to_verbatim(self):
        """異常系: 未知のモードはverbatimの指示文を使う"""
        client, _ = make_client(mode='unknown')

        assert '一字一句' in _build_prompt(client)


class TestPcmToWav:

    def test_wraps_pcm_in_wav_container(self):
        """正常系: 生PCMをWAVコンテナに包みヘッダ情報を保持する"""
        wav_bytes = _pcm_to_wav(PCM_SAMPLE, 16000, 1)

        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.readframes(wf.getnframes()) == PCM_SAMPLE


class TestValidateAudioFile:

    def test_empty_path(self):
        """異常系: パス未指定はエラーメッセージを返す"""
        is_valid, error = validate_audio_file('')
        assert is_valid is False
        assert '未指定' in str(error)

    def test_missing_file(self, tmp_path):
        """異常系: 存在しないファイルはエラーメッセージを返す"""
        is_valid, error = validate_audio_file(str(tmp_path / 'none.wav'))
        assert is_valid is False
        assert '存在しません' in str(error)

    def test_zero_size_file(self, tmp_path):
        """異常系: 0バイトのファイルはエラーメッセージを返す"""
        path = tmp_path / 'empty.wav'
        path.write_bytes(b'')

        is_valid, error = validate_audio_file(str(path))
        assert is_valid is False
        assert '0バイト' in str(error)

    def test_valid_file(self, tmp_path):
        """正常系: 実体のあるファイルは検証を通過する"""
        path = tmp_path / 'ok.wav'
        path.write_bytes(b'data')

        assert validate_audio_file(str(path)) == (True, None)


class TestTranscribePcm:

    def test_empty_audio_returns_none(self):
        """異常系: 音声データが空ならNoneを返す"""
        config = dict_to_app_config(BASE_CONFIG)
        client, _ = make_client()

        assert transcribe_pcm(b'', 16000, config, client) is None

    def test_sends_wav_with_prompt(self):
        """正常系: WAVに変換し指示文付きで送信する"""
        config = dict_to_app_config(BASE_CONFIG)
        client, create = make_client(custom_vocabulary=('心房細動',))
        set_output_text(create, 'おはようございます')

        result = transcribe_pcm(PCM_SAMPLE, 16000, config, client, 1)

        assert result == 'おはようございます'
        kwargs = create.call_args.kwargs
        assert kwargs['model'] == 'gemini-3.5-flash'
        audio, prompt = kwargs['contents']
        assert audio.inline_data is not None
        assert audio.inline_data.mime_type == 'audio/wav'
        assert (audio.inline_data.data or b'').startswith(b'RIFF')
        assert '心房細動' in prompt

    def test_empty_output_text_returns_empty_string(self):
        """正常系: 結果が空文字ならそのまま空文字を返す"""
        config = dict_to_app_config(BASE_CONFIG)
        client, create = make_client()
        set_output_text(create, '')

        assert transcribe_pcm(PCM_SAMPLE, 16000, config, client) == ''

    def test_none_output_text_returns_empty_string(self):
        """正常系: output_textがNoneでも空文字として扱う"""
        config = dict_to_app_config(BASE_CONFIG)
        client, create = make_client()
        set_output_text(create, None)

        assert transcribe_pcm(PCM_SAMPLE, 16000, config, client) == ''

    def test_api_error_returns_none(self):
        """異常系: API例外時はNoneを返す"""
        config = dict_to_app_config(BASE_CONFIG)
        client, create = make_client()
        create.side_effect = RuntimeError('API失敗')

        assert transcribe_pcm(PCM_SAMPLE, 16000, config, client) is None


class TestTranscribeAudio:

    def _write_wav(self, path) -> None:
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(PCM_SAMPLE)

    def test_invalid_file_returns_none(self, tmp_path):
        """異常系: 検証に失敗したファイルはNoneを返す"""
        config = dict_to_app_config(BASE_CONFIG)
        client, _ = make_client()

        assert transcribe_audio(str(tmp_path / 'none.wav'), config, client) is None

    def test_transcribes_saved_file(self, tmp_path):
        """正常系: 保存済みWAVを読み込んで文字起こしする"""
        path = tmp_path / 'audio.wav'
        self._write_wav(path)
        config = dict_to_app_config(BASE_CONFIG)
        client, create = make_client()
        set_output_text(create, 'テストです')

        assert transcribe_audio(str(path), config, client) == 'テストです'

    def test_broken_wav_returns_none(self, tmp_path):
        """異常系: WAVとして読めないファイルはNoneを返す"""
        path = tmp_path / 'broken.wav'
        path.write_bytes(b'not a wav file')
        config = dict_to_app_config(BASE_CONFIG)
        client, _ = make_client()

        assert transcribe_audio(str(path), config, client) is None
