from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aurora_stage20 import RoutingDecisionLog


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RouteHistoryService:
    """Stage 20 write-only route history collector."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_decision(
        self,
        *,
        user_id: UUID,
        input_aggregator_snapshot_id: str,
        decision_type: str,
        decision_payload: dict[str, Any],
        skills_injected: list[UUID] | None = None,
        sufficiency_judgment_id: UUID | None = None,
        decided_at: datetime | None = None,
        decision_id: UUID | None = None,
    ) -> UUID:
        now = decided_at or _utcnow()
        record = RoutingDecisionLog(
            decision_id=decision_id or uuid.uuid4(),
            created_at=now,
            updated_at=now,
            user_id=user_id,
            decided_at=now,
            input_aggregator_snapshot_id=input_aggregator_snapshot_id,
            sufficiency_judgment_id=sufficiency_judgment_id,
            decision_type=decision_type,
            decision_payload=decision_payload,
            skills_injected=[str(item) for item in (skills_injected or [])],
        )
        self.db.add(record)
        await self.db.commit()
        return UUID(str(record.decision_id))

    async def record_explicit_feedback(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        positive: bool,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        record = await self._load_decision(decision_id)
        if record is None:
            return None
        record.outcome_signal_id = outcome_signal_id
        record.outcome_type = "thumbs_up" if positive else "thumbs_down"
        record.outcome_collected_at = collected_at or _utcnow()
        record.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def record_follow_up_input(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        record = await self._load_decision(decision_id)
        if record is None:
            return None
        record.outcome_signal_id = outcome_signal_id
        record.outcome_type = "implicit_follow_up"
        record.outcome_collected_at = collected_at or _utcnow()
        record.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def mark_timeout(
        self,
        *,
        decision_id: UUID,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        record = await self._load_decision(decision_id)
        if record is None:
            return None
        record.outcome_signal_id = "timeout"
        record.outcome_type = "timeout"
        record.outcome_collected_at = collected_at or _utcnow()
        record.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def _load_decision(self, decision_id: UUID) -> RoutingDecisionLog | None:
        result = await self.db.execute(
            select(RoutingDecisionLog).where(RoutingDecisionLog.decision_id == decision_id)
        )
        return result.scalar_one_or_none()
