from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cognitive import CognitiveFragment
from app.schemas.analysis import AnalysisResult, AnalysisTaskInput
from app.schemas.intervention import EvidenceRef
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.analytics_service import AnalyticsService
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class UnifiedAnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = AnalyticsService(db)
        self.orchestrator = AnalysisOrchestrator()
        self.memory_service = MemoryService(db)

    async def analyze_fragment(self, fragment: CognitiveFragment) -> AnalysisResult:
        similar_text = await self._build_similar_text(fragment)
        user_summary = await self.analytics_service.get_user_profile_summary(fragment.user_id)

        evidence_refs = []
        if fragment.source_event_id:
            evidence_refs.append(
                EvidenceRef(type="event", id=fragment.source_event_id, schema_version="event.v1")
            )

        task_input = AnalysisTaskInput(
            task_id=str(fragment.id),
            task_type="behavior_pattern_from_fragment",
            user_id=fragment.user_id,
            source_type=fragment.source_type or "cognitive_fragment",
            payload={
                "fragment_content": fragment.content,
                "context_tags": fragment.context_tags,
                "error_tags": fragment.error_tags,
                "severity": fragment.severity,
                "similar_text": similar_text,
                "user_summary": user_summary,
            },
            evidence_refs=evidence_refs,
            context={"complexity": 0.6},
        )
        result = await self.orchestrator.run_task(task_input)
        result.metadata.setdefault("user_id", str(fragment.user_id))
        return result

    async def analyze_error(self, error_record: Any) -> AnalysisResult:
        raise NotImplementedError("analyze_error not implemented in Phase2")

    async def write_memory_from_result(self, result: AnalysisResult) -> str | None:
        if result.status != "ok":
            return None
        if result.task_type != "behavior_pattern_from_fragment":
            return None
        if not result.evidence_refs:
            return None
        if not result.primary_output:
            return None

        pattern_name = result.primary_output.get("pattern_name") or "Behavior Pattern"
        root_cause = result.primary_output.get("root_cause") or ""
        summary = f"{pattern_name}: {root_cause}".strip(": ")
        tags = [result.primary_output.get("pattern_type")] if result.primary_output.get("pattern_type") else None

        if "user_id" not in result.metadata:
            return None
        user_id = UUID(result.metadata["user_id"])
        record = await self.memory_service.create_episodic_memory(
            user_id=user_id,
            summary=summary,
            source_type="analysis",
            source_id=result.task_id,
            occurred_at=_utcnow(),
            importance_score=result.primary_output.get("confidence_score"),
            tags=tags,
            evidence_refs=[ref.model_dump() for ref in result.evidence_refs],
        )
        if record is None:
            logger.info("Episodic memory write blocked for analysis task %s", result.task_id)
            return None
        logger.info(f"Wrote episodic memory from analysis {result.task_id}: {record.id}")
        return str(record.id)

    async def _build_similar_text(self, fragment: CognitiveFragment) -> str:
        fragment_embedding = fragment.__dict__.get("embedding")
        if fragment_embedding is None:
            return ""
        try:
            rag_query = (
                select(CognitiveFragment)
                .where(CognitiveFragment.user_id == fragment.user_id)
                .where(CognitiveFragment.id != fragment.id)
                .where(CognitiveFragment.embedding.isnot(None))
                .order_by(CognitiveFragment.embedding.cosine_distance(fragment_embedding))
                .limit(3)
            )
            rag_result = await self.db.execute(rag_query)
            similar_fragments = rag_result.scalars().all()
        except Exception as exc:
            logger.warning(f"Unified analysis skipped similar fragment retrieval: {exc}")
            return ""

        return "\n".join(
            [f"- {item.content} (Tags: {item.error_tags})" for item in similar_fragments]
        )
