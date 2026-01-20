"""
STT Provider抽象接口测试
"""
import pytest
from unittest.mock import AsyncMock, Mock
from app.services.stt.providers.base import STTProvider


class MockSTTProvider(STTProvider):
    """Mock STT Provider for testing"""

    async def transcribe_stream(self, audio_stream, language=None, sample_rate=None):
        async for chunk in audio_stream:
            pass
        return "mocked transcription"

    async def transcribe_file(self, file_path, language=None):
        return "mocked transcription"


@pytest.mark.asyncio
async def test_stt_provider_abstract_methods():
    """测试STTProvider抽象方法"""
    provider = MockSTTProvider()

    # 测试transcribe_file方法
    result = await provider.transcribe_file("test.wav", language="zh-CN")
    assert result == "mocked transcription"

    # 测试transcribe_stream方法
    async def mock_audio_stream():
        yield b"audio_chunk_1"
        yield b"audio_chunk_2"

    result = await provider.transcribe_stream(mock_audio_stream(), language="zh-CN")
    assert result == "mocked transcription"

    # 测试close方法
    await provider.close()


@pytest.mark.asyncio
async def test_stt_provider_close():
    """测试STTProvider的close方法"""
    provider = MockSTTProvider()

    # close方法应该不会抛出异常
    await provider.close()
