"""
Unit Tests for Translation Service

Tests coverage:
- Segment-based translation
- Cache hit/miss scenarios
- Timeout handling
- Glossary application
- Error handling
- Cache key stability
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from tests._credentials import TEST_HY_API_KEY, TEST_SF_API_KEY
from app.services.translation_service import (
    translation_service,
    TranslationService,
    TranslationSegment,
    TranslatedSegment,
    TranslationResult
)


@pytest.fixture
def mock_cache_service():
    """Mock cache service"""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    mock = MagicMock()
    mock.chat = AsyncMock()
    mock.chat_model = "test-model"
    return mock


@pytest.mark.asyncio
async def test_translate_cache_hit(mock_cache_service, mock_llm_service):
    """Test translation with cache hit - should not call LLM"""
    service = TranslationService()

    # Mock cache hit
    cached_data = {
        "segments": [
            {
                "id": "s0",
                "translation": "缓存",
                "notes": ["cache = 缓存"],
                "spans": []
            }
        ]
    }
    mock_cache_service.get.return_value = cached_data

    segments = [TranslationSegment(id="s0", text="cache")]

    with patch("app.services.translation_service.cache_service", mock_cache_service):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN"
        )

    # Assertions
    assert result.cache_hit is True
    assert result.provider == "cache"
    assert result.model_id == "cached"
    assert len(result.segments) == 1
    assert result.segments[0].translation == "缓存"

    # LLM should not be called
    mock_cache_service.get.assert_called_once()
    cache_key = mock_cache_service.get.call_args[0][0]
    assert cache_key.startswith("translation:")


@pytest.mark.asyncio
async def test_translate_cache_miss(mock_cache_service, mock_llm_service):
    """Test translation with cache miss - should call LLM"""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None
    mock_llm_service.chat.return_value = "数据库"

    segments = [TranslationSegment(id="s0", text="database")]

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value="数据库")

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", return_value=mock_client), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", "test-key"):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN"
        )

    # Assertions
    assert result.cache_hit is False
    assert result.provider == "hunyuan"
    assert len(result.segments) == 1
    assert result.segments[0].translation == "数据库"

    # Hunyuan client should be called
    mock_client.chat.assert_awaited_once()

    # Result should be cached
    args, kwargs = mock_cache_service.set.call_args
    assert args is not None  # set was called
    assert kwargs['ttl'] == 86400  # 24 hours
    assert args[0].startswith("translation:")  # correct cache key prefix


@pytest.mark.asyncio
async def test_translate_with_siliconflow_provider_label(mock_cache_service, mock_llm_service):
    """When only SILICONFLOW_API_KEY is set, provider should be siliconflow."""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None

    segments = [TranslationSegment(id="s0", text="database")]

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value="数据库")

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", return_value=mock_client), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", ""), \
         patch("app.services.translation_service.settings.SILICONFLOW_API_KEY", TEST_SF_API_KEY):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN",
        )

    assert result.cache_hit is False
    assert result.provider == "siliconflow"
    assert result.segments[0].translation == "数据库"
    mock_client.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_translate_falls_back_to_backup_provider_when_hunyuan_fails(mock_cache_service, mock_llm_service):
    service = TranslationService()
    mock_cache_service.get.return_value = None

    failing_client = MagicMock()
    failing_client.chat = AsyncMock(side_effect=RuntimeError("429"))
    success_client = MagicMock()
    success_client.chat = AsyncMock(return_value="备用翻译")

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", side_effect=[failing_client, success_client]), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", TEST_HY_API_KEY), \
         patch("app.services.translation_service.settings.SILICONFLOW_API_KEY", TEST_SF_API_KEY):
        result = await service.translate(
            segments=[TranslationSegment(id="s0", text="backup")],
            source_lang="en",
            target_lang="zh-CN",
        )

    assert result.provider == "siliconflow"
    assert result.segments[0].translation == "备用翻译"
    failing_client.chat.assert_awaited_once()
    success_client.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_translate_with_glossary(mock_cache_service, mock_llm_service):
    """Test translation with glossary application"""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None
    mock_llm_service.chat.return_value = "应用程序接口"

    segments = [TranslationSegment(id="s0", text="The API endpoint")]

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value="应用程序接口")

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", return_value=mock_client), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", "test-key"):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN",
            glossary_id="cs_terms_v1"
        )

    # Assertions
    assert len(result.segments) == 1

    # Check that Hunyuan client was called with glossary in prompt
    call_args = mock_client.chat.await_args
    messages = call_args.kwargs['messages']
    prompt = messages[1]['content']

    # Glossary should be included in prompt
    assert "Terminology:" in prompt
    assert "API: 应用程序接口" in prompt


@pytest.mark.asyncio
async def test_translate_timeout_handling(mock_cache_service, mock_llm_service):
    """Test timeout fallback for slow translations"""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None

    # Simulate timeout in Hunyuan branch
    async def slow_translation(*args, **kwargs):
        await asyncio.sleep(10)  # Longer than timeout
        return "translation"

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(side_effect=slow_translation)

    segments = [TranslationSegment(id="s0", text="some text")]

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", return_value=mock_client), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", "test-key"):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN",
            timeout=0.1  # Very short timeout
        )

    # Should have fallback placeholder
    assert len(result.segments) == 1
    assert "[Translation timeout" in result.segments[0].translation
    assert "Translation service timeout" in result.segments[0].notes


@pytest.mark.asyncio
async def test_translate_falls_back_to_generic_llm_after_all_specialists_fail(mock_cache_service, mock_llm_service):
    service = TranslationService()
    mock_cache_service.get.return_value = None
    mock_llm_service.chat.return_value = "通用翻译"

    failing_client = MagicMock()
    failing_client.chat = AsyncMock(side_effect=RuntimeError("provider down"))

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", side_effect=[failing_client, failing_client]), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", TEST_HY_API_KEY), \
         patch("app.services.translation_service.settings.SILICONFLOW_API_KEY", TEST_SF_API_KEY):
        result = await service.translate(
            segments=[TranslationSegment(id="s0", text="fallback me")],
            source_lang="en",
            target_lang="zh-CN",
        )

    assert result.provider == "llm"
    assert result.segments[0].translation == "通用翻译"
    mock_llm_service.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_translate_multiple_segments(mock_cache_service, mock_llm_service):
    """Test translation with multiple segments"""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None

    # Return different translations for each segment
    translations = ["句子一", "句子二", "句子三"]

    async def create_translation(*args, **kwargs):
        return translations.pop(0) if translations else "default"

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(side_effect=create_translation)

    segments = [
        TranslationSegment(id="s0", text="Sentence one"),
        TranslationSegment(id="s1", text="Sentence two"),
        TranslationSegment(id="s2", text="Sentence three"),
    ]

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", return_value=mock_client), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", "test-key"):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN"
        )

    # Assertions
    assert len(result.segments) == 3
    assert result.segments[0].translation == "句子一"
    assert result.segments[1].translation == "句子二"
    assert result.segments[2].translation == "句子三"

    # Hunyuan client should be called 3 times
    assert mock_client.chat.await_count == 3


@pytest.mark.asyncio
async def test_cache_key_stability(mock_cache_service, mock_llm_service):
    """Test that cache keys are stable across identical requests"""
    service = TranslationService()

    mock_cache_service.get.return_value = None
    mock_llm_service.chat.return_value = "测试"

    segments1 = [TranslationSegment(id="s0", text="Test")]
    segments2 = [TranslationSegment(id="s0", text="Test")]  # Same text

    cache_keys = []

    async def capture_cache_key(key):
        cache_keys.append(key)
        return None

    mock_cache_service.get.side_effect = capture_cache_key

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service):
        # First request
        await service.translate(
            segments=segments1,
            source_lang="en",
            target_lang="zh-CN",
            domain="general",
            style="natural"
        )

        # Second request (identical)
        await service.translate(
            segments=segments2,
            source_lang="en",
            target_lang="zh-CN",
            domain="general",
            style="natural"
        )

    # Cache keys should be identical for same input
    assert len(cache_keys) == 2
    assert cache_keys[0] == cache_keys[1]


@pytest.mark.asyncio
async def test_cache_key_different_for_different_params(mock_cache_service, mock_llm_service):
    """Test that cache keys differ when parameters change"""
    service = TranslationService()

    mock_cache_service.get.return_value = None
    mock_llm_service.chat.return_value = "测试"

    segments = [TranslationSegment(id="s0", text="Test")]

    cache_keys = []

    async def capture_cache_key(key):
        cache_keys.append(key)
        return None

    mock_cache_service.get.side_effect = capture_cache_key

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service):
        # Request 1: natural style
        await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN",
            style="natural"
        )

        # Request 2: concise style
        await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN",
            style="concise"
        )

    # Cache keys should be different
    assert len(cache_keys) == 2
    assert cache_keys[0] != cache_keys[1]


def test_segment_text_simple():
    """Test simple text segmentation"""
    service = TranslationService()

    text = "First sentence. Second sentence! Third sentence?"
    segments = service.segment_text(text)

    assert len(segments) == 3
    assert segments[0].id == "s0"
    assert segments[0].text == "First sentence"
    assert segments[1].text == "Second sentence"
    assert segments[2].text == "Third sentence"


def test_segment_text_chinese():
    """Test Chinese text segmentation"""
    service = TranslationService()

    text = "第一句。第二句！第三句？"
    segments = service.segment_text(text)

    assert len(segments) == 3
    assert segments[0].text == "第一句"
    assert segments[1].text == "第二句"
    assert segments[2].text == "第三句"


def test_segment_text_empty():
    """Test empty text segmentation"""
    service = TranslationService()

    segments = service.segment_text("")
    assert len(segments) == 0

    segments = service.segment_text("   ")
    assert len(segments) == 0


def test_load_glossary_cs_terms():
    """Test loading built-in CS glossary"""
    service = TranslationService()

    # Use asyncio.run for async test
    import asyncio
    glossary = asyncio.run(service._load_glossary("cs_terms_v1"))

    assert len(glossary) == 10
    assert {"source": "cache", "target": "缓存"} in glossary
    assert {"source": "database", "target": "数据库"} in glossary
    assert {"source": "API", "target": "应用程序接口"} in glossary


def test_load_glossary_unknown():
    """Test loading unknown glossary returns empty list"""
    service = TranslationService()

    import asyncio
    glossary = asyncio.run(service._load_glossary("unknown_glossary"))

    assert len(glossary) == 0


def test_generate_cache_key_format():
    """Test cache key format"""
    service = TranslationService()

    segments = [TranslationSegment(id="s0", text="Test")]
    cache_key = service._generate_cache_key(
        segments=segments,
        source_lang="en",
        target_lang="zh-CN",
        domain="general",
        style="natural",
        glossary_id=None
    )

    # Cache key should start with "translation:"
    assert cache_key.startswith("translation:")

    # Should have hash part (16 chars)
    hash_part = cache_key.split(":")[1]
    assert len(hash_part) == 16


@pytest.mark.asyncio
async def test_translate_error_handling(mock_cache_service, mock_llm_service):
    """Test error handling during translation"""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None

    # Simulate Hunyuan error and LLM fallback error
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(side_effect=Exception("Hunyuan API error"))
    mock_llm_service.chat.side_effect = Exception("LLM API error")

    segments = [TranslationSegment(id="s0", text="test")]

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch("app.services.translation_service.SecureLLMClient.get", return_value=mock_client), \
         patch("app.services.translation_service.settings.HUNYUAN_API_KEY", "test-key"):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN"
        )

    # Should have error placeholder
    assert len(result.segments) == 1
    assert "[Translation error" in result.segments[0].translation
    assert "Exception" in result.segments[0].notes[0]


@pytest.mark.asyncio
async def test_terminology_notes_extraction(mock_cache_service, mock_llm_service):
    """Test terminology notes extraction from glossary"""
    service = TranslationService()

    # Mock cache miss
    mock_cache_service.get.return_value = None
    segments = [TranslationSegment(id="s0", text="Cache system uses database")]

    mocked_tx = {
        "segment": TranslatedSegment(
            id="s0",
            translation="缓存系统使用数据库",
            notes=["cache = 缓存", "database = 数据库"],
            spans=[],
        ),
        "provider": "llm",
        "model": "mock-model",
    }

    with patch("app.services.translation_service.cache_service", mock_cache_service), \
         patch("app.services.translation_service.llm_service", mock_llm_service), \
         patch.object(service, "_translate_segment", AsyncMock(return_value=mocked_tx)):
        result = await service.translate(
            segments=segments,
            source_lang="en",
            target_lang="zh-CN",
            glossary_id="cs_terms_v1"
        )

    # Should extract terminology notes
    notes = result.segments[0].notes
    assert len(notes) > 0

    # Should match glossary terms found in text
    note_text = " ".join(notes)
    assert "cache" in note_text.lower() or "database" in note_text.lower()


def test_translation_validation_accepts_translated_content_with_metadata_phrase():
    assert TranslationService._is_valid_translation_output(
        "术语说明：保留短语 Source language: English 作为示例文本。",
        "Source language: English",
        source_lang="en",
        target_lang="zh-CN",
    ) is True


def test_translation_validation_rejects_prompt_echo_in_source_language():
    assert TranslationService._is_valid_translation_output(
        "Source language: English\nTarget language: Chinese\nTranslate the following text",
        "Hello world",
        source_lang="en",
        target_lang="zh-CN",
    ) is False
