"""
Galaxy feedback signal processor - infer profile signals from expansion feedback.
"""
from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.galaxy import ExpansionFeedback
from app.services.profile_write_service import ProfileWriteService


class GalaxyFeedbackSignalProcessor:
    """Infer expansion-preference signals from recent galaxy feedback."""

    WINDOW_SIZE = 30

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis or cache_service.redis
        self.profile_write_service = ProfileWriteService(db, self.redis)

    async def process_feedback(self, user_id: UUID) -> None:
        result = await self.db.execute(
            select(ExpansionFeedback)
            .where(ExpansionFeedback.user_id == user_id)
            .order_by(desc(ExpansionFeedback.created_at))
            .limit(self.WINDOW_SIZE)
        )
        feedbacks = list(result.scalars().all())
        if not feedbacks:
            return

        ratings = [int(item.rating) for item in feedbacks if item.rating is not None]
        implicit_scores = [
            max(0.0, min(1.0, float(item.implicit_score)))
            for item in feedbacks
            if item.implicit_score is not None
        ]

        satisfaction = self._compute_satisfaction(ratings, implicit_scores)
        preferred_depth = self._preferred_depth(ratings, satisfaction)

        updates: dict[str, object] = {
            "knowledge_expansion_satisfaction": round(satisfaction, 3),
            "preferred_expansion_depth": preferred_depth,
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
            logger.warning("GalaxyFeedbackSignalProcessor failed to update inferred prefs: %s", exc)

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
    def _compute_satisfaction(ratings: list[int], implicit_scores: list[float]) -> float:
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            return max(0.0, min(1.0, (avg_rating - 1.0) / 4.0))
        if implicit_scores:
            return sum(implicit_scores) / len(implicit_scores)
        return 0.5

    @staticmethod
    def _preferred_depth(ratings: list[int], satisfaction: float) -> str:
        if ratings:
            high_ratio = sum(1 for rating in ratings if rating >= 4) / len(ratings)
            low_ratio = sum(1 for rating in ratings if rating <= 2) / len(ratings)
            if high_ratio > 0.6:
                return "deep"
            if low_ratio > 0.4:
                return "shallow"
        if satisfaction >= 0.7:
            return "deep"
        if satisfaction <= 0.35:
            return "shallow"
        return "moderate"
