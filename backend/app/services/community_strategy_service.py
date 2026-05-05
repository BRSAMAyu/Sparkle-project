"""Community strategy outcome recording service — COM-012 / GAP-P4-11."""

from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_strategy_outcome import CommunityStrategyOutcome


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CommunityStrategyService:
    """Persist and query community strategy outcomes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_outcome(
        self,
        *,
        user_id: str,
        directive_id: str,
        trigger_type: str,
        decision: str,
        context_snapshot: dict | None = None,
        user_feedback: str | None = None,
        time_to_decision_seconds: int | None = None,
        source: str = "user_action",
    ) -> CommunityStrategyOutcome:
        outcome = CommunityStrategyOutcome(
            user_id=user_id,
            directive_id=directive_id,
            trigger_type=trigger_type,
            decision=decision,
            context_snapshot=context_snapshot or {},
            time_to_decision_seconds=time_to_decision_seconds,
            user_feedback=user_feedback,
            source=source,
        )
        self.db.add(outcome)
        await self.db.commit()
        await self.db.refresh(outcome)
        logger.info(
            "CommunityStrategyOutcome recorded: user=%s directive=%s decision=%s trigger=%s",
            user_id, directive_id, decision, trigger_type,
        )
        return outcome

    async def list_outcomes(
        self,
        *,
        user_id: str,
        trigger_type: str | None = None,
        decision: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CommunityStrategyOutcome]:
        stmt = (
            select(CommunityStrategyOutcome)
            .where(CommunityStrategyOutcome.user_id == user_id)
            .where(CommunityStrategyOutcome.deleted_at.is_(None))
        )
        if trigger_type:
            stmt = stmt.where(CommunityStrategyOutcome.trigger_type == trigger_type)
        if decision:
            stmt = stmt.where(CommunityStrategyOutcome.decision == decision)

        stmt = stmt.order_by(desc(CommunityStrategyOutcome.created_at))
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_directive(
        self,
        *,
        user_id: str,
        directive_id: str,
    ) -> CommunityStrategyOutcome | None:
        stmt = (
            select(CommunityStrategyOutcome)
            .where(CommunityStrategyOutcome.user_id == user_id)
            .where(CommunityStrategyOutcome.directive_id == directive_id)
            .where(CommunityStrategyOutcome.deleted_at.is_(None))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
