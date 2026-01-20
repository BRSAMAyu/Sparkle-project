"""
STT Service测试
"""
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.services.stt_service import STTService


@pytest.mark.asyncio
async def test_stt_service_init_xunfei():
    """测试STTService初始化（科大讯飞Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.XUNFEI_API_KEY = "test_key"
        mock_settings.XUNFEI_API_SECRET = "test_secret"
        mock_settings.UPLOAD_DIR = "./uploads"

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_xunfei.return_value = mock_provider

            service = STTService()
            assert service.provider == mock_provider


@pytest.mark.asyncio
async def test_stt_service_init_whisper():
    """测试STTService初始化（Whisper Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "whisper"
        mock_settings.UPLOAD_DIR = "./uploads"

        with patch("app.services.stt.providers.whisper_provider.WhisperProvider") as mock_whisper:
            mock_provider = Mock()
            mock_whisper.return_value = mock_provider

            service = STTService()
            assert service.provider == mock_provider


@pytest.mark.asyncio
async def test_stt_service_init_unknown_provider():
    """测试STTService初始化（未知Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "unknown"
        mock_settings.UPLOAD_DIR = "./uploads"

        service = STTService()
        assert service.provider is None


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_success():
    """测试STTService文件转写成功"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_provider.transcribe_file = AsyncMock(return_value="测试转写结果")
            mock_xunfei.return_value = mock_provider

            service = STTService()

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"mock audio data")
                temp_path = f.name

            try:
                result = await service.transcribe_file(temp_path, language="zh-CN")
                assert result["text"] == "测试转写结果"
                assert result["error"] == False
            finally:
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_no_provider():
    """测试STTService文件转写（无Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "unknown"
        mock_settings.UPLOAD_DIR = "./uploads"

        service = STTService()
        result = await service.transcribe_file("test.wav")
        assert "Provider Not Initialized" in result["text"]
        assert result["error"] == True


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_not_found():
    """测试STTService文件不存在"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_xunfei.return_value = mock_provider

            service = STTService()
            result = await service.transcribe_file("non_existent_file.wav")
            assert result["text"] == ""
            assert result["error"] == "File not found"


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_error():
    """测试STTService转写错误"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.DEMO_MODE = False

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_provider.transcribe_file = AsyncMock(side_effect=Exception("API Error"))
            mock_xunfei.return_value = mock_provider

            service = STTService()

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"mock audio data")
                temp_path = f.name

            try:
                result = await service.transcribe_file(temp_path)
                assert "Transcription Error" in result["text"]
                assert result["error"] == True
            finally:
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_demo_mode():
    """测试STTService转写错误（演示模式）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.DEMO_MODE = True

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_provider.transcribe_file = AsyncMock(side_effect=Exception("API Error"))
            mock_xunfei.return_value = mock_provider

            service = STTService()

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"mock audio data")
                temp_path = f.name

            try:
                result = await service.transcribe_file(temp_path)
                assert "演示模式" in result["text"]
                assert result["error"] == False
            finally:
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_enhance_transcript():
    """测试STTService转写增强"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_xunfei.return_value = mock_provider

            service = STTService()

            # 测试空文本
            result = await service.enhance_transcript("")
            assert result == ""

            # 测试短文本
            result = await service.enhance_transcript("a")
            assert result == "a"

            # 测试正常文本（需要mock llm_service）
            with patch("app.services.stt_service.llm_service") as mock_llm:
                mock_llm.chat = AsyncMock(return_value="增强后的文本")
                result = await service.enhance_transcript("测试文本")
                assert result == "增强后的文本"


@pytest.mark.asyncio
async def test_stt_service_create_audio_stream_generator():
    """测试创建音频流生成器"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_xunfei.return_value = mock_provider

            service = STTService()

            # Mock WebSocket
            mock_websocket = Mock()
            mock_websocket.receive = AsyncMock(side_effect=[
                {"bytes": b"chunk1"},
                {"bytes": b"chunk2"},
                {"text": "STOP"},
            ])

            chunks = []
            async for chunk in service._create_audio_stream_generator(mock_websocket):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == b"chunk1"
            assert chunks[1] == b"chunk2"
