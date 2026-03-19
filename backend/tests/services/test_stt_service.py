"""
STT Service测试
"""

import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.stt_service import STTService


@pytest.mark.asyncio
async def test_stt_service_init_zhipu():
    """测试 STTService 初始化（智谱 Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_zhipu.return_value = mock_provider

            service = STTService()
            assert service.provider == mock_provider


@pytest.mark.asyncio
async def test_stt_service_init_unknown_provider():
    """测试STTService初始化（未知Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "unknown"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = ""
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        service = STTService()
        assert service.provider is None


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_success():
    """测试STTService文件转写成功"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_provider.transcribe_file = AsyncMock(return_value="测试转写结果")
            mock_zhipu.return_value = mock_provider

            service = STTService()

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"mock audio data")
                temp_path = f.name

            try:
                result = await service.transcribe_file(temp_path, language="zh-CN")
                assert result["text"] == "测试转写结果"
                assert not result["error"]
            finally:
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_no_provider():
    """测试STTService文件转写（无Provider）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "unknown"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = ""
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        service = STTService()
        result = await service.transcribe_file("test.wav")
        assert "Provider Not Initialized" in result["text"]
        assert result["error"]


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_not_found():
    """测试STTService文件不存在"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_zhipu.return_value = mock_provider

            service = STTService()
            result = await service.transcribe_file("non_existent_file.wav")
            assert result["text"] == ""
            assert result["error"] == "File not found"


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_error():
    """测试STTService转写错误"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.DEMO_MODE = False
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_provider.transcribe_file = AsyncMock(side_effect=Exception("API Error"))
            mock_zhipu.return_value = mock_provider

            service = STTService()

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"mock audio data")
                temp_path = f.name

            try:
                result = await service.transcribe_file(temp_path)
                assert "Transcription Error" in result["text"]
                assert result["error"]
            finally:
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_transcribe_file_demo_mode():
    """测试STTService转写错误（演示模式）"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.DEMO_MODE = True
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_provider.transcribe_file = AsyncMock(side_effect=Exception("API Error"))
            mock_zhipu.return_value = mock_provider

            service = STTService()

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"mock audio data")
                temp_path = f.name

            try:
                result = await service.transcribe_file(temp_path)
                assert "演示模式" in result["text"]
                assert not result["error"]
            finally:
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_enhance_transcript():
    """测试STTService转写增强"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_zhipu.return_value = mock_provider

            service = STTService()

            # 测试空文本
            result = await service.enhance_transcript("")
            assert result == ""

            # 测试短文本
            result = await service.enhance_transcript("a")
            assert result == "a"

            # 测试正常文本（mock 当前 STT fallback wrapper）
            with patch(
                "app.services.llm_fallback_utils.stt_llm.call",
                AsyncMock(return_value="增强后的文本"),
            ):
                result = await service.enhance_transcript("测试文本")
                assert result == "增强后的文本"


@pytest.mark.asyncio
async def test_stt_service_create_audio_stream_generator():
    """测试创建音频流生成器"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = "test-key"
        mock_settings.XUNFEI_APP_ID = ""
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            mock_provider = Mock()
            mock_zhipu.return_value = mock_provider

            service = STTService()

            # Mock WebSocket
            mock_websocket = Mock()
            mock_websocket.receive = AsyncMock(
                side_effect=[
                    {"bytes": b"chunk1"},
                    {"bytes": b"chunk2"},
                    {"text": "STOP"},
                ]
            )

            chunks = []
            async for chunk in service._create_audio_stream_generator(mock_websocket):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == b"chunk1"
            assert chunks[1] == b"chunk2"


@pytest.mark.asyncio
async def test_stt_service_init_xunfei_provider():
    """测试 xunfei 配置会初始化讯飞 provider"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.ZHIPU_API_KEY = ""
        mock_settings.XUNFEI_APP_ID = "app-id"
        mock_settings.XUNFEI_API_KEY = "api-key"
        mock_settings.XUNFEI_API_SECRET = "api-secret"

        with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
            mock_provider = Mock()
            mock_xunfei.return_value = mock_provider

            service = STTService()
            assert service.provider == mock_provider


@pytest.mark.asyncio
async def test_stt_service_falls_back_to_xunfei_when_zhipu_quota_exhausted():
    """测试主 provider 配额异常时会切换到讯飞"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "zhipu"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.DEMO_MODE = False
        mock_settings.ZHIPU_API_KEY = "zhipu-key"
        mock_settings.XUNFEI_APP_ID = "app-id"
        mock_settings.XUNFEI_API_KEY = "api-key"
        mock_settings.XUNFEI_API_SECRET = "api-secret"

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
                primary_provider = Mock()
                primary_provider.transcribe_file = AsyncMock(
                    side_effect=RuntimeError("智谱 ASR 请求失败: 余额不足或无可用资源包,请充值。")
                )
                backup_provider = Mock()
                backup_provider.transcribe_file = AsyncMock(return_value="讯飞转写结果")
                mock_zhipu.return_value = primary_provider
                mock_xunfei.return_value = backup_provider

                service = STTService()

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(b"mock audio data")
                    temp_path = f.name

                try:
                    result = await service.transcribe_file(temp_path)
                    assert result["text"] == "讯飞转写结果"
                    assert result["error"] is False
                    assert service.stream_provider == backup_provider
                finally:
                    os.unlink(temp_path)


@pytest.mark.asyncio
async def test_stt_service_falls_back_when_xunfei_times_out():
    """测试讯飞超时时会自动切换到备用 provider"""
    with patch("app.services.stt_service.settings") as mock_settings:
        mock_settings.STT_PROVIDER = "xunfei"
        mock_settings.UPLOAD_DIR = "./uploads"
        mock_settings.DEMO_MODE = False
        mock_settings.ZHIPU_API_KEY = "zhipu-key"
        mock_settings.XUNFEI_APP_ID = "app-id"
        mock_settings.XUNFEI_API_KEY = "api-key"
        mock_settings.XUNFEI_API_SECRET = "api-secret"

        with patch("app.services.stt.providers.zhipu_provider.ZhipuProvider") as mock_zhipu:
            with patch("app.services.stt.providers.xunfei_provider.XunFeiProvider") as mock_xunfei:
                primary_provider = Mock()
                primary_provider.transcribe_file = AsyncMock(side_effect=TimeoutError("xunfei timeout"))
                backup_provider = Mock()
                backup_provider.transcribe_file = AsyncMock(return_value="智谱兜底结果")
                mock_xunfei.return_value = primary_provider
                mock_zhipu.return_value = backup_provider

                service = STTService()

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(b"mock audio data")
                    temp_path = f.name

                try:
                    result = await service.transcribe_file(temp_path)
                    assert result["text"] == "智谱兜底结果"
                    assert result["error"] is False
                finally:
                    os.unlink(temp_path)
