"""
Translation Tool
Provides text translation with segmentation, caching, and glossary support
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from loguru import logger

from .base import BaseTool, ToolCategory, ToolResult
from app.services.translation_service import (
    translation_service,
    TranslationSegment
)


class TranslateTextParams(BaseModel):
    """Translation tool parameters"""
    text: str = Field(..., description="Text to translate", max_length=5000)
    source_lang: str = Field(
        default="en",
        description="Source language code (e.g., 'en', 'zh-CN')"
    )
    target_lang: str = Field(
        default="zh-CN",
        description="Target language code (e.g., 'en', 'zh-CN')"
    )
    domain: str = Field(
        default="general",
        description="Domain for terminology: 'cs', 'math', 'business', 'general'"
    )
    style: str = Field(
        default="natural",
        description="Translation style: 'concise', 'literal', 'natural'"
    )
    glossary_id: Optional[str] = Field(
        default=None,
        description="Optional glossary ID for terminology consistency (e.g., 'cs_terms_v1')"
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

    name = "translate_text"
    description = """Translate text from one language to another with domain-aware terminology.
    Supports automatic segmentation, caching, and glossary-based consistency.
    Use when the user asks to translate text, phrases, or paragraphs.
    Example: "translate this to Chinese", "翻译成英文", "帮我翻译一下这段话"
    """
    category = ToolCategory.KNOWLEDGE
    parameters_schema = TranslateTextParams
    requires_confirmation = False

    async def execute(
        self,
        params: TranslateTextParams,
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None
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
                f"Translating {len(segments)} segments from {params.source_lang} "
                f"to {params.target_lang} (domain: {params.domain}, style: {params.style})"
            )

            # 2. Translate with caching
            result = await translation_service.translate(
                segments=segments,
                source_lang=params.source_lang,
                target_lang=params.target_lang,
                domain=params.domain,
                style=params.style,
                glossary_id=params.glossary_id,
                timeout=5.0  # 5 seconds per segment
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

            # 6. Return result with widget data for frontend
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "translation": full_translation,
                    "source_text": params.text,
                    "source_lang": params.source_lang,
                    "target_lang": params.target_lang,
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
                    "latency_ms": result.latency_ms
                },
                widget_type="translation_result",
                widget_data={
                    "source_text": params.text,
                    "target_text": full_translation,
                    "source_lang": params.source_lang,
                    "target_lang": params.target_lang,
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
