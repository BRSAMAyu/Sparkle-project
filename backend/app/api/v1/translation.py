"""
Translation API
Provides text translation with segmentation, caching, and glossary support
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from loguru import logger

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.translation_service import (
    translation_service,
    TranslationSegment,
    TranslationResult
)

router = APIRouter()

# ============ Schemas ============

class TranslateRequest(BaseModel):
    """Request schema for translation"""
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


class SegmentData(BaseModel):
    """Translated segment data"""
    id: str
    translation: str
    notes: List[str] = []


class TranslateResponse(BaseModel):
    """Response schema for translation"""
    success: bool
    translation: str
    segments: List[SegmentData]
    meta: dict


# ============ Endpoints ============

@router.post("/translate", response_model=TranslateResponse, summary="翻译文本")
async def translate_text(
    request: TranslateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Translate text with automatic segmentation and caching

    Features:
    - Automatic sentence segmentation for better caching
    - Domain-aware terminology (cs, math, business, general)
    - Glossary support for consistent terminology
    - L2 caching with 24-hour TTL
    - Graceful timeout handling (5s per segment)

    Args:
        request: Translation request parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        TranslateResponse with translation and metadata
    """
    try:
        # 1. Segment text
        segments = translation_service.segment_text(request.text)

        if not segments:
            raise HTTPException(
                status_code=400,
                detail="No valid text segments found in input"
            )

        logger.info(
            f"Translation request from user {current_user.id}: "
            f"{len(segments)} segments, {request.source_lang}->{request.target_lang}"
        )

        # 2. Translate with caching
        result: TranslationResult = await translation_service.translate(
            segments=segments,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            domain=request.domain,
            style=request.style,
            glossary_id=request.glossary_id,
            timeout=5.0  # 5 seconds per segment
        )

        # 3. Combine segments into full translation
        full_translation = " ".join([s.translation for s in result.segments])

        # 4. Format response
        segments_data = [
            SegmentData(
                id=s.id,
                translation=s.translation,
                notes=s.notes
            )
            for s in result.segments
        ]

        logger.info(
            f"Translation completed for user {current_user.id}: "
            f"provider={result.provider}, cache_hit={result.cache_hit}, "
            f"latency={result.latency_ms}ms"
        )

        return TranslateResponse(
            success=True,
            translation=full_translation,
            segments=segments_data,
            meta={
                "provider": result.provider,
                "model_id": result.model_id,
                "cache_hit": result.cache_hit,
                "latency_ms": result.latency_ms,
                "segment_count": len(result.segments),
                "source_lang": request.source_lang,
                "target_lang": request.target_lang,
                "domain": request.domain,
                "style": request.style
            }
        )

    except ValueError as e:
        logger.warning(f"Translation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Translation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Translation service error: {str(e)}"
        )


@router.get("/glossaries", summary="获取可用词汇表")
async def list_glossaries(
    current_user: User = Depends(get_current_user)
):
    """
    List available glossaries for translation

    Returns:
        List of available glossary IDs and descriptions
    """
    # For MVP, return hardcoded glossaries
    # In Phase 2, this will query the database
    glossaries = [
        {
            "id": "cs_terms_v1",
            "name": "Computer Science Terms (CS)",
            "description": "Common CS terminology (cache, database, API, etc.)",
            "term_count": 10,
            "language_pair": "en->zh-CN"
        }
    ]

    return {
        "glossaries": glossaries,
        "total": len(glossaries)
    }
