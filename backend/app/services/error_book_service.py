"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

错题档案服务层 - Phase 4 Optimized
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from datetime import timezone, datetime, timedelta
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import String, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.config import settings
from app.core.event_bus import ErrorCreated, event_bus
from app.core.llm_client import llm_client
from app.models.achievement import UserStreakStats
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.schemas.error_book import (
    ErrorQueryParams,
    ErrorRecordCreate,
    ErrorRecordUpdate,
    KnowledgeLinkBrief,
    ReviewAction,
    ReviewPerformanceEnum,
)
from app.schemas.semantic_memory import ConceptBrief, ErrorSemanticSummary, SimilarErrorItem, StrategyNodeResponse
from app.services.embedding_service import embedding_service
from app.services.memory_service import MemoryService
from app.services.ocr_service import ocr_service
from app.services.semantic_memory_service import SemanticMemoryService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


SPARKLE_FILE_REFERENCE_PREFIX = "sparkle-file://"


class ReviewSchedulerService:
    """
    复习计划调度服务
    SM-2 Algorithm with Fuzzing/Jitter to prevent review bombing.
    """

    MAX_EASINESS_FACTOR = 2.5

    def calculate_next_review(
        self,
        current_mastery: float,
        easiness_factor: float,
        interval_days: float,
        review_count: int,
        performance: ReviewPerformanceEnum,
    ) -> tuple[float, float, float, datetime]:
        """
        Returns: (new_mastery, new_ef, new_interval, next_review_date)
        """
        now = _utcnow()

        # SM-2 Logic
        # Quality: Forgotten=1, Fuzzy=3, Remembered=5 (simplified mapping)
        if performance == ReviewPerformanceEnum.REMEMBERED:
            quality = 5
        elif performance == ReviewPerformanceEnum.FUZZY:
            quality = 3
        else:  # Forgotten
            quality = 1

        # 1. Update Easiness Factor (EF)
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, min(new_ef, self.MAX_EASINESS_FACTOR))  # SM-2 EF bounded to prevent runaway intervals

        # 2. Update Interval
        if quality < 3:
            # Failed
            new_interval = 1.0
            review_count = 0  # Reset count or keep? SM-2 usually resets interval chain
        else:
            if review_count == 0:
                new_interval = 1.0
            elif review_count == 1:
                new_interval = 6.0
            else:
                new_interval = interval_days * new_ef

            review_count += 1

        # 3. Update Mastery (Simplified)
        if quality == 5:
            new_mastery = min(1.0, current_mastery + 0.15)
        elif quality == 3:
            new_mastery = max(0.0, current_mastery - 0.05)
        else:
            new_mastery = max(0.0, current_mastery - 0.2)

        # 4. Apply Jitter (Fuzzing) ±10%
        # Do not fuzz if interval is small (<= 1 day)
        if new_interval > 1.5:
            jitter = random.uniform(0.9, 1.1)
            final_interval = new_interval * jitter
        else:
            final_interval = new_interval

        next_review = now + timedelta(days=final_interval)

        return new_mastery, new_ef, final_interval, next_review


