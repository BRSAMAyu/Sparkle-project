"""
Asset review signal processor - infer retention signals from learning assets.
"""
from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.learning_assets import AssetStatus, LearningAsset
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import pick_with_hysteresis, recency_weight


class AssetReviewSignalProcessor:
    """Infer review-style signals from active learning assets."""

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis or cache_service.redis
        self.profile_write_service = ProfileWriteService(db, self.redis)

    async def process_assets(self, user_id: UUID) -> None:
        result = await self.db.execute(
            select(LearningAsset).where(
                LearningAsset.user_id == user_id,
                LearningAsset.status == AssetStatus.ACTIVE.value,
                LearningAsset.deleted_at.is_(None),
            )
        )
        assets = list(result.scalars().all())
        if not assets:
            return

        try:
            prefs = await self.profile_write_service.pref_service.get_preferences(user_id)
            previous_style = (prefs.inferred or {}).get("vocabulary_retention_style")
        except Exception:
            previous_style = None

        weighted_total = 0.0
        weighted_reviewed_assets = 0.0
        weighted_reviews = 0.0
        weighted_success = 0.0
        ignored_weight = 0.0
        style_scores = {"passive": 0.0, "consistent": 0.0, "cramming": 0.0}
        for asset in assets:
            observed_at = (
                asset.last_seen_at
                or asset.review_due_at
                or asset.provenance_updated_at
                or asset.updated_at
                or asset.created_at
            )
            weight = recency_weight(observed_at, half_life_days=10.0, min_weight=0.25)
            weighted_total += weight
            ignored_weight += min(float(asset.ignored_count or 0), 3.0) * weight
            if (asset.review_count or 0) > 0:
                weighted_reviewed_assets += weight
                review_count = float(asset.review_count or 0)
                weighted_reviews += review_count * weight
                weighted_success += float(asset.review_success_rate or 0.0) * review_count * weight

            if (asset.ignored_count or 0) >= 2:
                style_scores["passive"] += weight
            elif (asset.review_count or 0) >= 2 and float(asset.review_success_rate or 0.0) >= 0.75:
                style_scores["consistent"] += weight
            else:
                style_scores["cramming"] += weight

        review_engagement = weighted_reviewed_assets / weighted_total if weighted_total else 0.0
        review_accuracy = (weighted_success / weighted_reviews) if weighted_reviews > 0 else 0.0

        ignored_ratio = ignored_weight / weighted_total if weighted_total else 0.0
        if review_engagement >= 0.6 and review_accuracy >= 0.75:
            style_scores["consistent"] += 0.25
        elif ignored_ratio >= 0.6:
            style_scores["passive"] += 0.25
        else:
            style_scores["cramming"] += 0.15
        selected_style = pick_with_hysteresis(
            style_scores,
            previous_style if isinstance(previous_style, str) else None,
            margin=0.15,
        )
        retention_style = selected_style if isinstance(selected_style, str) else "cramming"

        updates: dict[str, object] = {
            "review_engagement": round(review_engagement, 3),
            "review_accuracy": round(review_accuracy, 3),
            "vocabulary_retention_style": retention_style,
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
            logger.warning("AssetReviewSignalProcessor failed to update inferred prefs: %s", exc)

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
