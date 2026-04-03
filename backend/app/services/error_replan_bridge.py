from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select

from app.models.error_book import ErrorRecord
from app.models.galaxy import UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.task_resources import TaskKnowledgeLink
from app.orchestration.adaptive_replanner import AdaptiveReplanner


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ErrorReplanBridge:
    """Separates ErrorCreated -> immediate plan-health evaluation from mastery sync."""

    LOW_MASTERY_THRESHOLD = 50.0
    ERROR_PRESSURE_LOOKBACK_DAYS = 7
    ERROR_PRESSURE_TRIGGER_COUNT = 3
    TRIGGERING_ERROR_TYPES = {"concept_confusion", "knowledge_gap"}

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def on_error_created(
        self,
        *,
        user_id: UUID,
        error_id: UUID,
        linked_node_ids: list[UUID],
    ) -> dict[str, object]:
        normalized_node_ids = [node_id for node_id in linked_node_ids if node_id]
        if not normalized_node_ids:
            return {"triggered": False, "reason": "no_linked_nodes", "plan_ids": []}

        error = await self.db.get(ErrorRecord, error_id)
        if error is None or error.user_id != user_id:
            return {"triggered": False, "reason": "error_not_found", "plan_ids": []}

        error_type = self._extract_error_type(error)
        if error_type not in self.TRIGGERING_ERROR_TYPES:
            return {"triggered": False, "reason": f"unsupported_error_type:{error_type}", "plan_ids": []}

        plan_ids = await self._find_relevant_active_plan_ids(user_id=user_id, node_ids=normalized_node_ids)
        if not plan_ids:
            return {"triggered": False, "reason": "no_relevant_active_plan", "plan_ids": []}

        low_mastery_nodes = await self._find_low_mastery_nodes(user_id=user_id, node_ids=normalized_node_ids)
        if not low_mastery_nodes:
            return {"triggered": False, "reason": "mastery_not_low", "plan_ids": []}

        recent_error_count = await self._count_recent_triggering_errors(
            user_id=user_id,
            node_ids=low_mastery_nodes,
            days=self.ERROR_PRESSURE_LOOKBACK_DAYS,
        )
        if recent_error_count < self.ERROR_PRESSURE_TRIGGER_COUNT:
            return {
                "triggered": False,
                "reason": "insufficient_error_pressure",
                "plan_ids": [],
                "recent_error_count": recent_error_count,
            }

        replanner = AdaptiveReplanner(self.db, self.redis)
        triggered_plan_ids: list[str] = []
        for plan_id in sorted(plan_ids, key=str):
            await replanner.evaluate_plan_health_now(
                user_id=user_id,
                plan_id=plan_id,
                trigger="error_created_bridge",
                feedback_category="concept_gap_repeated",
            )
            triggered_plan_ids.append(str(plan_id))

        logger.info(
            "ErrorReplanBridge: triggered immediate plan-health evaluation for user={} error={} plans={} count={}",
            user_id,
            error_id,
            len(triggered_plan_ids),
            recent_error_count,
        )
        return {
            "triggered": True,
            "reason": "error_pressure_bridge",
            "plan_ids": triggered_plan_ids,
            "recent_error_count": recent_error_count,
        }

    @staticmethod
    def _extract_error_type(error: ErrorRecord) -> str:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        return str(analysis.get("error_type") or "other").strip().lower()

    async def _find_low_mastery_nodes(self, *, user_id: UUID, node_ids: list[UUID]) -> list[UUID]:
        result = await self.db.execute(
            select(UserNodeStatus.node_id)
            .where(UserNodeStatus.user_id == user_id)
            .where(UserNodeStatus.node_id.in_(node_ids))
            .where(UserNodeStatus.mastery_score < self.LOW_MASTERY_THRESHOLD)
        )
        return list(result.scalars().all())

    async def _find_relevant_active_plan_ids(self, *, user_id: UUID, node_ids: list[UUID]) -> set[UUID]:
        today = _utcnow().date()
        result = await self.db.execute(
            select(Task.plan_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(TaskKnowledgeLink, TaskKnowledgeLink.task_id == Task.id)
            .where(
                Task.user_id == user_id,
                Task.plan_id.is_not(None),
                Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
                TaskKnowledgeLink.knowledge_node_id.in_(node_ids),
            )
            .where((Task.due_date.is_(None)) | (Task.due_date >= today))
        )
        return {plan_id for plan_id in result.scalars().all() if plan_id is not None}

    async def _count_recent_triggering_errors(
        self,
        *,
        user_id: UUID,
        node_ids: list[UUID],
        days: int,
    ) -> int:
        cutoff = _utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(
                ErrorRecord.id,
                ErrorRecord.created_at,
                ErrorRecord.latest_analysis,
                ErrorRecord.linked_knowledge_node_ids,
            )
            .where(ErrorRecord.user_id == user_id)
            .where(ErrorRecord.is_deleted.is_(False))
            .order_by(desc(ErrorRecord.created_at))
        )

        seen_error_ids: set[UUID] = set()
        for error_id, created_at, latest_analysis, linked_ids in result.all():
            normalized_created_at = created_at
            if normalized_created_at and normalized_created_at.tzinfo is not None:
                normalized_created_at = normalized_created_at.replace(tzinfo=None)
            if normalized_created_at and normalized_created_at < cutoff:
                continue

            analysis = latest_analysis if isinstance(latest_analysis, dict) else {}
            error_type = str(analysis.get("error_type") or "other").strip().lower()
            if error_type not in self.TRIGGERING_ERROR_TYPES:
                continue

            linked = {str(value) for value in (linked_ids or []) if value is not None}
            if not linked.intersection({str(node_id) for node_id in node_ids}):
                continue
            seen_error_ids.add(error_id)
        return len(seen_error_ids)
