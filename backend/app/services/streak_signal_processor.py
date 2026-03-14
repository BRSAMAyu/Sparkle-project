"""
Streak signal processor - infer profile signals from check-in consistency.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.achievement import UserStreakStats
from app.models.user import User
from app.services.profile_write_service import ProfileWriteService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class StreakSignalProcessor:
    """Infer persistence and motivation signals from check-in streaks."""

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis or cache_service.redis
        self.profile_write_service = ProfileWriteService(db, self.redis)

    async def process_checkin(self, user_id: UUID) -> None:
        streak_result = await self.db.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        )
        streak = streak_result.scalar_one_or_none()
        if streak is None:
            return

        user = await self.db.get(User, user_id)
        registered_days = self._registered_days(user.created_at if user else None)
        current = int(streak.current_streak or 0)
        maximum = max(int(streak.max_streak or 0), int(streak.longest_streak or 0), 1)
        total_checkin_days = int(streak.total_checkin_days or 0)

        streak_consistency = current / maximum
        checkin_regularity = min(1.0, total_checkin_days / registered_days)
        if current > 7:
            motivation_type = "streak_driven"
        elif current < 3:
            motivation_type = "task_driven"
        else:
            motivation_type = "balanced"

        updates: dict[str, object] = {
            "streak_consistency": round(streak_consistency, 3),
            "motivation_type": motivation_type,
            "checkin_regularity": round(checkin_regularity, 3),
        }
        updates = await self._filter_noop_updates(user_id, updates)
        if not updates:
            return

        try:
            await self.profile_write_service.update_inferred_preference(
                user_id=user_id,
                updates=updates,
                source="ai_inferred",
            )
        except Exception as exc:
            logger.warning("StreakSignalProcessor failed to update inferred prefs: %s", exc)

    async def _filter_noop_updates(self, user_id: UUID, updates: dict[str, object]) -> dict[str, object]:
        try:
            prefs = await self.profile_write_service.pref_service.get_preferences(user_id)
            inferred = prefs.inferred or {}
        except Exception:
            return updates
        return {
            key: value
            for key, value in updates.items()
            if inferred.get(key) != value
        }

    @staticmethod
    def _registered_days(created_at: datetime | None) -> int:
        if created_at is None:
            return 1
        delta = _utcnow().date() - created_at.date()
        return max(delta.days + 1, 1)
