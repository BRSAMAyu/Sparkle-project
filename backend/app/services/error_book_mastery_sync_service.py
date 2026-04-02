"""
ErrorBookMasterySyncService — Bridges error evidence to knowledge node mastery.

This is断点2: 让错题证据正式写回知识节点掌握度。

Before this service:
  - Error book knows what the user got wrong (error_type, root_cause, linked nodes)
  - Galaxy knows what the user studied (task completion)
  - They never talked to each other in a meaningful way

After this service:
  - Error diagnosis → node mastery evidence-based decrease
  - Error review → node mastery recovery
  - Both flow into StudyRecord主干 and node_mastery_updated events

See: docs/product/implementation/ERROR_BOOK_TO_KNOWLEDGE_MASTERY_IMPLEMENTATION_2026-04-02.md
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.event_bus import NodeMasteryUpdatedEvent
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.services.galaxy.stats_service import GalaxyStatsService


# ---------------------------------------------------------------------------
# Error type → mastery impact weights
# ---------------------------------------------------------------------------

ERROR_TYPE_IMPACT: dict[str, int] = {
    "concept_confusion": -8,
    "knowledge_gap": -10,
    "method_wrong": -6,
    "logic_error": -5,
    "calculation_error": -3,
    "reading_careless": -2,
    "other": -3,
}

# Multi-node decay: how much of the base impact to apply per node rank
NODE_RANK_WEIGHTS = [1.0, 0.6, 0.3]

# Review performance → node mastery recovery
REVIEW_PERFORMANCE_IMPACT: dict[str, int] = {
    "remembered": 4,
    "fuzzy": 1,
    "forgot": -2,
}

# Safety limits
MAX_SINGLE_ERROR_IMPACT = 10   # 单次错题最多对单节点扣10分
MIN_MASTERY_SCORE = 0
MAX_MASTERY_SCORE = 100


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ErrorBookMasterySyncService:
    """Syncs error evidence to knowledge node mastery scores."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.stats_service = GalaxyStatsService(db)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def apply_error_diagnosis(
        self,
        user_id: UUID,
        error_record: Any,  # ErrorRecord from error_book models
    ) -> list[dict]:
        """Apply error diagnosis to linked knowledge nodes.

        Called after analyze_and_link() successfully writes linked_knowledge_node_ids.

        For each linked node:
        1. Calculate mastery delta based on error_type
        2. Update UserNodeStatus.mastery_score
        3. Write StudyRecord(record_type='error_diagnosis')
        4. Publish node_mastery_updated event

        Returns list of {node_id, old_mastery, new_mastery, delta} dicts.
        """
        linked_ids = getattr(error_record, "linked_knowledge_node_ids", None) or []
        if not linked_ids:
            return []

        error_type = self._extract_error_type(error_record)
        base_impact = ERROR_TYPE_IMPACT.get(error_type, -3)

        results: list[dict] = []
        for rank, node_id in enumerate(linked_ids[:3]):  # Max 3 nodes
            weight = NODE_RANK_WEIGHTS[rank] if rank < len(NODE_RANK_WEIGHTS) else 0.3
            delta = self._clamp_impact(round(base_impact * weight))

            node_result = await self._update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                delta=delta,
                record_type="error_diagnosis",
                reason=f"error_diagnosis:{error_type}",
                error_id=getattr(error_record, "id", None),
            )
            if node_result:
                results.append(node_result)

        if results:
            logger.info(
                "ErrorBookMasterySync: applied diagnosis for error {}, "
                "type={}, affected {} nodes",
                getattr(error_record, "id", "?"),
                error_type,
                len(results),
            )

        return results

    async def apply_review_feedback(
        self,
        user_id: UUID,
        error_record: Any,
        performance: str,
    ) -> list[dict]:
        """Apply review feedback to linked knowledge nodes.

        Called after submit_review() updates error_record.mastery_level.

        Maps review performance to node mastery recovery:
        - remembered → +4
        - fuzzy → +1
        - forgot → -2

        Returns list of {node_id, old_mastery, new_mastery, delta} dicts.
        """
        linked_ids = getattr(error_record, "linked_knowledge_node_ids", None) or []
        if not linked_ids:
            return []

        delta = REVIEW_PERFORMANCE_IMPACT.get(performance, 0)
        if delta == 0:
            return []

        results: list[dict] = []
        for node_id in linked_ids[:3]:
            node_result = await self._update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                delta=delta,
                record_type="error_review",
                reason=f"error_review:{performance}",
                error_id=getattr(error_record, "id", None),
            )
            if node_result:
                results.append(node_result)

        if results:
            logger.info(
                "ErrorBookMasterySync: applied review feedback for error {}, "
                "performance={}, affected {} nodes",
                getattr(error_record, "id", "?"),
                performance,
                len(results),
            )

        return results

    # -----------------------------------------------------------------------
    # Core mastery update
    # -----------------------------------------------------------------------

    async def _update_node_mastery(
        self,
        user_id: UUID,
        node_id: UUID,
        delta: int,
        record_type: str,
        reason: str,
        error_id: UUID | None = None,
    ) -> dict | None:
        """Update a single node's mastery and record the change."""
        status = await self._get_or_create_node_status(
            user_id,
            node_id,
            create_if_missing=False,
        )
        old_mastery = int(status.mastery_score or 0) if status else 0
        new_mastery = self._clamp_mastery(old_mastery + delta)

        if status is None and new_mastery == old_mastery:
            return None

        if status is None:
            status = await self._get_or_create_node_status(
                user_id,
                node_id,
                create_if_missing=True,
            )
            if not status:
                logger.warning(
                    "ErrorBookMasterySync: could not create status for user={}/node={}",
                    user_id, node_id,
                )
                return None

        if new_mastery == old_mastery:
            return None

        # 2. Update mastery
        now = _utcnow()
        was_unlocked = bool(status.is_unlocked)
        status.mastery_score = new_mastery
        status.study_count = (status.study_count or 0) + 1
        status.last_study_at = now

        # 3. Update BKT mastery probability & next_review_at (fix #3)
        # Scale mastery_score (0-100) → bkt_mastery_prob (0.0-1.0)
        status.bkt_mastery_prob = max(0.0, min(new_mastery / 100.0, 1.0))
        status.bkt_last_updated_at = now
        status.next_review_at = self.stats_service._calculate_next_review(float(new_mastery))
        if new_mastery > 0:
            status.is_unlocked = True
            if not was_unlocked and getattr(status, "first_unlock_at", None) is None:
                status.first_unlock_at = now

        # 4. Write StudyRecord
        study_record = StudyRecord(
            user_id=user_id,
            node_id=node_id,
            study_minutes=0,
            mastery_delta=float(new_mastery - old_mastery),
            initial_mastery=float(old_mastery),
            record_type=record_type,
        )
        self.db.add(study_record)

        # 5. Defer event publish — caller commits then flushes pending events (fix #1)
        pending_event = {
            "topic": "node_mastery_updated",
            "payload": NodeMasteryUpdatedEvent(
                user_id=str(user_id),
                node_id=str(node_id),
                old_mastery=old_mastery,
                new_mastery=new_mastery,
                reason=reason,
            ).to_dict(),
        }

        return {
            "node_id": str(node_id),
            "error_id": str(error_id) if error_id else None,
            "old_mastery": old_mastery,
            "new_mastery": new_mastery,
            "delta": new_mastery - old_mastery,
            "record_type": record_type,
            "_pending_event": pending_event,
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    async def _get_or_create_node_status(
        self,
        user_id: UUID,
        node_id: UUID,
        *,
        create_if_missing: bool = True,
    ) -> UserNodeStatus | None:
        """Get existing UserNodeStatus or create a new one."""
        try:
            result = await self.db.execute(
                select(UserNodeStatus).where(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id == node_id,
                )
            )
            status = result.scalar_one_or_none()
            if status:
                return status
            if not create_if_missing:
                return None

            # Create new — but do NOT auto-unlock (fix #2):
            # A node linked via error diagnosis with 0 mastery has no evidence yet.
            # It enters the user's awareness via the StudyRecord but stays locked
            # until positive evidence (task completion or review recovery) unlocks it.
            status = UserNodeStatus(
                user_id=user_id,
                node_id=node_id,
                mastery_score=0,
                is_unlocked=False,
                study_count=0,
                bkt_mastery_prob=0.0,
            )
            self.db.add(status)
            # Flush to get the object into session
            await self.db.flush()
            return status
        except Exception as exc:
            logger.warning(
                "ErrorBookMasterySync: get/create failed for {}/{}: {}",
                user_id, node_id, exc,
            )
            return None

    def _extract_error_type(self, error_record: Any) -> str:
        """Extract error_type from the error record's latest_analysis."""
        analysis = getattr(error_record, "latest_analysis", None) or {}
        if isinstance(analysis, dict):
            return analysis.get("error_type", "other")
        return "other"

    @staticmethod
    def _clamp_impact(value: int) -> int:
        """Clamp single-impact to safety range."""
        return max(-MAX_SINGLE_ERROR_IMPACT, min(MAX_SINGLE_ERROR_IMPACT, value))

    @staticmethod
    def _clamp_mastery(value: int) -> int:
        """Clamp mastery to 0-100 range."""
        return max(MIN_MASTERY_SCORE, min(MAX_MASTERY_SCORE, value))
