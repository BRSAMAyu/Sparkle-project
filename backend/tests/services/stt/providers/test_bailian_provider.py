"""
百炼（Qwen3-ASR-Flash-Realtime）STT Provider 测试。

通过 mock WebSocket 层验证请求形态（session.update / append / commit / finish）
与响应解析（conversation.item.input_audio_transcription.completed / error）。
"""

import asyncio
import base64
import io
import json
import wave
from unittest.mock import Mock, patch

import pytest
import websockets

from app.services.stt.providers.bailian_provider import BailianProvider


def _provider_settings_mock():
    mock = Mock()
    mock.DASHSCOPE_API_KEY = "test-dashscope-key"
    mock.QWEN_ASR_WS_URL = "wss://asr.example.invalid/api-ws/v1/realtime"
    mock.QWEN_ASR_MODEL = "qwen3-asr-flash-realtime"
    mock.QWEN_ASR_SAMPLE_RATE = 16000
    mock.QWEN_ASR_STREAM_SEGMENT_SECONDS = 1
    mock.QWEN_ASR_MAX_AUDIO_SECONDS = 60
    mock.QWEN_ASR_REQUEST_TIMEOUT_SECONDS = 5
    mock.QWEN_ASR_LANGUAGE = "zh"
    return mock


class FakeBailianWebSocket:
    """按脚本回放服务端事件的假 WebSocket。"""

    def __init__(self, script):
        self.script = list(script)
        self.sent = []
        self.connect_kwargs = None

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    async def recv(self):
        if not self.script:
            raise websockets.ConnectionClosed(None, None)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        await asyncio.sleep(0)
        return json.dumps(item) if isinstance(item, dict) else item

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def _completed(transcript: str) -> dict:
    return {"type": "conversation.item.input_audio_transcription.completed", "transcript": transcript}


def _make_provider(**overrides) -> tuple[BailianProvider, Mock]:
    settings_mock = _provider_settings_mock()
    for key, value in overrides.items():
        setattr(settings_mock, key, value)
    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        provider = BailianProvider()
    return provider, settings_mock


def _wav_bytes(duration_seconds: float = 0.2, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * int(rate * duration_seconds))
    return buffer.getvalue()


async def test_transcribe_segment_request_shape_and_parsing():
    """单段转写：验证 WS URL/头/session.update/append/commit/finish 与文本解析。"""
    provider, settings_mock = _make_provider()
    fake_ws = FakeBailianWebSocket(
        [
            {"type": "session.created"},
            _completed("你好我在测试语音识别"),
        ]
    )
    connect_mock = Mock(return_value=fake_ws)

    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        with patch("app.services.stt.providers.bailian_provider.websockets.connect", connect_mock):
            text = await provider._transcribe_pcm_segment(b"\x01\x00" * 1600, "zh-CN")

    assert text == "你好我在测试语音识别"

    # 连接形态：realtime 端点 + 模型 query + 鉴权头
    url = connect_mock.call_args.args[0]
    assert url == "wss://asr.example.invalid/api-ws/v1/realtime?model=qwen3-asr-flash-realtime"
    headers = connect_mock.call_args.kwargs["additional_headers"]
    assert headers["Authorization"] == "Bearer test-dashscope-key"
    assert headers["OpenAI-Beta"] == "realtime=v1"

    # 事件序列：session.update → append*N → commit → finish
    types = [event["type"] for event in fake_ws.sent]
    assert types[0] == "session.update"
    assert types[-1] == "session.finish"
    assert types[-2] == "input_audio_buffer.commit"
    assert set(types[1:-2]) == {"input_audio_buffer.append"}

    session = fake_ws.sent[0]["session"]
    assert session["modalities"] == ["text"]
    assert session["input_audio_format"] == "pcm"
    assert session["sample_rate"] == 16000
    assert session["turn_detection"] is None  # manual commit 模式
    assert session["input_audio_transcription"] == {"language": "zh"}

    appended = b"".join(
        base64.b64decode(event["audio"]) for event in fake_ws.sent if event["type"] == "input_audio_buffer.append"
    )
    assert appended == b"\x01\x00" * 1600


