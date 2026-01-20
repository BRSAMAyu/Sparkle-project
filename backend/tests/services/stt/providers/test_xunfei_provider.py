"""
科大讯飞星火STT Provider测试
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.services.stt.providers.xunfei_provider import XunFeiProvider


@pytest.mark.asyncio
async def test_xunfei_provider_init():
    """测试XunFeiProvider初始化"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = "test_key"
        mock_settings.XUNFEI_API_SECRET = "test_secret"
        mock_settings.XUNFEI_STT_DOMAIN = "iat"
        mock_settings.XUNFEI_STT_LANGUAGE = "zh-CN"
        mock_settings.XUNFEI_STT_SAMPLE_RATE = 16000
        mock_settings.XUNFEI_STT_EOS_MS = 6000

        provider = XunFeiProvider()
        assert provider.api_key == "test_key"
        assert provider.api_secret == "test_secret"
        assert provider.domain == "iat"
        assert provider.language == "zh-CN"
        assert provider.sample_rate == 16000
        assert provider.eos_ms == 6000


@pytest.mark.asyncio
async def test_xunfei_provider_init_no_credentials():
    """测试XunFeiProvider初始化（无API密钥）"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        provider = XunFeiProvider()
        assert provider.api_key == ""
        assert provider.api_secret == ""


@pytest.mark.asyncio
async def test_xunfei_provider_generate_auth_url():
    """测试生成科大讯飞鉴权URL"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = "test_key"
        mock_settings.XUNFEI_API_SECRET = "test_secret"
        mock_settings.XUNFEI_STT_DOMAIN = "iat"
        mock_settings.XUNFEI_STT_LANGUAGE = "zh-CN"
        mock_settings.XUNFEI_STT_SAMPLE_RATE = 16000
        mock_settings.XUNFEI_STT_EOS_MS = 6000

        provider = XunFeiProvider()
        url = provider._generate_auth_url()

        # 验证URL格式
        assert "wss://iat.xf-yun.com/v1/iat" in url
        assert "authorization=" in url
        assert "date=" in url
        assert "host=" in url


@pytest.mark.asyncio
async def test_xunfei_provider_build_audio_frame():
    """测试构建音频帧"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = "test_key"
        mock_settings.XUNFEI_API_SECRET = "test_secret"

        provider = XunFeiProvider()

        # 测试普通帧
        audio_data = b"test_audio"
        frame = provider._build_audio_frame(audio_data, is_last=False)
        assert len(frame) > len(audio_data)

        # 测试最后一帧
        frame = provider._build_audio_frame(audio_data, is_last=True)
        assert len(frame) > len(audio_data)


@pytest.mark.asyncio
async def test_xunfei_provider_parse_response():
    """测试解析科大讯飞响应"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = "test_key"
        mock_settings.XUNFEI_API_SECRET = "test_secret"

        provider = XunFeiProvider()

        # 测试有效响应
        response_data = {
            "data": {
                "ws": [
                    {"bg": 0, "cw": [{"w": "你好"}]},
                    {"bg": 1, "cw": [{"w": "世界"}]},
                ]
            }
        }
        result = provider._parse_response(response_data)
        assert result == "你好世界"

        # 测试无效响应
        result = provider._parse_response({})
        assert result is None

        # 测试空响应
        result = provider._parse_response({"data": {}})
        assert result is None


@pytest.mark.asyncio
async def test_xunfei_provider_transcribe_stream_no_credentials():
    """测试XunFeiProvider流式转写（无API密钥）"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = ""
        mock_settings.XUNFEI_API_SECRET = ""

        provider = XunFeiProvider()

        async def mock_audio_stream():
            yield b"audio_chunk_1"

        results = []
        async for text in provider.transcribe_stream(mock_audio_stream()):
            results.append(text)

        assert len(results) == 1
        assert "科大讯飞API密钥未配置" in results[0]


@pytest.mark.asyncio
async def test_xunfei_provider_close():
    """测试XunFeiProvider的close方法"""
    with patch("app.services.stt.providers.xunfei_provider.settings") as mock_settings:
        mock_settings.XUNFEI_API_KEY = "test_key"
        mock_settings.XUNFEI_API_SECRET = "test_secret"

        provider = XunFeiProvider()
        await provider.close()  # 应该不会抛出异常
