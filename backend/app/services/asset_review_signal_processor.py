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

        total_assets = len(assets)
        reviewed_assets = [asset for asset in assets if (asset.review_count or 0) > 0]
        review_engagement = len(reviewed_assets) / total_assets

        weighted_reviews = sum(int(asset.review_count or 0) for asset in reviewed_assets)
        if weighted_reviews > 0:
            weighted_success = sum(
                float(asset.review_success_rate or 0.0) * int(asset.review_count or 0)
                for asset in reviewed_assets
            )
            review_accuracy = weighted_success / weighted_reviews
        else:
            review_accuracy = 0.0

        ignored_ratio = sum(int(asset.ignored_count or 0) for asset in assets) / total_assets
        if ignored_ratio > 0.5:
            retention_style = "passive"
        elif review_engagement >= 0.6 and review_accuracy >= 0.75:
            retention_style = "consistent"
        else:
            retention_style = "cramming"

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
