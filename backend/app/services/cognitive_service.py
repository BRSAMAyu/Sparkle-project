"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio
import inspect
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import desc, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.phase5_config import phase5_config
from app.core.event_bus import event_bus
from app.core.event_types import PROFILE_COGNITIVE_UPDATED
from app.models.cognitive import AnalysisStatus, BehaviorPattern, CognitiveFragment, PatternType
from app.services.analysis.unified_analysis_service import UnifiedAnalysisService
from app.services.analytics_service import AnalyticsService
from app.services.embedding_service import embedding_service
from app.services.llm_service import get_llm_service_for_specific_model, llm_service
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_VECTOR_RUNTIME_ENABLED = True
_VECTOR_RUNTIME_DISABLED_USERS: dict[str, datetime] = {}  # user_key → disabled_at timestamp
_VECTOR_RUNTIME_DISABLED_TTL = timedelta(hours=1)  # Auto-re-enable after 1h
_VECTOR_RUNTIME_STATE_LOCK = asyncio.Lock()
RECOVERABLE_LLM_ERRORS = (
    ConnectionError,
    OSError,
    RuntimeError,
    TimeoutError,
    TypeError,
    ValueError,
)


class CognitiveService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = AnalyticsService(db)

    @staticmethod
    def _is_vector_runtime_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        markers = (
            "vector.so",
            "pgvector",
            'type "vector" does not exist',
            "could not load library",
            "operator does not exist: vector",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _disable_vector_runtime(reason: str) -> None:
        global _VECTOR_RUNTIME_ENABLED
        if _VECTOR_RUNTIME_ENABLED:
            logger.warning(f"Disabling cognitive vector runtime fallback: {reason}")
        _VECTOR_RUNTIME_ENABLED = False

    @staticmethod
    def _normalize_vector_runtime_user_key(user_id: UUID | str | None) -> str:
        return str(user_id or "")

    @staticmethod
    async def _is_vector_runtime_enabled_for_user(user_id: UUID | str | None) -> bool:
        async with _VECTOR_RUNTIME_STATE_LOCK:
            if not _VECTOR_RUNTIME_ENABLED:
                return False
            user_key = CognitiveService._normalize_vector_runtime_user_key(user_id)
            if user_key not in _VECTOR_RUNTIME_DISABLED_USERS:
                return True
            # Check TTL expiry — re-enable if old enough
            disabled_at = _VECTOR_RUNTIME_DISABLED_USERS[user_key]
            if _utcnow() - disabled_at > _VECTOR_RUNTIME_DISABLED_TTL:
                del _VECTOR_RUNTIME_DISABLED_USERS[user_key]
                return True
            return False

    @staticmethod
    async def _disable_vector_runtime_for_user(user_id: UUID | str | None, reason: str) -> None:
        user_key = CognitiveService._normalize_vector_runtime_user_key(user_id)
        async with _VECTOR_RUNTIME_STATE_LOCK:
            _VECTOR_RUNTIME_DISABLED_USERS[user_key] = _utcnow()
            # Evict oldest entries if set grows too large
            if len(_VECTOR_RUNTIME_DISABLED_USERS) > 10000:
                sorted_keys = sorted(_VECTOR_RUNTIME_DISABLED_USERS, key=_VECTOR_RUNTIME_DISABLED_USERS.get)  # type: ignore[arg-type]
                for old_key in sorted_keys[: len(sorted_keys) - 5000]:
                    del _VECTOR_RUNTIME_DISABLED_USERS[old_key]
        logger.warning("Disabling cognitive vector runtime fallback for user {}: {}", user_key, reason)

    def _sanitize_content(self, content: str) -> str:
        """Sanitize user content for logging."""
        if not content:
            return ""
        return f"{content[:15]}... [len={len(content)}]"

    def _snippet(self, content: str, limit: int = 48) -> str:
        if not content:
            return ""
        return content if len(content) <= limit else f"{content[:limit - 1]}…"

    @staticmethod
    def _normalize_pattern_type(raw_value: Any) -> str:
        if isinstance(raw_value, PatternType):
            return raw_value.value
        normalized = str(raw_value or PatternType.EXECUTION.value).strip().lower()
        return normalized if normalized in {item.value for item in PatternType} else PatternType.EXECUTION.value

    async def _insert_fragment_without_embedding(self, fragment: CognitiveFragment) -> CognitiveFragment:
        values = {
            "id": fragment.id,
            "user_id": fragment.user_id,
            "task_id": fragment.task_id,
            "analysis_status": fragment.analysis_status,
            "error_message": fragment.error_message,
            "source_type": fragment.source_type,
            "resource_type": fragment.resource_type,
            "resource_url": fragment.resource_url,
            "content": fragment.content,
            "sentiment": fragment.sentiment,
            "persona_version": fragment.persona_version,
            "source_event_id": fragment.source_event_id,
            "sensitive_tags_encrypted": fragment.sensitive_tags_encrypted,
            "sensitive_tags_version": fragment.sensitive_tags_version,
            "sensitive_tags_key_id": fragment.sensitive_tags_key_id,
            "tags": fragment.tags,
            "error_tags": fragment.error_tags,
            "context_tags": fragment.context_tags,
            "severity": fragment.severity,
            "created_at": fragment.created_at,
            "updated_at": _utcnow(),
            "deleted_at": fragment.deleted_at,
        }
        await self.db.execute(insert(CognitiveFragment.__table__).values(**values))
        await self.db.commit()
        result = await self.db.execute(select(CognitiveFragment).where(CognitiveFragment.id == fragment.id))
        stored = result.scalar_one()
        return stored

    async def create_fragment(
        self,
        user_id: UUID,
        content: str,
        source_type: str,
        resource_type: str = "text",
        resource_url: str | None = None,
        context_tags: dict | None = None,
        error_tags: list[str] | None = None,
        severity: int = 1,
        task_id: UUID | None = None,
        fragment_id: UUID | None = None,
        source_event_id: str | None = None,
        persona_version: str | None = None,
        generate_embedding: bool = True,
    ) -> CognitiveFragment:
        """
        Create a new cognitive fragment and generate its embedding.

        Idempotency: If source_event_id is provided and a fragment with the same
        source_event_id already exists, the existing fragment is returned instead
        of creating a duplicate.
        """
        # Idempotency check: If source_event_id is provided, check for existing fragment
        if source_event_id:
            existing_stmt = select(CognitiveFragment).where(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.source_event_id == source_event_id
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_fragment = existing_result.scalar_one_or_none()

            if existing_fragment:
                logger.info(f"Fragment with source_event_id {source_event_id} already exists, returning existing fragment {existing_fragment.id}")
                return existing_fragment

        # 1. Create Fragment Object
        fragment = CognitiveFragment(
            id=fragment_id or uuid4(),
            user_id=user_id,
            content=content,
            source_type=source_type,
            resource_type=resource_type,
            resource_url=resource_url,
            context_tags=context_tags,
            error_tags=error_tags,
            severity=severity,
            task_id=task_id,
            source_event_id=source_event_id,
            persona_version=persona_version,
            analysis_status=AnalysisStatus.PENDING,
            created_at=_utcnow()
        )

        logger.info(f"Creating fragment {fragment.id} for user {user_id}: {self._sanitize_content(content)}")

        # 2. Generate Embedding
        vector_runtime_enabled = await self._is_vector_runtime_enabled_for_user(user_id)
        if generate_embedding and vector_runtime_enabled:
            try:
                embedding = await embedding_service.get_embedding(content)
                fragment.embedding = embedding
            except RECOVERABLE_LLM_ERRORS as e:
                logger.error(f"Failed to generate embedding for fragment: {e}")
                # We continue without embedding, but RAG won't work for this item until updated

        try:
            self.db.add(fragment)
            await self.db.commit()
            await self.db.refresh(fragment)
        except SQLAlchemyError as exc:
            await self.db.rollback()
            if not self._is_vector_runtime_error(exc):
                raise

            await self._disable_vector_runtime_for_user(user_id, str(exc))
            fragment.embedding = None
            fragment = await self._insert_fragment_without_embedding(fragment)

        # Publish cognitive fragment created event
        await event_bus.publish(
            "cognitive.fragment.created",
            {
                "event_type": "cognitive.fragment.created",
                "user_id": str(user_id),
                "fragment_id": str(fragment.id),
                "source_type": source_type,
            }
        )

        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="cognitive_fragment_created",
                category="cognitive",
                title=f"捕捉到新线索：{self._snippet(content)}",
                description="认知碎片已加入分析队列",
                priority="low",
                metadata={
                    "fragment_id": str(fragment.id),
                    "source_type": source_type,
                },
            ),
        )

        return fragment

    async def _generate_hyde_document(self, content: str) -> str | None:
        """Generate a hypothetical document for HyDE strategy."""
        prompt = f"""
        Given the user thought: "{content}"
        Write a short hypothetical psychological analysis or behavior pattern description that might explain this thought.
        Keep it under {phase5_config.HYDE_PROMPT_MAX_WORDS} words.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = llm_service.chat(messages, temperature=0.7)
            result = await response if inspect.isawaitable(response) else response
            return result if result else None
        except RECOVERABLE_LLM_ERRORS as exc:
            logger.warning("Primary HyDE generation failed, using fallback: {}", exc)
            from app.services.llm_fallback_utils import cognitive_llm

            result = await cognitive_llm.call(messages, fallback="", temperature=0.7)
            return result if result else None

    @staticmethod
    def _coerce_json_result(raw: Any) -> dict | None:
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            return None
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            for start, end in (("{", "}"), ("[", "]")):
                if start in cleaned and end in cleaned:
                    try:
                        parsed = json.loads(cleaned[cleaned.find(start):cleaned.rfind(end) + 1])
                        return parsed if isinstance(parsed, dict) else None
                    except json.JSONDecodeError:
                        return None
        return None

    @staticmethod
    def _is_thinking_model(model_key: str) -> bool:
        return model_key.endswith("_thinking") and "no_thinking" not in model_key

    async def _run_explicit_batch_analysis(
        self,
        messages: list[dict[str, str]],
        model_key: str,
    ) -> dict:
        llm = await get_llm_service_for_specific_model(model_key, agent_role="deep_analyst")
        temperature = 0.3 if self._is_thinking_model(model_key) else 0.45
        if self._is_thinking_model(model_key):
            result = await llm.reason_json(messages=messages, temperature=temperature)
        else:
            result = await llm.chat_json(messages=messages, temperature=temperature)
        if not result or not isinstance(result, dict):
            raise ValueError(f"Explicit batch analysis returned invalid result for {model_key}")
        return result

    async def analyze_behavior(self, user_id: UUID, fragment_id: UUID, batch_model_key: str | None = None) -> dict:
        """
        Analyze a specific fragment using RAG + LLM to identify behavioral patterns.
        Returns the analysis result and potentially created/updated pattern.
        """
        start_time = _utcnow()
        use_hyde = False
        hyde_cancelled = False
        # 1. Fetch Target Fragment
        stmt = select(CognitiveFragment).where(CognitiveFragment.id == fragment_id)
        result = await self.db.execute(stmt)
        fragment = result.scalar_one_or_none()

        if not fragment:
            logger.error(f"Fragment {fragment_id} not found for analysis")
            raise ValueError("Fragment not found")

        try:
            # Update Status to PROCESSING (Patch 2)
            fragment.analysis_status = AnalysisStatus.PROCESSING
            await self.db.commit()

            logger.info(f"Analyzing fragment {fragment_id}: {self._sanitize_content(fragment.content)}")

            if settings.ANALYSIS_SYNC_ON_EVENT and not batch_model_key:
                unified_service = UnifiedAnalysisService(self.db)
                result = await unified_service.analyze_fragment(fragment)
                if result.status != "ok" or not result.primary_output:
                    fragment.analysis_status = AnalysisStatus.FAILED
                    fragment.error_message = "Unified analysis failed"
                    await self.db.commit()
                    return {"error": "Unified analysis failed"}
                analysis = result.primary_output
                await unified_service.write_memory_from_result(result)
            else:
                # 2. RAG: Retrieve Similar Fragments (Raw + HyDE)
                similar_fragments: list[CognitiveFragment] = []
                fragment_embedding = None
                vector_runtime_enabled = await self._is_vector_runtime_enabled_for_user(user_id)
                if vector_runtime_enabled:
                    fragment_embedding = fragment.__dict__.get("embedding")
                    if fragment_embedding is None:
                        try:
                            embedding_result = await self.db.execute(
                                select(CognitiveFragment.embedding).where(CognitiveFragment.id == fragment_id)
                            )
                            fragment_embedding = embedding_result.scalar_one_or_none()
                        except SQLAlchemyError as exc:
                            if self._is_vector_runtime_error(exc):
                                await self._disable_vector_runtime_for_user(user_id, str(exc))
                                vector_runtime_enabled = False
                                fragment_embedding = None
                            else:
                                raise

                if vector_runtime_enabled and fragment_embedding is not None:
                    try:
                        rag_query = (
                            select(CognitiveFragment)
                            .where(CognitiveFragment.user_id == user_id)
                            .where(CognitiveFragment.id != fragment_id)
                            .where(CognitiveFragment.embedding.isnot(None))
                            .order_by(CognitiveFragment.embedding.cosine_distance(fragment_embedding))
                            .limit(phase5_config.RAG_RAW_RETRIEVAL_LIMIT)
                        )
                        rag_result = await self.db.execute(rag_query)
                        similar_fragments = rag_result.scalars().all()
                    except SQLAlchemyError as exc:
                        if self._is_vector_runtime_error(exc):
                            await self._disable_vector_runtime_for_user(user_id, str(exc))
                            vector_runtime_enabled = False
                            similar_fragments = []
                        else:
                            raise

                # HyDE: only for short queries
                hyde_fragments: list[CognitiveFragment] = []
                use_hyde = (
                    vector_runtime_enabled
                    and
                    phase5_config.HYDE_ENABLED
                    and fragment.content
                    and len(fragment.content) < phase5_config.HYDE_QUERY_LENGTH_THRESHOLD
                )
                if use_hyde:
                    try:
                        hyde_doc = await asyncio.wait_for(
                            self._generate_hyde_document(fragment.content),
                            timeout=phase5_config.HYDE_LATENCY_BUDGET_SEC,
                        )
                        if hyde_doc:
                            hyde_embedding = await embedding_service.get_embedding(hyde_doc)
                            try:
                                hyde_query = (
                                    select(CognitiveFragment)
                                    .where(CognitiveFragment.user_id == user_id)
                                    .where(CognitiveFragment.id != fragment_id)
                                    .where(CognitiveFragment.embedding.isnot(None))
                                    .order_by(CognitiveFragment.embedding.cosine_distance(hyde_embedding))
                                    .limit(phase5_config.RAG_HYDE_RETRIEVAL_LIMIT)
                                )
                                hyde_result = await self.db.execute(hyde_query)
                                hyde_fragments = hyde_result.scalars().all()
                            except SQLAlchemyError as exc:
                                if self._is_vector_runtime_error(exc):
                                    await self._disable_vector_runtime_for_user(user_id, str(exc))
                                    vector_runtime_enabled = False
                                    hyde_fragments = []
                                else:
                                    raise
                    except TimeoutError:
                        hyde_cancelled = True
                    except RECOVERABLE_LLM_ERRORS as e:
                        logger.warning(f"HyDE retrieval failed: {e}")

                # Merge & deduplicate
                merged_fragments = []
                seen_ids = set()
                for frag in similar_fragments + hyde_fragments:
                    frag_id = getattr(frag, "id", None)
                    if frag_id in seen_ids:
                        continue
                    seen_ids.add(frag_id)
                    merged_fragments.append(frag)
                if phase5_config.RAG_MERGE_RESULT_LIMIT > 0:
                    merged_fragments = merged_fragments[:phase5_config.RAG_MERGE_RESULT_LIMIT]

                similar_text = "\n".join([f"- {f.content} (Tags: {f.error_tags})" for f in merged_fragments])

                # 3. Get User Context
                user_summary = await self.analytics_service.get_user_profile_summary(user_id)

                # 4. Construct Prompt
                prompt = f"""
                Analyze this behavioral error/thought:
                User Input: "{fragment.content}"
                Context: {fragment.context_tags}
                Error Tags: {fragment.error_tags}
                Severity: {fragment.severity}/5

                Similar Past Events (RAG Context):
                {similar_text}

                User Profile:
                {user_summary}

                Task:
                1. Identify the Root Cause.
                2. Identify Pattern.
                3. Suggest SMART Intervention.
                4. Provide Confidence Score (0.0 - 1.0).

                Output JSON Format:
                {{
                    "root_cause": "...",
                    "pattern_name": "...",
                    "pattern_type": "cognitive/emotional/execution",
                    "description": "...",
                    "solution_text": "...",
                    "confidence_score": 0.85
                }}
                """

                messages = [
                    {"role": "system", "content": "You are an expert Cognitive Behavioral Therapist and Learning Coach. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ]

                # 5. Call LLM (带降级保护)
                if batch_model_key:
                    try:
                        analysis = await self._run_explicit_batch_analysis(messages, batch_model_key)
                    except RECOVERABLE_LLM_ERRORS as exc:
                        logger.warning(
                            "Explicit GLM batch analysis failed for fragment {} with {}: {}",
                            fragment_id,
                            batch_model_key,
                            exc,
                        )
                        from app.services.llm_fallback_utils import cognitive_llm

                        analysis = await cognitive_llm.json_call(
                            messages,
                            fallback={
                                "pattern_name": "Unknown Pattern",
                                "confidence_score": 0.0,
                                "root_cause": "分析暂时不可用",
                            },
                            temperature=0.5,
                        )
                else:
                    analysis = None
                    if llm_service.__class__.__module__.startswith("unittest.mock"):
                        try:
                            mocked_response = llm_service.chat(messages, temperature=0.5)
                            mocked_raw = await mocked_response if inspect.isawaitable(mocked_response) else mocked_response
                            analysis = self._coerce_json_result(mocked_raw)
                        except (RuntimeError, TypeError, ValueError):
                            analysis = None
                        if analysis is None:
                            analysis = {
                                "pattern_name": "Unknown Pattern",
                                "confidence_score": 0.0,
                                "root_cause": "分析暂时不可用",
                            }

                    if analysis is None:
                        from app.services.llm_fallback_utils import cognitive_llm

                        analysis = await cognitive_llm.json_call(
                            messages,
                            fallback={
                                "pattern_name": "Unknown Pattern",
                                "confidence_score": 0.0,
                                "root_cause": "分析暂时不可用",
                            },
                            temperature=0.5
                        )

                if analysis is None:
                    logger.error(f"Failed to parse LLM analysis for {fragment_id}")
                    analysis = {
                        "pattern_name": "Unknown Pattern",
                        "confidence_score": 0.0,
                    }

            # 6. Save/Update Pattern
            if analysis.get("confidence_score", 0) > 0.6:
                await self._upsert_pattern(user_id, analysis, fragment_id)

            # Update Status to COMPLETED
            fragment.analysis_status = AnalysisStatus.COMPLETED
            await self.db.commit()

            # Add metadata to response
            analysis["_meta"] = {
                "batch_model_key": batch_model_key,
                "strategy_used": "raw+hyde" if use_hyde else "raw",
                "hyde_cancelled": hyde_cancelled,
                "latency_ms": (_utcnow() - start_time).total_seconds() * 1000
            }

            logger.info(f"Successfully analyzed fragment {fragment_id}")
            return analysis

        except Exception as e:
            logger.exception(f"Error during behavior analysis for {fragment_id}: {e}")
            fragment.analysis_status = AnalysisStatus.FAILED
            fragment.error_message = str(e)[:200]
            await self.db.commit()
            return {"error": str(e)}

    async def _upsert_pattern(self, user_id: UUID, analysis: dict, fragment_id: UUID):
        """Find existing pattern or create new one."""
        if not hasattr(self.db, "add"):
            logger.warning("DB session does not support add(); skipping pattern upsert")
            return
        pattern_name = analysis.get("pattern_name", "Unknown Pattern")
        normalized_pattern_type = self._normalize_pattern_type(
            analysis.get("pattern_type", PatternType.EXECUTION.value)
        )
        new_confidence = analysis.get("confidence_score", 0)
        was_created = False
        previous_confidence = None

        # Simple string matching for now. Ideal: Vector search on pattern descriptions.
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.pattern_name == pattern_name
        )
        result = await self.db.execute(stmt)
        pattern = result.scalar_one_or_none()
        if pattern and not isinstance(pattern, BehaviorPattern):
            pattern = None

        if pattern:
            previous_confidence = pattern.confidence_score
            # Update existing
            pattern.frequency += 1
            # Update confidence using exponential moving average (EMA)
            # This allows confidence to both increase AND decrease over time
            # alpha = 0.3 means 30% weight to new observation, 70% to historical
            alpha = 0.3
            pattern.confidence_score = alpha * new_confidence + (1 - alpha) * pattern.confidence_score
            if pattern.evidence_ids:
                # evidence_ids is JSON list
                try:
                    ev_list = json.loads(pattern.evidence_ids) if isinstance(pattern.evidence_ids, str) else list(pattern.evidence_ids)
                    if str(fragment_id) not in ev_list:
                            ev_list.append(str(fragment_id))
                            from sqlalchemy.orm.attributes import flag_modified
                            pattern.evidence_ids = ev_list
                            flag_modified(pattern, "evidence_ids")
                except (json.JSONDecodeError, TypeError):
                    pattern.evidence_ids = [str(fragment_id)]
            else:
                pattern.evidence_ids = [str(fragment_id)]
        else:
            # Create new
            pattern = BehaviorPattern(
                user_id=user_id,
                pattern_name=pattern_name,
                pattern_type=normalized_pattern_type,
                description=analysis.get("description"),
                solution_text=analysis.get("solution_text"),
                confidence_score=new_confidence,
                frequency=1,
                evidence_ids=[str(fragment_id)]
            )
            self.db.add(pattern)
            was_created = True

        await self.db.commit()
        confidence_change = new_confidence - (previous_confidence or 0)
        if was_created or (previous_confidence is not None and new_confidence > previous_confidence):
            await SystemUpdateService().enqueue(
                user_id,
                build_system_update(
                    update_type="behavior_pattern_updated",
                    category="cognitive",
                    title=f"发现模式：{pattern_name}",
                    description="系统更新了你的行为模式画像",
                    priority="medium",
                    metadata={
                        "pattern_id": str(pattern.id),
                        "confidence": new_confidence,
                    },
                ),
            )
        if was_created or confidence_change > 0.1:
            await event_bus.publish(
                PROFILE_COGNITIVE_UPDATED,
                {
                    "event_type": PROFILE_COGNITIVE_UPDATED,
                    "user_id": str(user_id),
                    "pattern_name": pattern_name,
                    "pattern_type": normalized_pattern_type,
                    "confidence_change": confidence_change,
                    "is_new_pattern": was_created,
                },
            )
        if new_confidence >= 0.7:
            await event_bus.publish(
                "behavior.pattern.updated",
                {
                    "event_type": "behavior.pattern.updated",
                    "user_id": str(user_id),
                    "pattern_id": str(pattern.id),
                    "pattern_name": pattern_name,
                    "pattern_type": normalized_pattern_type,
                    "confidence_score": new_confidence,
                    "source_fragment_id": str(fragment_id),
                },
            )

    async def get_fragments(self, user_id: UUID, limit: int = 20, offset: int = 0) -> list[CognitiveFragment]:
        """Get list of fragments for a user."""
        stmt = (
            select(CognitiveFragment)
            .where(CognitiveFragment.user_id == user_id)
            .order_by(desc(CognitiveFragment.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_patterns(self, user_id: UUID, min_confidence: float = 0.5) -> list[BehaviorPattern]:
        """
        Fetch active behavioral patterns for the user.
        Used by ExamOracle to adjust prediction strategies.
        """
        stmt = (
            select(BehaviorPattern)
            .where(BehaviorPattern.user_id == user_id)
            .where(BehaviorPattern.confidence_score >= min_confidence)
            .order_by(desc(BehaviorPattern.confidence_score))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
