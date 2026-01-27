from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.event import TrackingEvent
from app.models.galaxy import KnowledgeNode
from app.models.semantic_memory import StrategyNode
from app.models.task import Task
from app.models.nightly_review import NightlyReview
from app.models.user_state import UserStateSnapshot
from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory
from app.core.business_metrics import EVIDENCE_MISSING_TOTAL
from app.services.evidence_scoring import compute_score
from loguru import logger


class EvidenceHealthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_evidence_refs(
        self,
        evidence_refs: Iterable[Dict[str, Any]],
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for ref in evidence_refs:
            ref_type = ref.get("type")
            ref_id = ref.get("id")
            if not ref_type or not ref_id:
                results.append({"type": ref_type, "id": ref_id, "status": "invalid"})
                continue
            resolver = getattr(self, f"_resolve_{ref_type}", None)
            if resolver is None:
                results.append({"type": ref_type, "id": ref_id, "status": "unsupported"})
                continue
            results.append(await resolver(ref_id, user_id))
        return results

    async def check_memory_item(
        self,
        item: Any,
        user_id: UUID,
    ) -> Dict[str, Any]:
        evidence_refs = item.evidence_refs or []
        if not evidence_refs:
            return {"missing": True, "snapshot": [], "resolved": []}
        resolved = await self.resolve_evidence_refs(evidence_refs, user_id)
        missing = any(entry["status"] != "ok" for entry in resolved)
        if missing:
            logger.info(
                "Evidence missing for memory item {item_type} {item_id}",
                item_type=item.__class__.__name__,
                item_id=getattr(item, "id", None),
            )
        snapshot = self.build_snapshot(resolved) if isinstance(item, EpisodicMemory) else None
        return {
            "missing": missing,
            "snapshot": snapshot,
            "resolved": resolved,
        }

    async def run_health_check(self, user_id: UUID, limit: int = 50) -> Dict[str, Dict[str, int]]:
        counts = {"preferences": 0, "goals": 0, "episodic": 0}
        missing_counts = {"preferences": 0, "goals": 0, "episodic": 0}

        prefs = await self._get_recent(MemoryPreference, user_id, limit)
        for item in prefs:
            result = await self.check_memory_item(item, user_id)
            item.evidence_missing = result["missing"]
            item.evidence_checked_at = datetime.utcnow()
            item.evidence_score = compute_score(item.evidence_refs, evidence_missing=result["missing"])
            if result["missing"]:
                EVIDENCE_MISSING_TOTAL.labels(type="preference").inc()
                missing_counts["preferences"] += 1
            counts["preferences"] += 1

        goals = await self._get_recent(MemoryGoal, user_id, limit)
        for item in goals:
            result = await self.check_memory_item(item, user_id)
            item.evidence_missing = result["missing"]
            item.evidence_checked_at = datetime.utcnow()
            item.evidence_score = compute_score(item.evidence_refs, evidence_missing=result["missing"])
            if result["missing"]:
                EVIDENCE_MISSING_TOTAL.labels(type="goal").inc()
                missing_counts["goals"] += 1
            counts["goals"] += 1

        episodic = await self._get_recent(EpisodicMemory, user_id, limit)
        for item in episodic:
            result = await self.check_memory_item(item, user_id)
            item.evidence_missing = result["missing"]
            item.evidence_checked_at = datetime.utcnow()
            item.evidence_snapshot = result["snapshot"]
            item.evidence_score = compute_score(item.evidence_refs, evidence_missing=result["missing"])
            if result["missing"]:
                EVIDENCE_MISSING_TOTAL.labels(type="episodic").inc()
                missing_counts["episodic"] += 1
            counts["episodic"] += 1

        await self.db.commit()
        return {"checked": counts, "missing": missing_counts}

    async def _get_recent(self, model, user_id: UUID, limit: int):
        conditions = [model.user_id == user_id, model.deleted_at.is_(None)]
        if hasattr(model, "retracted_at"):
            conditions.append(model.retracted_at.is_(None))
        result = await self.db.execute(
            select(model)
            .where(*conditions)
            .order_by(model.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def build_snapshot(resolved: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        snapshot: List[Dict[str, Any]] = []
        for entry in resolved:
            snapshot.append(
                {
                    "type": entry.get("type"),
                    "id": entry.get("id"),
                    "status": entry.get("status"),
                    "detail": entry.get("detail"),
                }
            )
        return snapshot

    async def _resolve_event(self, event_id: str, user_id: UUID) -> Dict[str, Any]:
        result = await self.db.execute(
            select(TrackingEvent).where(
                TrackingEvent.event_id == event_id,
                TrackingEvent.user_id == user_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            return {"type": "event", "id": event_id, "status": "not_found"}
        if event.deleted_at is not None:
            return {"type": "event", "id": event_id, "status": "redacted"}
        return {
            "type": "event",
            "id": event_id,
            "status": "ok",
            "detail": {"event_type": event.event_type, "ts_ms": event.ts_ms},
        }

    async def _resolve_user_state(self, snapshot_id: str, user_id: UUID) -> Dict[str, Any]:
        try:
            snapshot_uuid = UUID(snapshot_id)
        except ValueError:
            return {"type": "user_state", "id": snapshot_id, "status": "invalid_id"}

        result = await self.db.execute(
            select(UserStateSnapshot).where(
                UserStateSnapshot.id == snapshot_uuid,
                UserStateSnapshot.user_id == user_id,
            )
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            return {"type": "user_state", "id": snapshot_id, "status": "not_found"}
        if snapshot.deleted_at is not None:
            return {"type": "user_state", "id": snapshot_id, "status": "redacted"}
        return {
            "type": "user_state",
            "id": snapshot_id,
            "status": "ok",
            "detail": {
                "snapshot_at": snapshot.snapshot_at,
                "strain_index": snapshot.strain_index,
            },
        }

    async def _resolve_error(self, error_id: str, user_id: UUID) -> Dict[str, Any]:
        try:
            error_uuid = UUID(error_id)
        except ValueError:
            return {"type": "error", "id": error_id, "status": "invalid_id"}
        result = await self.db.execute(
            select(ErrorRecord).where(
                ErrorRecord.id == error_uuid,
                ErrorRecord.user_id == user_id,
            )
        )
        error = result.scalar_one_or_none()
        if not error:
            return {"type": "error", "id": error_id, "status": "not_found"}
        if error.is_deleted:
            return {"type": "error", "id": error_id, "status": "redacted"}
        return {
            "type": "error",
            "id": error_id,
            "status": "ok",
            "detail": {"subject_code": error.subject_code},
        }

    async def _resolve_concept(self, node_id: str, user_id: UUID) -> Dict[str, Any]:
        try:
            node_uuid = UUID(node_id)
        except ValueError:
            return {"type": "concept", "id": node_id, "status": "invalid_id"}
        result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_uuid))
        node = result.scalar_one_or_none()
        if not node:
            return {"type": "concept", "id": node_id, "status": "not_found"}
        if node.deleted_at is not None:
            return {"type": "concept", "id": node_id, "status": "redacted"}
        return {
            "type": "concept",
            "id": node_id,
            "status": "ok",
            "detail": {"name": node.name},
        }

    async def _resolve_strategy(self, strategy_id: str, user_id: UUID) -> Dict[str, Any]:
        try:
            strategy_uuid = UUID(strategy_id)
        except ValueError:
            return {"type": "strategy", "id": strategy_id, "status": "invalid_id"}
        result = await self.db.execute(
            select(StrategyNode).where(
                StrategyNode.id == strategy_uuid,
                StrategyNode.user_id == user_id,
            )
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            return {"type": "strategy", "id": strategy_id, "status": "not_found"}
        if strategy.deleted_at is not None:
            return {"type": "strategy", "id": strategy_id, "status": "redacted"}
        return {
            "type": "strategy",
            "id": strategy_id,
            "status": "ok",
            "detail": {"title": strategy.title},
        }

    async def _resolve_task(self, task_id: str, user_id: UUID) -> Dict[str, Any]:
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            return {"type": "task", "id": task_id, "status": "invalid_id"}
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_uuid,
                Task.user_id == user_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return {"type": "task", "id": task_id, "status": "not_found"}
        if task.deleted_at is not None:
            return {"type": "task", "id": task_id, "status": "redacted"}
        return {
            "type": "task",
            "id": task_id,
            "status": "ok",
            "detail": {"title": task.title, "status": task.status.value if task.status else None},
        }

    async def _resolve_summary(self, summary_id: str, user_id: UUID) -> Dict[str, Any]:
        try:
            summary_uuid = UUID(summary_id)
        except ValueError:
            return {"type": "summary", "id": summary_id, "status": "invalid_id"}
        result = await self.db.execute(
            select(NightlyReview).where(
                NightlyReview.id == summary_uuid,
                NightlyReview.user_id == user_id,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            return {"type": "summary", "id": summary_id, "status": "not_found"}
        if review.deleted_at is not None:
            return {"type": "summary", "id": summary_id, "status": "redacted"}
        return {
            "type": "summary",
            "id": summary_id,
            "status": "ok",
            "detail": {"review_date": review.review_date},
        }
