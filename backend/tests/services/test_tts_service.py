"""
百炼 TTS（qwen3-tts-instruct-flash）服务测试。

通过 mock HTTP 层验证请求形态（multimodal-generation 端点、model/input 字段）
与响应解析（output.audio.data base64 / output.audio.url 下载、音频 magic 校验）。
"""

import base64
import io
import wave
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.services.tts_service import BailianTTSProvider, TTSProviderError, TTSService


def _settings_mock():
    mock = Mock()
    mock.DASHSCOPE_API_KEY = "test-dashscope-key"
    mock.DASHSCOPE_BASE_HTTP_API_URL = "https://dashscope.example.invalid/api/v1"
    mock.TTS_PROVIDER = "bailian"
    mock.QWEN_TTS_MODEL = "qwen3-tts-instruct-flash"
    mock.QWEN_TTS_VOICE = "Cherry"
    mock.QWEN_TTS_AUDIO_FORMAT = "wav"
    mock.QWEN_TTS_REQUEST_TIMEOUT_SECONDS = 30
    return mock


def _real_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(b"\x00\x00" * 2400)  # 0.1s @24kHz
    return buffer.getvalue()


class FakeAsyncClient:
    def __init__(self, post_response=None, get_response=None):
        self.post = AsyncMock(return_value=post_response)
        self.get = AsyncMock(return_value=get_response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def _json_response(payload: dict, status_code: int = 200) -> Mock:
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = payload
    if status_code >= 400:
        response.text = str(payload)
    return response


def _provider() -> tuple[BailianTTSProvider, Mock]:
    settings_mock = _settings_mock()
    with patch("app.services.tts_service.settings", settings_mock):
        provider = BailianTTSProvider()
    return provider, settings_mock


async def test_synthesize_request_shape_and_base64_data_path():
    """请求形态 + output.audio.data(base64) 解析。"""
    provider, settings_mock = _provider()
    wav = _real_wav_bytes()
    payload = {
        "output": {"audio": {"data": base64.b64encode(wav).decode("utf-8"), "expires_at": 123}},
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    client = FakeAsyncClient(post_response=_json_response(payload))

    with patch("app.services.tts_service.settings", settings_mock):
        with patch("app.services.tts_service.httpx.AsyncClient", return_value=client):
            audio = await provider.synthesize("你好，正在测试语音合成", instructions="用平静的语气说")

    assert audio == wav

    endpoint = client.post.call_args.args[0]
    assert endpoint == "https://dashscope.example.invalid/api/v1/services/aigc/multimodal-generation/generation"
    headers = client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-dashscope-key"
    body = client.post.call_args.kwargs["json"]
    assert body["model"] == "qwen3-tts-instruct-flash"
    assert body["input"]["text"] == "你好，正在测试语音合成"
    assert body["input"]["voice"] == "Cherry"  # 默认音色
    assert body["input"]["instructions"] == "用平静的语气说"


async def test_synthesize_url_download_path():
    """output.audio.url → 二次 GET 下载音频。"""
    provider, settings_mock = _provider()
    wav = _real_wav_bytes()
    payload = {"output": {"audio": {"url": "https://cdn.example.invalid/tts/audio.wav"}}}
    client = FakeAsyncClient(
        post_response=_json_response(payload),
        get_response=Mock(spec=httpx.Response, status_code=200, content=wav),
    )

    with patch("app.services.tts_service.settings", settings_mock):
        with patch("app.services.tts_service.httpx.AsyncClient", return_value=client):
            audio = await provider.synthesize("测试")

    assert audio == wav
    assert client.get.call_args.args[0] == "https://cdn.example.invalid/tts/audio.wav"


async def test_synthesize_http_error_raises():
    provider, settings_mock = _provider()
    client = FakeAsyncClient(post_response=_json_response({"error": {"code": "Throttling", "message": "限流"}}, 429))

    with patch("app.services.tts_service.settings", settings_mock):
        with patch("app.services.tts_service.httpx.AsyncClient", return_value=client):
            with pytest.raises(TTSProviderError, match="限流"):
                await provider.synthesize("测试")


async def test_synthesize_invalid_audio_magic_raises():
    """返回内容不是 RIFF/mp3 时应报错而非静默透传。"""
    provider, settings_mock = _provider()
    payload = {"output": {"audio": {"data": base64.b64encode(b"not-audio-at-all!!").decode()}}}
    client = FakeAsyncClient(post_response=_json_response(payload))

    with patch("app.services.tts_service.settings", settings_mock):
        with patch("app.services.tts_service.httpx.AsyncClient", return_value=client):
            with pytest.raises(TTSProviderError, match="有效音频"):
                await provider.synthesize("测试")


async def test_synthesize_empty_text_raises():
    provider, settings_mock = _provider()
    with patch("app.services.tts_service.settings", settings_mock):
        with pytest.raises(TTSProviderError, match="文本不能为空"):
            await provider.synthesize("  ")


async def test_tts_service_wraps_result_and_unavailable_provider():
    settings_mock = _settings_mock()

    with patch("app.services.tts_service.settings", settings_mock):
        service = TTSService()
        # 正常路径
        with patch.object(BailianTTSProvider, "synthesize", AsyncMock(return_value=b"RIFF____WAVE")):
            result = await service.synthesize("你好")
        assert result["audio"] == b"RIFF____WAVE"
        assert result["error"] is None
        assert result["format"] == "wav"

        # 失败路径
        with patch.object(
            BailianTTSProvider,
            "synthesize",
            AsyncMock(side_effect=TTSProviderError("百炼 TTS 请求失败: 限流")),
        ):
            result = await service.synthesize("你好")
        assert result["audio"] == b""
        assert "限流" in str(result["error"])

    # Provider 未初始化路径
    with patch("app.services.tts_service.settings", settings_mock):
        with patch.object(service, "provider", None):
            result = await service.synthesize("你好")
        assert "Provider Not Initialized" in str(result["error"])
