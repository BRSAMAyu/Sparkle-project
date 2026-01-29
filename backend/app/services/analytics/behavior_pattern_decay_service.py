from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.cognitive import BehaviorPattern


class BehaviorPatternDecayService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_decay(
        self,
        user_id: UUID,
        window_days: int = 30,
        decay_factor: float = 0.9,
        min_confidence: float = 0.35,
    ) -> dict[str, int]:
        if not settings.ENABLE_BEHAVIOR_DECAY:
            return {"updated": 0, "archived": 0}

        cutoff = datetime.utcnow() - timedelta(days=window_days)
        decay_guard = datetime.utcnow() - timedelta(hours=24)
        result = await self.db.execute(
            select(BehaviorPattern).where(
                BehaviorPattern.user_id == user_id,
                not BehaviorPattern.is_archived,
            )
        )
        patterns = result.scalars().all()

        updated = 0
        archived = 0
        for pattern in patterns:
            observed_at = pattern.last_observed_at or pattern.created_at
            if observed_at and observed_at > cutoff:
                continue
            if pattern.last_decay_at and pattern.last_decay_at > decay_guard:
                continue
            pattern.confidence_score = float(pattern.confidence_score or 0.0) * decay_factor
            pattern.last_decay_at = datetime.utcnow()
            if pattern.confidence_score < min_confidence and not pattern.is_archived:
                pattern.is_archived = True
                archived += 1
            updated += 1

        if updated:
            await self.db.commit()
        return {"updated": updated, "archived": archived}
