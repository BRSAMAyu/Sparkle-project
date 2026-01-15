"""
Translation Service - Focus Translate v2

Provides segment-based translation with caching, glossary support, and timeout handling.
"""
import asyncio
import hashlib
import json
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config.settings import settings
from app.services.llm_service import llm_service
from app.core.cache import cache_service
from app.services.vocabulary_service import vocabulary_service


@dataclass
class TranslationSegment:
    """Input segment for translation"""
    id: str
    text: str


@dataclass
class TranslatedSegment:
    """Translated segment with metadata"""
    id: str
    translation: str
    notes: List[str]
    spans: List[Dict[str, Any]]  # Alignment spans (future enhancement)


@dataclass
class TranslationResult:
    """Complete translation result"""
    segments: List[TranslatedSegment]
    provider: str
    model_id: str
    cache_hit: bool
    latency_ms: int
    recommendation: Optional[Dict[str, Any]] = None


class TranslationService:
    """
    Translation service with segmentation, caching, and terminology support.

    Features:
    - Segment-based translation for better caching
    - L2 cache with stable keys (segmenter_version + prompt_version)
    - Glossary support for terminology consistency
    - Timeout fallback for reliability
    """

    VERSION = "v2"
    SEGMENTER_VERSION = "seg_v2"
    PROMPT_VERSION = "focus_translate_v2"

    def __init__(self):
        self.segmenter_version = self.SEGMENTER_VERSION
        self.prompt_version = self.PROMPT_VERSION

    async def translate(
        self,
        segments: List[TranslationSegment],
        source_lang: str,
        target_lang: str,
        domain: str = "general",
        style: str = "natural",
        glossary_id: Optional[str] = None,
        timeout: float = 5.0,
        # v2 Signals
        user_id: Optional[UUID] = None,
        fingerprint: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> TranslationResult:
        """
        Translate text segments with caching and terminology support.

        Args:
            segments: Text segments to translate
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "zh-CN")
            domain: Domain for terminology ("cs", "math", "business", "general")
            style: Translation style ("concise", "literal", "natural")
            glossary_id: Optional glossary for terminology consistency
            timeout: Max time per segment (default: 5.0s)
            user_id: User ID for quota tracking
            fingerprint: Content hash for signal tracking
            db: Database session for quota check

        Returns:
            TranslationResult with translated segments
        """
        start_time = time.time()

        # 0. Evaluate signals (Async, non-blocking for translation)
        recommendation = None
        if user_id and db:
            try:
                recommendation = await self._evaluate_signals(user_id, fingerprint, db)
            except Exception as e:
                logger.warning(f"Signal evaluation failed: {e}")

        # 1. Check L2 cache (by segment hash)
        cache_key = self._generate_cache_key(
            segments, source_lang, target_lang, domain, style, glossary_id
        )

        cached = await cache_service.get(cache_key)
        if cached:
            logger.info(f"Translation cache hit: {cache_key}")
            return TranslationResult(
                segments=[
                    TranslatedSegment(**seg) for seg in cached["segments"]
                ],
                provider="cache",
                model_id="cached",
                cache_hit=True,
                latency_ms=int((time.time() - start_time) * 1000),
                recommendation=recommendation
            )

        # 2. Load glossary if specified
        glossary_terms = await self._load_glossary(glossary_id) if glossary_id else []

        # 3. Translate each segment
        translated_segments = []
        for segment in segments:
            try:
                result = await asyncio.wait_for(
                    self._translate_segment(
                        segment, source_lang, target_lang,
                        domain, style, glossary_terms
                    ),
                    timeout=timeout
                )
                translated_segments.append(result)
            except asyncio.TimeoutError:
                logger.warning(f"Translation timeout for segment {segment.id}: {segment.text[:50]}...")
                # Fallback: simple placeholder
                translated_segments.append(TranslatedSegment(
                    id=segment.id,
                    translation=f"[Translation timeout: {segment.text[:50]}...]",
                    notes=["Translation service timeout"],
                    spans=[]
                ))
            except Exception as e:
                logger.error(f"Translation error for segment {segment.id}: {e}")
                translated_segments.append(TranslatedSegment(
                    id=segment.id,
                    translation=f"[Translation error: {str(e)}]",
                    notes=[f"Error: {type(e).__name__}"],
                    spans=[]
                ))

        # 4. Store in cache
        result = TranslationResult(
            segments=translated_segments,
            provider="llm",  # Or specific provider
            model_id=llm_service.chat_model,
            cache_hit=False,
            latency_ms=int((time.time() - start_time) * 1000),
            recommendation=recommendation
        )

        # Cache for 24 hours
        await cache_service.set(cache_key, {
            "segments": [asdict(s) for s in translated_segments]
        }, ttl=86400)

        logger.info(
            f"Translation completed: {len(segments)} segments, "
            f"{result.latency_ms}ms, cache_key={cache_key[:16]}..."
        )

        return result

    async def _evaluate_signals(
        self, 
        user_id: UUID, 
        fingerprint: Optional[str], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Evaluate user signals to generate recommendations.
        
        Rules:
        1. Daily Quota: Max cards/day (configurable).
        2. Repetition: If fingerprint seen > 1 times in 1 hour -> Suggest card.
        """
        daily_limit = settings.TRANSLATION_DAILY_CARD_LIMIT
        
        # 1. Check Quota (Fast DB query)
        created_today = await vocabulary_service.get_today_creation_count(db, user_id)
        quota_remaining = max(0, daily_limit - created_today)
        
        should_create = False
        reason = None
        
        if quota_remaining > 0 and fingerprint:
            # 2. Check Repetition (Redis)
            # Key: translation:signal:freq:{user_id}:{fingerprint}
            # TTL: 1 hour (short term memory)
            freq_key = f"translation:signal:freq:{user_id}:{fingerprint}"
            count = await cache_service.incr(freq_key)
            await cache_service.expire(freq_key, 3600) 
            
            if count >= 2:
                should_create = True
                reason = "repeated_query"
        
        return {
            "should_create_card": should_create,
            "reason": reason,
            "daily_quota_remaining": quota_remaining
        }

    async def _translate_segment(
        self,
        segment: TranslationSegment,
        source_lang: str,
        target_lang: str,
        domain: str,
        style: str,
        glossary_terms: List[Dict[str, str]]
    ) -> TranslatedSegment:
        """Translate a single segment using LLM"""

        # Build prompt with glossary
        glossary_text = ""
        if glossary_terms:
            glossary_text = "\n\nTerminology:\n" + "\n".join(
                [f"- {t['source']}: {t['target']}" for t in glossary_terms[:10]]
            )

        prompt = f"""Translate the following {source_lang} text to {target_lang}.
Domain: {domain}
Style: {style}
{glossary_text}

Text: {segment.text}

Output ONLY the translation, no explanations."""

        # Call LLM service
        response = await llm_service.chat(
            messages=[{"role": "user", "content": prompt}],
            model=llm_service.chat_model  # Fast model
        )

        translation = response.strip()

        # Extract terminology notes (simple heuristic)
        notes = []
        for term in glossary_terms:
            if term["source"].lower() in segment.text.lower():
                notes.append(f"{term['source']} = {term['target']}")

        return TranslatedSegment(
            id=segment.id,
            translation=translation,
            notes=notes,
            spans=[]  # TODO: Implement alignment extraction in Phase 2
        )

    def _generate_cache_key(
        self,
        segments: List[TranslationSegment],
        source_lang: str,
        target_lang: str,
        domain: str,
        style: str,
        glossary_id: Optional[str]
    ) -> str:
        """
        Generate stable cache key.

        Includes:
        - Normalized segment text (lowercase, trimmed)
        - Language pair
        - Domain and style
        - Glossary ID
        - Segmenter version
        - Prompt version
        """
        # Normalize text
        normalized = [s.text.strip().lower() for s in segments]

        key_data = {
            "segments": normalized,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "style": style,
            "glossary_id": glossary_id or "",
            "segmenter_version": self.segmenter_version,
            "prompt_version": self.prompt_version
        }

        key_str = json.dumps(key_data, sort_keys=True)
        hash_val = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        return f"translation:{hash_val}"

    async def _load_glossary(self, glossary_id: str) -> List[Dict[str, str]]:
        """
        Load glossary terms from database or config.

        Args:
            glossary_id: Glossary identifier

        Returns:
            List of term mappings [{"source": "cache", "target": "缓存"}, ...]
        """
        # TODO: Implement glossary storage in database
        # For MVP, return built-in CS glossary

        if glossary_id == "cs_terms_v1":
            return [
                {"source": "cache", "target": "缓存"},
                {"source": "database", "target": "数据库"},
                {"source": "API", "target": "应用程序接口"},
                {"source": "function", "target": "函数"},
                {"source": "variable", "target": "变量"},
                {"source": "loop", "target": "循环"},
                {"source": "condition", "target": "条件"},
                {"source": "array", "target": "数组"},
                {"source": "object", "target": "对象"},
                {"source": "class", "target": "类"},
            ]

        return []

    def segment_text(self, text: str) -> List[TranslationSegment]:
        """
        Segment text into translation units.

        Uses simple sentence splitting for MVP.
        TODO: Use proper sentence tokenizer (spacy, nltk) in Phase 2.

        Args:
            text: Input text to segment

        Returns:
            List of TranslationSegment objects
        """
        import re

        # Split by sentence terminators
        sentences = re.split(r'[.!?。！？]+', text)

        # Filter empty and create segments
        segments = []
        for i, sentence in enumerate(sentences):
            cleaned = sentence.strip()
            if cleaned:
                segments.append(TranslationSegment(
                    id=f"s{i}",
                    text=cleaned
                ))

        return segments


# Singleton instance
translation_service = TranslationService()
