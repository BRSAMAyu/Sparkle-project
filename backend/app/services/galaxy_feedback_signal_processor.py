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
from app.services.signal_adaptation import pick_with_hysteresis, recency_weight, weighted_average


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

        try:
            prefs = await self.profile_write_service.pref_service.get_preferences(user_id)
            previous_depth = (prefs.inferred or {}).get("preferred_expansion_depth")
        except Exception:
            previous_depth = None

        satisfaction = self._compute_satisfaction(feedbacks)
        preferred_depth = self._preferred_depth(feedbacks, satisfaction, previous_depth if isinstance(previous_depth, str) else None)

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
    def _compute_satisfaction(feedbacks: list[ExpansionFeedback]) -> float:
        weighted_ratings: list[tuple[float, float]] = []
        weighted_implicit: list[tuple[float, float]] = []
        now = None
        for item in feedbacks:
            observed_at = getattr(item, "created_at", None)
            weight = recency_weight(observed_at, now=now, half_life_days=7.0, min_weight=0.25)
            if item.rating is not None:
                weighted_ratings.append((float(item.rating), weight))
            if item.implicit_score is not None:
                weighted_implicit.append((max(0.0, min(1.0, float(item.implicit_score))), weight))

        avg_rating = weighted_average(weighted_ratings)
        if avg_rating is not None:
            return max(0.0, min(1.0, (avg_rating - 1.0) / 4.0))
        implicit = weighted_average(weighted_implicit)
        if implicit is not None:
            return implicit
        return 0.5

    @staticmethod
    def _preferred_depth(
        feedbacks: list[ExpansionFeedback],
        satisfaction: float,
        previous: str | None = None,
    ) -> str:
        now = None
        scores = {"deep": 0.0, "moderate": 0.0, "shallow": 0.0}
        for item in feedbacks:
            weight = recency_weight(getattr(item, "created_at", None), now=now, half_life_days=7.0, min_weight=0.25)
            if item.rating is None:
                continue
            rating = int(item.rating)
            if rating >= 4:
                scores["deep"] += weight
            elif rating <= 2:
                scores["shallow"] += weight
            else:
                scores["moderate"] += weight

        selected = pick_with_hysteresis(scores, previous, margin=0.12)
        if isinstance(selected, str) and scores.get(selected, 0.0) > 0:
            return selected
        if satisfaction >= 0.7:
            return "deep"
        if satisfaction <= 0.35:
            return "shallow"
        return "moderate"
