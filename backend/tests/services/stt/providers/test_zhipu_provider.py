"""
智谱 STT Provider 测试
"""

import io
import wave
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.stt.providers.zhipu_provider import ZhipuProvider


@pytest.mark.asyncio
async def test_zhipu_provider_init():
    """测试 ZhipuProvider 初始化"""
    with patch("app.services.stt.providers.zhipu_provider.settings") as mock_settings:
        mock_settings.ZHIPU_API_KEY = "test_key"
        mock_settings.ZHIPU_ASR_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
        mock_settings.ZHIPU_ASR_MODEL = "glm-asr-2512"
        mock_settings.ZHIPU_ASR_SAMPLE_RATE = 16000
        mock_settings.ZHIPU_ASR_STREAM_SEGMENT_SECONDS = 4
        mock_settings.ZHIPU_ASR_MAX_AUDIO_SECONDS = 30
        mock_settings.ZHIPU_ASR_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
        mock_settings.ZHIPU_ASR_REQUEST_TIMEOUT_SECONDS = 90

        provider = ZhipuProvider()
        assert provider.api_key == "test_key"
        assert provider.endpoint == "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"
        assert provider.model == "glm-asr-2512"


def test_zhipu_provider_build_wav_bytes():
    """测试 PCM 封装为 WAV"""
    with patch("app.services.stt.providers.zhipu_provider.settings") as mock_settings:
        mock_settings.ZHIPU_API_KEY = "test_key"
        mock_settings.ZHIPU_ASR_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
        mock_settings.ZHIPU_ASR_MODEL = "glm-asr-2512"
        mock_settings.ZHIPU_ASR_SAMPLE_RATE = 16000
        mock_settings.ZHIPU_ASR_STREAM_SEGMENT_SECONDS = 4
        mock_settings.ZHIPU_ASR_MAX_AUDIO_SECONDS = 30
        mock_settings.ZHIPU_ASR_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
        mock_settings.ZHIPU_ASR_REQUEST_TIMEOUT_SECONDS = 90

        provider = ZhipuProvider()
        wav_bytes = provider._build_wav_bytes(b"\x00\x01" * 320, 16000)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            assert wav_file.getframerate() == 16000
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2


@pytest.mark.asyncio
async def test_zhipu_provider_transcribe_audio_bytes_success():
    """测试智谱音频转写调用"""
    with patch("app.services.stt.providers.zhipu_provider.settings") as mock_settings:
        mock_settings.ZHIPU_API_KEY = "test_key"
        mock_settings.ZHIPU_ASR_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
        mock_settings.ZHIPU_ASR_MODEL = "glm-asr-2512"
        mock_settings.ZHIPU_ASR_SAMPLE_RATE = 16000
        mock_settings.ZHIPU_ASR_STREAM_SEGMENT_SECONDS = 4
        mock_settings.ZHIPU_ASR_MAX_AUDIO_SECONDS = 30
        mock_settings.ZHIPU_ASR_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
        mock_settings.ZHIPU_ASR_REQUEST_TIMEOUT_SECONDS = 90

        provider = ZhipuProvider()
        response = httpx.Response(200, json={"text": "测试转写"})
        post_mock = AsyncMock(return_value=response)

        with patch("httpx.AsyncClient.post", post_mock):
            text = await provider._transcribe_audio_bytes(
                audio_bytes=b"audio",
                filename="sample.wav",
                content_type="audio/wav",
            )

        assert text == "测试转写"
        assert post_mock.await_count == 1


@pytest.mark.asyncio
async def test_zhipu_provider_transcribe_stream_no_credentials():
    """测试 ZhipuProvider 流式转写缺少密钥"""
    with patch("app.services.stt.providers.zhipu_provider.settings") as mock_settings:
        mock_settings.ZHIPU_API_KEY = ""
        mock_settings.ZHIPU_ASR_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
        mock_settings.ZHIPU_ASR_MODEL = "glm-asr-2512"
        mock_settings.ZHIPU_ASR_SAMPLE_RATE = 16000
        mock_settings.ZHIPU_ASR_STREAM_SEGMENT_SECONDS = 4
        mock_settings.ZHIPU_ASR_MAX_AUDIO_SECONDS = 30
        mock_settings.ZHIPU_ASR_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
        mock_settings.ZHIPU_ASR_REQUEST_TIMEOUT_SECONDS = 90

        provider = ZhipuProvider()

        async def mock_audio_stream():
            yield b"audio_chunk_1"

        with pytest.raises(RuntimeError, match="API Key"):
            async for _ in provider.transcribe_stream(mock_audio_stream()):
                pass
