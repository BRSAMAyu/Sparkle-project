"""
Translation Tool
Provides text translation with segmentation, caching, and glossary support
"""
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from app.services.translation_service import translation_service

from .base import BaseTool, ToolCategory, ToolResult

# Language mapping: natural language → ISO code
LANGUAGE_MAP = {
    # Chinese
    "中文": "zh-CN", "zh": "zh-CN", "chinese": "zh-CN", "zh-cn": "zh-CN",
    # English
    "英文": "en", "english": "en",
    # Japanese
    "日文": "ja", "日语": "ja", "japanese": "ja", "日本語": "ja",
    # Korean
    "韩文": "ko", "韩语": "ko", "korean": "ko", "한국어": "ko",
    # French
    "法文": "fr", "法语": "fr", "french": "fr",
    # German
    "德文": "de", "德语": "de", "german": "de",
    # Spanish
    "西班牙文": "es", "西班牙语": "es", "spanish": "es",
    # Russian
    "俄文": "ru", "俄语": "ru", "russian": "ru",
}


def _normalize_language_code(lang: str) -> str:
    """将自然语言或ISO代码统一转换为标准代码"""
    if not lang or lang == "auto":
        return "auto"
    lang_lower = lang.lower()
    return LANGUAGE_MAP.get(lang_lower, lang)


class TranslateTextParams(BaseModel):
    """Translation tool parameters - supports both natural and ISO codes"""
    text: str = Field(..., description="Text to translate", max_length=5000)
    target_lang: str = Field(
        default="zh-CN",
        description="Target language (e.g., '中文', 'zh-CN', 'en', 'ja')"
    )
    source_lang: str = Field(
        default="auto",
        description="Source language, 'auto' for detection"
    )
    domain: str = Field(
        default="general",
        description="Domain: 'cs', 'math', 'business', 'general'"
    )
    style: str = Field(
        default="natural",
        description="Style: 'concise', 'literal', 'natural'"
    )
    glossary_id: str | None = Field(
        default=None,
        description="Glossary ID for terminology (e.g., 'cs_terms_v1')"
    )
    fingerprint: str | None = Field(
        default=None,
        description="Content fingerprint for signal tracking (v2)"
    )


class TranslateTextTool(BaseTool):
    """
    Translate text with segmentation and caching

    This tool translates text from one language to another with:
    - Automatic sentence segmentation for better caching
    - Domain-aware terminology (cs, math, business, general)
    - Glossary support for consistent terminology
    - L2 caching with 24-hour TTL
    - Graceful timeout handling (5s per segment)

    Use cases:
    - "Translate this paragraph to Chinese"
    - "翻译这段代码注释到中文（计算机领域）"
    - "Translate using concise style"
    """

    name = "translate"
    description = """翻译文本到指定语言，支持领域术语、分片处理和缓存。
    使用场景：
    - "把这段英文翻译成中文"
    - "翻译成日语"
    - "中译英（计算机领域）"
    """
    category = ToolCategory.QUERY
    parameters_schema = TranslateTextParams
    requires_confirmation = False

    async def execute(
        self,
        params: TranslateTextParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        """
        Execute translation with segmentation and caching

        Args:
            params: Translation parameters
            user_id: Current user ID
            db_session: Database session (not used, but required by interface)
            tool_call_id: Tool call ID for tracking

        Returns:
            ToolResult with translation data and widget configuration
        """
        try:
            # Normalize language codes (support natural language and ISO codes)
            source_lang = _normalize_language_code(params.source_lang)
            target_lang = _normalize_language_code(params.target_lang)

            # 1. Segment text into translation units
            segments = translation_service.segment_text(params.text)

            if not segments:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="No valid text segments found",
                    suggestion="请提供有效的文本内容"
                )

            logger.info(
                f"Translating {len(segments)} segments from {source_lang} "
                f"to {target_lang} (domain: {params.domain}, style: {params.style})"
            )

            # 2. Translate with caching
            result = await translation_service.translate(
                segments=segments,
                source_lang=source_lang,
                target_lang=target_lang,
                domain=params.domain,
                style=params.style,
                glossary_id=params.glossary_id,
                timeout=15.0,  # 15 seconds per segment (increased from 5s)
                user_id=user_id,  # v2: Pass user_id for signal evaluation
                fingerprint=params.fingerprint,  # v2: Content fingerprint for signal tracking
                db=db_session,  # v2: Pass db for quota tracking
            )

            # 3. Combine segments into full translation
            full_translation = " ".join([s.translation for s in result.segments])

            # 4. Collect terminology notes
            all_notes = []
            for seg in result.segments:
                all_notes.extend(seg.notes)
            unique_notes = list(set(all_notes))  # Remove duplicates

            # 5. Log performance
            logger.info(
                f"Translation completed: provider={result.provider}, "
                f"cache_hit={result.cache_hit}, latency={result.latency_ms}ms, "
                f"segments={len(result.segments)}"
            )

            # 6. Build recommendation data for frontend
            recommendation_data = None
            if result.recommendation:
                recommendation_data = {
                    "should_create_card": result.recommendation.get("should_create_card", False),
                    "reason": result.recommendation.get("reason"),
                    "daily_quota_remaining": result.recommendation.get("daily_quota_remaining", 0),
                }

            # 7. Return result with widget data for frontend
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "translation": full_translation,
                    "source_text": params.text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "segments": [
                        {
                            "id": s.id,
                            "translation": s.translation,
                            "notes": s.notes
                        }
                        for s in result.segments
                    ],
                    "terminology_notes": unique_notes,
                    "provider": result.provider,
                    "model_id": result.model_id,
                    "cache_hit": result.cache_hit,
                    "latency_ms": result.latency_ms,
                    "recommendation": recommendation_data,  # v2: Signal evaluation results
                },
                widget_type="translation_result",
                widget_data={
                    "source_text": params.text,
                    "target_text": full_translation,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "domain": params.domain,
                    "style": params.style,
                    "segments": [
                        {
                            "id": s.id,
                            "source": segments[i].text if i < len(segments) else "",
                            "translation": s.translation,
                            "notes": s.notes
                        }
                        for i, s in enumerate(result.segments)
                    ],
                    "terminology_notes": unique_notes,
                    "cache_hit": result.cache_hit,
                    "show_save_button": True,  # Allow saving to knowledge graph
                }
            )

        except Exception as e:
            logger.error(f"Translation error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"Translation failed: {str(e)}",
                suggestion="翻译服务暂时不可用，请稍后重试或检查输入文本"
            )