class ErrorBookService:
    """
    错题档案核心服务 (Phase 4)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.review_scheduler = ReviewSchedulerService()

    async def _flush_pending_mastery_events(self, results: list[dict]) -> None:
        """Publish deferred node mastery events after the surrounding DB commit succeeds."""
        for item in results or []:
            pending = item.get("_pending_event") or {}
            topic = pending.get("topic")
            payload = pending.get("payload")
            if not topic or not payload:
                continue
            try:
                await event_bus.publish(topic, payload)
            except Exception as exc:
                logger.warning(f"Failed to publish deferred mastery event: {exc}")

    @staticmethod
    def _coerce_uuid(value: object) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    def _primary_affected_node_id(self, error: ErrorRecord) -> UUID | None:
        affected_node_id = self._coerce_uuid(getattr(error, "affected_node_id", None))
        if affected_node_id:
            return affected_node_id

        linked_ids = getattr(error, "linked_knowledge_node_ids", None) or []
        if not linked_ids:
            return None
        return self._coerce_uuid(linked_ids[0])

    async def _attach_knowledge_links(self, records: list[ErrorRecord]) -> None:
        """Attach transient knowledge link summaries for API responses."""
        node_ids: set[UUID] = set()
        normalized_links_by_error: dict[UUID, list[UUID]] = {}

        for error in records:
            linked_ids = [
                node_id
                for node_id in (self._coerce_uuid(value) for value in (error.linked_knowledge_node_ids or []))
                if node_id is not None
            ]
            primary_id = self._primary_affected_node_id(error)
            if primary_id is not None and primary_id not in linked_ids:
                linked_ids.insert(0, primary_id)

            normalized_links_by_error[error.id] = linked_ids
            node_ids.update(linked_ids)

            # Backfill response-only primary node from legacy linked ids. This is intentionally
            # not committed here; the next write path will persist the column.
            if getattr(error, "affected_node_id", None) is None and primary_id is not None:
                set_committed_value(error, "affected_node_id", primary_id)

        if not node_ids:
            for error in records:
                error.knowledge_links = []
            return

        node_stmt = select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))
        nodes = (await self.db.execute(node_stmt)).scalars().all()
        node_names = {node.id: node.name for node in nodes}

        for error in records:
            primary_id = self._primary_affected_node_id(error)
            links: list[KnowledgeLinkBrief] = []
            for node_id in normalized_links_by_error.get(error.id, []):
                name = node_names.get(node_id)
                if not name:
                    continue
                links.append(
                    KnowledgeLinkBrief(
                        id=node_id,
                        name=name,
                        is_primary=primary_id == node_id,
                    )
                )
            error.knowledge_links = links

    async def create_error(self, user_id: UUID, data: ErrorRecordCreate) -> ErrorRecord:
        error = ErrorRecord(
            user_id=user_id,
            question_text=data.question_text,
            question_image_url=data.question_image_url,
            user_answer=data.user_answer,
            correct_answer=data.correct_answer,
            subject_code=data.subject.value,
            chapter=data.chapter,
            cognitive_tags=data.cognitive_tags,
            ai_analysis_summary=data.ai_analysis_summary,
            # Initial State
            next_review_at=_utcnow(),  # Immediate review or +1 day? Usually immediate for first learn.
            interval_days=0.0,
            easiness_factor=2.5,
            review_count=0,
            mastery_level=0.0,
        )

        self.db.add(error)
        await self.db.commit()
        await self.db.refresh(error)

        logger.info(f"Created error record {error.id} for user {user_id}")
        return error

    async def analyze_and_link(self, error_id: UUID, user_id: UUID):
        """
        Async Background Task:
        1. Check/Run OCR
        2. RAG Retrieval
        3. LLM Analysis
        4. Update DB
        """
        # Note: This runs in a background task, so we need to ensure the session is valid.
        # Ideally, the caller handles the session scope, or we use a fresh session here.
        # Assuming `self.db` is valid or using `AsyncSessionLocal` pattern in the worker wrapper.
        # Here we assume self.db is injected correctly (likely needing a fresh session if run in background).

        try:
            stmt = select(ErrorRecord).where(ErrorRecord.id == error_id)
            res = await self.db.execute(stmt)
            error = res.scalar_one_or_none()

            if not error:
                logger.error(f"Error {error_id} not found for analysis")
                return

            # --- Step 1: OCR / Text Check ---
            ocr_text = None
            final_text = error.question_text or ""

            if error.question_image_url and (not error.question_text or len(error.question_text) < 10):
                # Trigger OCR
                logger.info(f"Running OCR for error {error.id}")
                ocr_text = await self._run_ocr(error.question_image_url)
                if ocr_text:
                    final_text = f"{final_text}\n[OCR]: {ocr_text}".strip()
                    # Optionally update the record's text or just keep it for analysis context
                    # Let's save it in latest_analysis['ocr_text'] later.

            if not final_text:
                logger.warning("No text available for analysis")
                return

            # --- Step 2: RAG Retrieval ---
            linked_ids = []
            nodes: list[KnowledgeNode] = []

            try:
                # Retrieve relevant knowledge nodes
                nodes = await self._search_knowledge_nodes(user_id, final_text)
                if nodes:
                    linked_ids = [n.id for n in nodes]
                    logger.info(f"Found {len(linked_ids)} linked nodes for error {error.id}")
                else:
                    logger.info("No relevant nodes found (Cold Start), asking LLM for suggestions")
            except Exception as e:
                logger.error(f"RAG search failed: {e}")
                # Continue without links

            # --- Step 3: LLM Analysis ---
            analysis_result = await self._run_llm_analysis(
                subject=error.subject_code,
                question=final_text,
                user_ans=error.user_answer,
                correct_ans=error.correct_answer,
                linked_nodes=nodes if "nodes" in locals() and nodes else [],
            )

            if ocr_text:
                analysis_result["ocr_text"] = ocr_text

            # Extract suggested concepts if any (from LLM or fallback)
            # Currently strict JSON schema doesn't have 'suggested_concepts' in top level,
            # but we can add it to the DB column.

            # --- Step 4: Update DB ---
            error.latest_analysis = analysis_result
            error.linked_knowledge_node_ids = linked_ids
            error.affected_node_id = linked_ids[0] if linked_ids else None
            # error.suggested_concepts = ... (if LLM returns them)

            # 先落库核心分析结果，保证前端/验收链能尽快读取 latest_analysis。
            # 后续语义记忆、画像信号和事件总线即使稍慢，也不再阻塞“分析已完成”的主链路。
            if not error.question_text and ocr_text:
                error.question_text = ocr_text

            await self.db.commit()
            logger.info(f"Analysis core result committed for error {error.id}")

            try:
                async with self.db.begin_nested():
                    semantic_service = SemanticMemoryService(self.db)
                    await semantic_service.upsert_strategy_from_error(error)
                await self.db.commit()
            except Exception as e:
                logger.warning(f"Semantic memory linking failed: {e}")
                await self.db.rollback()

            logger.info(f"Analysis completed for error {error.id}")

            try:
                await self._write_error_analysis_memory(error=error, linked_nodes=nodes)
            except Exception as e:
                logger.warning(f"Error analysis episodic memory write failed: {e}")

            try:
                from app.services.error_book_signal_processor import ErrorBookSignalProcessor

                processor = ErrorBookSignalProcessor(self.db)
                await processor.process_error_created(user_id)
            except Exception as e:
                logger.warning(f"Error book preference sync failed: {e}")

            # --- Mastery sync: error diagnosis → knowledge node mastery ---
            try:
                from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

                mastery_sync = ErrorBookMasterySyncService(self.db)
                mastery_results = await mastery_sync.apply_error_diagnosis(user_id, error)
                if mastery_results:
                    primary_result = mastery_results[0]
                    error.affected_node_id = self._coerce_uuid(primary_result.get("node_id")) or error.affected_node_id
                    error.mastery_delta = float(primary_result.get("delta") or 0.0)
                await self.db.commit()
                await self._flush_pending_mastery_events(mastery_results)
            except Exception as e:
                logger.warning(f"Error book mastery sync (diagnosis) failed: {e}")

            # Publish Error Created Event
            try:
                event = ErrorCreated(
                    user_id=str(user_id), error_id=str(error.id), linked_node_ids=[str(i) for i in linked_ids]
                )
                await event_bus.publish(event.to_dict()["event_type"], event.to_dict())
            except Exception as e:
                logger.error(f"Failed to publish ErrorCreated event: {e}")

        except Exception as e:
            logger.error(f"Async analysis failed for error {error_id}: {e}")
            await self.db.rollback()

    async def _write_error_analysis_memory(
        self,
        *,
        error: ErrorRecord,
        linked_nodes: list[KnowledgeNode],
    ) -> None:
        from app.models.memory import EpisodicMemory

        existing = await self.db.execute(
            select(EpisodicMemory.id).where(
                EpisodicMemory.user_id == error.user_id,
                EpisodicMemory.source_type == "error_analysis",
                EpisodicMemory.source_id == str(error.id),
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none() is not None:
            return

        analysis = error.latest_analysis or {}
        error_type = str(analysis.get("error_type_label") or analysis.get("error_type") or "错题").strip()
        primary_node = linked_nodes[0].name if linked_nodes else ""
        focus_label = primary_node or str(error.chapter or error.subject_code or "当前知识点").strip()
        occurred_label = (error.created_at or _utcnow()).strftime("%Y-%m-%d")
        summary = f"{occurred_label} 在 {focus_label} 上出现了{error_type}"

        root_cause = str(analysis.get("root_cause") or "").strip()
        if root_cause:
            summary = f"{summary}：{root_cause[:120]}"

        memory_service = MemoryService(self.db)
        await memory_service.create_episodic_memory(
            user_id=error.user_id,
            summary=summary,
            source_type="error_analysis",
            source_id=str(error.id),
            occurred_at=error.created_at or _utcnow(),
            importance_score=0.75,
            tags=[tag for tag in [str(error.subject_code or "").strip(), error_type] if tag],
            evidence_refs=[
                {"type": "error", "id": str(error.id), "schema_version": "error.v1"},
                *(
                    [{"type": "concept", "id": str(linked_nodes[0].id), "schema_version": "concept.v1"}]
                    if linked_nodes
                    else []
                ),
            ],
        )

    async def _run_ocr(self, image_url: str) -> str:
        """使用 GLM OCR 进行图片文字识别。"""
        try:
            resolved_image_url = await self._resolve_question_image_url(image_url)
            if not resolved_image_url:
                return ""
            text = await ocr_service.ocr_for_math(resolved_image_url)
            return text
        except Exception as e:
            logger.error(f"OCR failed for image {image_url}: {e}")
            return ""

    async def _resolve_question_image_url(self, image_url: str) -> str:
        if not image_url.startswith(SPARKLE_FILE_REFERENCE_PREFIX):
            return image_url

        file_id = image_url.removeprefix(SPARKLE_FILE_REFERENCE_PREFIX).strip()
        if not file_id:
            return ""

        gateway_url = (settings.GATEWAY_URL or "").rstrip("/")
        if not gateway_url:
            logger.warning("Cannot resolve sparkle-file image without GATEWAY_URL")
            return ""
        if not settings.INTERNAL_API_KEY:
            logger.warning("Cannot resolve sparkle-file image without INTERNAL_API_KEY")
            return ""

        headers: dict[str, str] = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{gateway_url}/internal/files/{file_id}/download",
                    headers=headers,
                )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("download_url") or "")
        except Exception as exc:
            logger.warning(f"Failed to resolve sparkle-file image {file_id}: {exc}")
            return ""

    async def _search_knowledge_nodes(self, user_id: UUID, text: str, limit: int = 3) -> list[KnowledgeNode]:
        try:
            async with self.db.begin_nested():
                embedding = await embedding_service.get_embedding(text, text_type="query")
                stmt = (
                    select(KnowledgeNode)
                    .outerjoin(
                        UserNodeStatus,
                        and_(
                            UserNodeStatus.node_id == KnowledgeNode.id,
                            UserNodeStatus.user_id == user_id,
                        ),
                    )
                    .where(
                        KnowledgeNode.not_deleted_filter(),
                        or_(
                            KnowledgeNode.is_seed,
                            UserNodeStatus.user_id.isnot(None),
                        ),
                    )
                    .order_by(KnowledgeNode.embedding.l2_distance(embedding))
                    .limit(limit)
                )

                result = await self.db.execute(stmt)
                return result.scalars().all()
        except Exception as exc:
            logger.warning(f"Knowledge node vector search failed, falling back to keyword search: {exc}")
            return await self._keyword_search_knowledge_nodes(user_id, text, limit=limit)

    async def _keyword_search_knowledge_nodes(self, user_id: UUID, text: str, limit: int = 3) -> list[KnowledgeNode]:
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        keywords = [
            token for token in re.split(r"[\s,，。！？；;:：/\\\\()\\[\\]{}]+", cleaned_text) if len(token) >= 2
        ][:6]
        if not keywords:
            keywords = [cleaned_text[:40]]

        conditions = []
        for keyword in keywords:
            like = f"%{keyword}%"
            conditions.append(KnowledgeNode.name.ilike(like))
            conditions.append(KnowledgeNode.description.ilike(like))

        stmt = (
            select(KnowledgeNode)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id,
                ),
            )
            .where(
                KnowledgeNode.not_deleted_filter(),
                or_(
                    KnowledgeNode.is_seed,
                    UserNodeStatus.user_id.isnot(None),
                ),
                or_(*conditions),
            )
            .order_by(KnowledgeNode.is_seed.desc(), KnowledgeNode.updated_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _run_llm_analysis(self, subject, question, user_ans, correct_ans, linked_nodes) -> dict:
        node_context = ", ".join([n.name for n in linked_nodes])

        prompt = f"""
        Analyze this {subject} error.
        Question: {question}
        Student Answer: {user_ans}
        Correct Answer: {correct_ans}
        Related Concepts: {node_context}

        Provide output in JSON:
        {{
            "error_type": "concept_confusion" | "calculation_error" | "reading_careless" | "knowledge_gap" | "method_wrong" | "logic_error" | "other",
            "error_type_label": "Short Chinese Label",
            "root_cause": "Detailed analysis...",
            "correct_approach": "Step-by-step approach...",
            "similar_traps": ["Trap 1", "Trap 2"],
            "recommended_knowledge": ["Concept 1", "Concept 2"],
            "study_suggestion": "Actionable advice..."
        }}
        """

        try:
            response = await asyncio.wait_for(
                llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are an expert tutor."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=700,
                ),
                timeout=12.0,
            )
            # Parse JSON
            if isinstance(response, str):
                import re

                json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
                content = json_match.group(1) if json_match else response
                return json.loads(content)
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._build_fallback_analysis(
                question=question,
                user_ans=user_ans,
                correct_ans=correct_ans,
                linked_nodes=linked_nodes,
            )

    def _build_fallback_analysis(self, question, user_ans, correct_ans, linked_nodes) -> dict:
        question_text = (question or "").strip()
        user_text = (user_ans or "").strip()
        correct_text = (correct_ans or "").strip()
        related_concepts = [node.name for node in linked_nodes[:3] if getattr(node, "name", None)]

        combined_text = f"{question_text}\n{user_text}\n{correct_text}".lower()
        if any(keyword in combined_text for keyword in ["指针", "pointer", "*p", "地址", "内存"]):
            error_type = "concept_confusion"
            error_type_label = "概念混淆"
        elif any(keyword in combined_text for keyword in ["计算", "算错", "结果", "公式"]):
            error_type = "calculation_error"
            error_type_label = "计算失误"
        else:
            error_type = "knowledge_gap"
            error_type_label = "知识缺口"

        root_cause = (
            f"从题干与作答来看，当前错误更像是{error_type_label}。"
            f"学生回答“{user_text or '未填写'}”与正确表达“{correct_text or '未提供'}”之间存在关键概念错位。"
        )
        correct_approach = (
            f"先用自己的话复述题目核心概念，再明确区分“{correct_text or '正确答案中的关键定义'}”"
            "与常见混淆点，最后用一个最小例子重新验证。"
        )
        similar_traps = [
            "把符号本身和它表示的对象混为一谈",
            "没有先确认概念定义就直接代入理解",
        ]
        recommended_knowledge = related_concepts or ["核心概念定义", "易混点辨析"]
        study_suggestion = (
            "先把这道题压缩成一张两列表：左边写错误理解，右边写正确解释；"
            "随后再做一道同类型变式题，确认自己能稳定说清差异。"
        )
        return {
            "error_type": error_type,
            "error_type_label": error_type_label,
            "root_cause": root_cause,
            "correct_approach": correct_approach,
            "similar_traps": similar_traps,
            "recommended_knowledge": recommended_knowledge,
            "study_suggestion": study_suggestion,
        }

    async def get_error(self, error_id: UUID, user_id: UUID) -> ErrorRecord | None:
        stmt = select(ErrorRecord).where(
            and_(ErrorRecord.id == error_id, ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            await self._attach_knowledge_links([record])

        return record

    async def get_semantic_summary(self, error_id: UUID, user_id: UUID) -> ErrorSemanticSummary | None:
        error = await self.get_error(error_id, user_id)
        if not error:
            return None

        semantic_service = SemanticMemoryService(self.db)
        strategies = await semantic_service.get_strategies_for_error(error_id, user_id)
        similar_errors = await semantic_service.get_same_cause_errors(error_id, user_id, limit=5)

        concepts: list[ConceptBrief] = []
        if error.linked_knowledge_node_ids:
            result = await self.db.execute(
                select(KnowledgeNode).where(KnowledgeNode.id.in_(error.linked_knowledge_node_ids))
            )
            nodes = result.scalars().all()
            concepts = [ConceptBrief(id=node.id, name=node.name, description=node.description) for node in nodes]

        root_cause = (error.latest_analysis or {}).get("root_cause") if error.latest_analysis else None
        return ErrorSemanticSummary(
            error_id=error.id,
            root_cause=root_cause,
            linked_concepts=concepts,
            strategies=[
                StrategyNodeResponse(
                    id=strategy.id,
                    title=strategy.title,
                    description=strategy.description,
                    subject_code=strategy.subject_code,
                    tags=strategy.tags,
                    created_at=strategy.created_at,
                )
                for strategy in strategies
            ],
            similar_errors=[
                SimilarErrorItem(
                    id=item.id,
                    subject_code=item.subject_code,
                    root_cause=(item.latest_analysis or {}).get("root_cause"),
                    created_at=item.created_at,
                )
                for item in similar_errors
            ],
            metadata={"strategy_count": len(strategies), "similar_error_count": len(similar_errors)},
        )

    async def list_errors(self, user_id: UUID, params: ErrorQueryParams) -> tuple[list[ErrorRecord], int]:
        query = select(ErrorRecord).where(and_(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False)))

        if params.subject:
            query = query.where(ErrorRecord.subject_code == params.subject.value)
        if params.chapter:
            query = query.where(ErrorRecord.chapter.ilike(f"%{params.chapter}%"))
        if params.node_id:
            node_id_text = params.node_id.strip()
            node_uuid = self._coerce_uuid(node_id_text)
            if node_uuid is not None:
                query = query.where(
                    or_(
                        ErrorRecord.affected_node_id == node_uuid,
                        ErrorRecord.linked_knowledge_node_ids.contains([node_uuid]),
                    )
                )
            else:
                query = query.where(
                    or_(
                        ErrorRecord.question_text.ilike(f"%{node_id_text}%"),
                        ErrorRecord.ai_analysis_summary.ilike(f"%{node_id_text}%"),
                        func.cast(ErrorRecord.latest_analysis, String).ilike(f"%{node_id_text}%"),
                    )
                )
        if params.error_type:
            query = query.where(ErrorRecord.latest_analysis["error_type"].astext == params.error_type.value)
        if params.mastery_min is not None:
            query = query.where(ErrorRecord.mastery_level >= params.mastery_min)
        if params.mastery_max is not None:
            query = query.where(ErrorRecord.mastery_level <= params.mastery_max)
        if params.need_review:
            query = query.where(ErrorRecord.next_review_at <= _utcnow())
        if params.cognitive_dimension:
            # Filter where cognitive_tags contains the dimension
            query = query.where(ErrorRecord.cognitive_tags.contains([params.cognitive_dimension]))
        if params.keyword:
            # Search in text or analysis or OCR
            query = query.where(
                or_(
                    ErrorRecord.question_text.ilike(f"%{params.keyword}%"),
                    func.cast(ErrorRecord.latest_analysis, String).ilike(f"%{params.keyword}%"),
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Order
        query = (
            query.order_by(ErrorRecord.next_review_at.asc().nullslast(), ErrorRecord.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        await self._attach_knowledge_links(items)

        return items, total

    async def update_error(self, error_id: UUID, user_id: UUID, data: ErrorRecordUpdate) -> ErrorRecord | None:
        error = await self.get_error(error_id, user_id)
        if not error:
            return None

        update_data = data.dict(exclude_unset=True)
        # Rename subject to subject_code if present
        if "subject" in update_data:
            update_data["subject_code"] = update_data.pop("subject").value

        for key, value in update_data.items():
            if hasattr(error, key):
                setattr(error, key, value)

        await self.db.commit()
        await self.db.refresh(error)
        return error

    async def delete_error(self, error_id: UUID, user_id: UUID) -> bool:
        stmt = select(ErrorRecord).where(and_(ErrorRecord.id == error_id, ErrorRecord.user_id == user_id))
        result = await self.db.execute(stmt)
        error = result.scalar_one_or_none()

        if not error:
            return False

        error.is_deleted = True
        await self.db.commit()
        return True

    async def submit_review(self, user_id: UUID, error_id: UUID, data: ReviewAction) -> ErrorRecord:
        error = await self.get_error(error_id, user_id)
        if not error:
            raise ValueError(f"Error {error_id} not found")

        previous_mastery = error.mastery_level or 0.0

        # Calculate new schedule
        new_mastery, new_ef, new_interval, next_review = self.review_scheduler.calculate_next_review(
            current_mastery=error.mastery_level or 0.0,
            easiness_factor=error.easiness_factor or 2.5,
            interval_days=error.interval_days or 0.0,
            review_count=error.review_count or 0,
            performance=data.performance,
        )

        # Update Record
        error.mastery_level = new_mastery
        error.easiness_factor = new_ef
        error.interval_days = new_interval
        error.next_review_at = next_review
        error.review_count = (error.review_count or 0) + 1
        error.last_reviewed_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(error)

        try:
            await self._store_practice_outcome_memory(
                user_id=user_id,
                error=error,
                performance=data.performance,
                previous_mastery=previous_mastery,
            )
        except Exception as e:
            logger.warning(f"Practice outcome memory write failed after review: {e}")

        try:
            from app.services.error_book_signal_processor import ErrorBookSignalProcessor

            processor = ErrorBookSignalProcessor(self.db)
            await processor.process_error_created(user_id)
        except Exception as e:
            logger.warning(f"Error book preference refresh after review failed: {e}")

        # --- Mastery sync: review feedback → knowledge node mastery ---
        try:
            from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

            mastery_sync = ErrorBookMasterySyncService(self.db)
            mastery_results = await mastery_sync.apply_review_feedback(user_id, error, data.performance.value)
            await self.db.commit()
            await self._flush_pending_mastery_events(mastery_results)
        except Exception as e:
            logger.warning(f"Error book mastery sync (review) failed: {e}")

        return error

    async def _store_practice_outcome_memory(
        self,
        *,
        user_id: UUID,
        error: ErrorRecord,
        performance: ReviewPerformanceEnum,
        previous_mastery: float,
    ) -> None:
        memory_service = MemoryService(self.db)
        current_mastery = float(error.mastery_level or 0.0)
        summary = f"错题复习结果：{performance.value}，掌握度 {previous_mastery:.2f} → " f"{current_mastery:.2f}。"
        tags = [
            "practice_outcome",
            f"performance:{performance.value}",
            f"mastery_before:{previous_mastery:.2f}",
            f"mastery_after:{current_mastery:.2f}",
        ]
        await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=summary,
            source_type="practice_outcome",
            source_id=str(error.id),
            occurred_at=error.last_reviewed_at or _utcnow(),
            importance_score=0.55,
            tags=tags,
            evidence_refs=[
                {"type": "practice_outcome", "id": str(error.id), "schema_version": "practice_outcome.v1"},
                {"type": "error", "id": str(error.id), "schema_version": "error.v1"},
            ],
        )

    async def get_review_stats(self, user_id: UUID) -> dict:
        # Base query
        base_filter = and_(
            ErrorRecord.user_id == user_id,
            ErrorRecord.is_deleted.is_(False),
        )

        total = await self.db.scalar(select(func.count()).select_from(ErrorRecord).where(base_filter))

        mastered = await self.db.scalar(
            select(func.count()).select_from(ErrorRecord).where(and_(base_filter, ErrorRecord.mastery_level >= 0.8))
        )

        need_review = await self.db.scalar(
            select(func.count())
            .select_from(ErrorRecord)
            .where(and_(base_filter, ErrorRecord.next_review_at <= _utcnow()))
        )

        subject_result = await self.db.execute(
            select(ErrorRecord.subject_code, func.count()).where(base_filter).group_by(ErrorRecord.subject_code)
        )
        subject_distribution = {row[0]: row[1] for row in subject_result}

        streak_stats = await self.db.scalar(select(UserStreakStats).where(UserStreakStats.user_id == user_id))
        review_streak_days = int(streak_stats.current_streak or 0) if streak_stats else 0

        return {
            "total_errors": total or 0,
            "mastered_count": mastered or 0,
            "need_review_count": need_review or 0,
            "review_streak_days": review_streak_days,
            "subject_distribution": subject_distribution,
        }