async def test_transcribe_segment_error_event_raises():
    provider, settings_mock = _make_provider()
    fake_ws = FakeBailianWebSocket([{"type": "error", "error": {"code": "InvalidParameter", "message": "bad audio"}}])
    connect_mock = Mock(return_value=fake_ws)

    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        with patch("app.services.stt.providers.bailian_provider.websockets.connect", connect_mock):
            with pytest.raises(RuntimeError, match="bad audio"):
                await provider._transcribe_pcm_segment(b"\x00\x00" * 100)


async def test_transcribe_stream_yields_incremental_segments():
    """流式：按 QWEN_ASR_STREAM_SEGMENT_SECONDS 分段、去重增量返回。"""
    provider, settings_mock = _make_provider()
    segment_bytes = provider.sample_rate * 2 * provider.stream_segment_seconds
    tail_bytes = 100
    transcripts = iter(["第一段", "第二段"])

    async def fake_segment(pcm_bytes, language, sample_rate=None):
        del language, sample_rate
        assert len(pcm_bytes) in (segment_bytes, tail_bytes)  # 整段 + 流结束尾段
        return next(transcripts)

    async def audio_stream():
        yield b"\x00\x00" * (segment_bytes // 4)
        yield b"\x00\x00" * (segment_bytes // 4)
        yield b"\x00\x00" * (tail_bytes // 2)  # 不足一段的尾巴

    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        with patch.object(BailianProvider, "_transcribe_pcm_segment", side_effect=fake_segment):
            texts = [text async for text in provider.transcribe_stream(audio_stream())]

    assert texts == ["第一段", "第二段"]


async def test_transcribe_file_wav():
    provider, settings_mock = _make_provider()
    fake_ws = FakeBailianWebSocket([_completed("这是文件转写结果")])
    connect_mock = Mock(return_value=fake_ws)

    wav_path = "/tmp/fake_bailian_test_16k.wav"
    with open(wav_path, "wb") as f:
        f.write(_wav_bytes(duration_seconds=0.2, rate=16000))

    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        with patch("app.services.stt.providers.bailian_provider.websockets.connect", connect_mock):
            text = await provider.transcribe_file(wav_path)

    assert text == "这是文件转写结果"
    assert "input_audio_buffer.commit" in [event["type"] for event in fake_ws.sent]


async def test_transcribe_file_wav_non_16k_keeps_native_sample_rate():
    """非 16k wav 文件按真实采样率声明会话参数，不做重采样。"""
    provider, settings_mock = _make_provider()
    fake_ws = FakeBailianWebSocket([_completed("结果")])
    connect_mock = Mock(return_value=fake_ws)

    wav_path = "/tmp/fake_bailian_test_24k.wav"
    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        buffer = io.BytesIO(_wav_bytes(duration_seconds=0.1, rate=24000))
        with open(wav_path, "wb") as f:
            f.write(buffer.getvalue())
        with patch("app.services.stt.providers.bailian_provider.websockets.connect", connect_mock):
            text = await provider.transcribe_file(wav_path)

    assert text == "结果"
    session_update = fake_ws.sent[0]["session"]
    assert session_update["sample_rate"] == 24000


async def test_transcribe_file_missing_raises():
    provider, settings_mock = _make_provider()
    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        with pytest.raises(RuntimeError, match="文件不存在"):
            await provider.transcribe_file("/nonexistent/audio.wav")


async def test_missing_api_key_raises():
    provider, settings_mock = _make_provider(DASHSCOPE_API_KEY="")
    with patch("app.services.stt.providers.bailian_provider.settings", settings_mock):
        with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
            await provider.transcribe_file("/tmp/whatever.wav")
