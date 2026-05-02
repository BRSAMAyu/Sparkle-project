"""
科大讯飞 STT Provider 测试
"""

import asyncio
import json
import os
import tempfile
import wave
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.stt.providers.xunfei_provider import XunFeiProvider


def _mock_xunfei_payload(text: str, status: int) -> str:
    return json.dumps(
        {
            "code": 0,
            "data": {
                "status": status,
                "result": {
                    "ws": [
                        {
                            "cw": [
                                {
                                    "w": text,
                                }
                            ]
                        }
                    ]
                },
            },
        },
        ensure_ascii=False,
    )


def _build_temp_wav() -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        with wave.open(handle, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x01" * 1600)
        return handle.name


def _patch_settings():
    return patch("app.services.stt.providers.xunfei_provider.settings")


@pytest.mark.asyncio
async def test_xunfei_provider_drain_messages_collects_segments_and_terminal_status():
    """测试讯飞回包解析会提取文本并识别终态"""
    with _patch_settings() as mock_settings:
        mock_settings.XUNFEI_APP_ID = "app-id"
        mock_settings.XUNFEI_API_KEY = "test-xunfei-api-key"
        mock_settings.XUNFEI_API_SECRET = "test-xunfei-api-secret"
        mock_settings.XUNFEI_STT_DOMAIN = "iat"
        mock_settings.XUNFEI_STT_LANGUAGE = "zh-CN"
        mock_settings.XUNFEI_STT_SAMPLE_RATE = 16000
        mock_settings.XUNFEI_STT_EOS_MS = 6000

        provider = XunFeiProvider()
        websocket = Mock()
        websocket.recv = AsyncMock(
            side_effect=[
                _mock_xunfei_payload("你好", 1),
                _mock_xunfei_payload("你好世界", 2),
            ]
        )

        last_text, texts, terminal = await provider._drain_messages(websocket, "", timeout=0.1)

        assert last_text == "你好世界"
        assert texts == ["你好", "你好世界"]
        assert terminal is True


@pytest.mark.asyncio
async def test_xunfei_provider_transcribe_file_timeout_returns_error_text():
    """测试文件转写超时会返回可识别的错误文本"""
    with _patch_settings() as mock_settings:
        mock_settings.XUNFEI_APP_ID = "app-id"
        mock_settings.XUNFEI_API_KEY = "test-xunfei-api-key"
        mock_settings.XUNFEI_API_SECRET = "test-xunfei-api-secret"
        mock_settings.XUNFEI_STT_DOMAIN = "iat"
        mock_settings.XUNFEI_STT_LANGUAGE = "zh-CN"
        mock_settings.XUNFEI_STT_SAMPLE_RATE = 16000
        mock_settings.XUNFEI_STT_EOS_MS = 6000

        provider = XunFeiProvider()
        wav_path = _build_temp_wav()

        async def slow_stream(*args, **kwargs):
            del args, kwargs
            await asyncio.sleep(1)
            if False:
                yield ""

        provider.transcribe_stream = slow_stream

        async def timeout_wait_for(awaitable, timeout):
            del timeout
            awaitable.close()
            raise asyncio.TimeoutError

        with patch("app.services.stt.providers.xunfei_provider.asyncio.wait_for", timeout_wait_for):
            result = await provider.transcribe_file(wav_path)

        assert "转写超时" in result
        os.unlink(wav_path)
