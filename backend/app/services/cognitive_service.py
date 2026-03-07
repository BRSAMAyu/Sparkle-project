import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.phase5_config import phase5_config
from app.core.event_bus import event_bus
from app.models.cognitive import AnalysisStatus, BehaviorPattern, CognitiveFragment
from app.services.analysis.unified_analysis_service import UnifiedAnalysisService
from app.services.analytics_service import AnalyticsService
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CognitiveService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = AnalyticsService(db)

    def _sanitize_content(self, content: str) -> str:
        """Sanitize user content for logging."""
        if not content:
            return ""
        return f"{content[:15]}... [len={len(content)}]"

    def _snippet(self, content: str, limit: int = 48) -> str:
        if not content:
            return ""
        return content if len(content) <= limit else f"{content[:limit - 1]}…"

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
        persona_version: str | None = None
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
        try:
            embedding = await embedding_service.get_embedding(content)
            fragment.embedding = embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for fragment: {e}")
            # We continue without embedding, but RAG won't work for this item until updated

        self.db.add(fragment)
        await self.db.commit()
        await self.db.refresh(fragment)
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
            return await llm_service.chat(messages, temperature=0.7)
        except Exception as e:
            logger.warning(f"HyDE generation failed: {e}")
            return None

    async def analyze_behavior(self, user_id: UUID, fragment_id: UUID) -> dict:
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

            if settings.ANALYSIS_SYNC_ON_EVENT:
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
                if fragment.embedding is not None:
                    rag_query = (
                        select(CognitiveFragment)
                        .where(CognitiveFragment.user_id == user_id)
                        .where(CognitiveFragment.id != fragment_id)
                        .where(CognitiveFragment.embedding.isnot(None))
                        .order_by(CognitiveFragment.embedding.cosine_distance(fragment.embedding))
                        .limit(phase5_config.RAG_RAW_RETRIEVAL_LIMIT)
                    )
                    rag_result = await self.db.execute(rag_query)
                    similar_fragments = rag_result.scalars().all()

                # HyDE: only for short queries
                hyde_fragments: list[CognitiveFragment] = []
                use_hyde = (
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
                    except asyncio.TimeoutError:
                        hyde_cancelled = True
                    except Exception as e:
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

                # 5. Call LLM
                response_text = await llm_service.chat(messages, temperature=0.5)

                try:
                    cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                    analysis = json.loads(cleaned_text)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse LLM analysis for {fragment_id}")
                    analysis = {
                        "pattern_name": "Unknown Pattern",
                        "confidence_score": 0.0,
                        "raw_text": response_text,
                    }

            # 6. Save/Update Pattern
            if analysis.get("confidence_score", 0) > 0.6:
                await self._upsert_pattern(user_id, analysis, fragment_id)

            # Update Status to COMPLETED
            fragment.analysis_status = AnalysisStatus.COMPLETED
            await self.db.commit()

            # Add metadata to response
            analysis["_meta"] = {
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
            # Update confidence (simple moving average-ish or max)
            pattern.confidence_score = max(pattern.confidence_score, new_confidence)
            if pattern.evidence_ids:
                # evidence_ids is JSON list
                try:
                    ev_list = json.loads(pattern.evidence_ids) if isinstance(pattern.evidence_ids, str) else pattern.evidence_ids
                    if str(fragment_id) not in ev_list:
                            ev_list.append(str(fragment_id))
                            pattern.evidence_ids = ev_list
                except:
                    pattern.evidence_ids = [str(fragment_id)]
            else:
                pattern.evidence_ids = [str(fragment_id)]
        else:
            # Create new
            pattern = BehaviorPattern(
                user_id=user_id,
                pattern_name=pattern_name,
                pattern_type=analysis.get("pattern_type", "execution"),
                description=analysis.get("description"),
                solution_text=analysis.get("solution_text"),
                confidence_score=new_confidence,
                frequency=1,
                evidence_ids=[str(fragment_id)]
            )
            self.db.add(pattern)
            was_created = True

        await self.db.commit()
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
        if new_confidence >= 0.7:
            await event_bus.publish(
                "behavior.pattern.updated",
                {
                    "event_type": "behavior.pattern.updated",
                    "user_id": str(user_id),
                    "pattern_id": str(pattern.id),
                    "pattern_name": pattern_name,
                    "pattern_type": analysis.get("pattern_type", "execution"),
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
