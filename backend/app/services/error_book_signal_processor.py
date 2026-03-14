"""
Error book signal processor - infer preferences from error book patterns.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.error_book import ErrorRecord
from app.services.profile_write_service import ProfileWriteService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ErrorBookSignalProcessor:
    """Process ErrorCreated events and update inferred preferences."""

    WINDOW_DAYS = 14
    DENSITY_MAX_ERRORS = 20.0
    MAX_TAGS = 5

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis or cache_service.redis
        self.profile_write_service = ProfileWriteService(db, self.redis)

    async def process_error_created(self, user_id: UUID) -> None:
        since = _utcnow() - timedelta(days=self.WINDOW_DAYS)
        result = await self.db.execute(
            select(ErrorRecord).where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted.is_(False),
                ErrorRecord.created_at >= since,
            )
        )
        errors = list(result.scalars().all())
        if not errors:
            return

        total = len(errors)
        error_density_score = min(1.0, total / self.DENSITY_MAX_ERRORS)
        recurring_error_tags = self._recurring_error_tags(errors)
        error_correction_rate = self._correction_rate(errors)

        updates: dict[str, object] = {
            "error_density_score": round(error_density_score, 3),
            "error_correction_rate": round(error_correction_rate, 3),
            "recurring_error_tags": recurring_error_tags,
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
            logger.warning("ErrorBookSignalProcessor failed to update inferred prefs: %s", exc)

    async def _filter_noop_updates(self, user_id: UUID, updates: dict[str, object]) -> dict[str, object]:
        if not updates:
            return {}
        try:
            prefs = await self.profile_write_service.pref_service.get_preferences(user_id)
            inferred = prefs.inferred or {}
        except Exception:
            return updates

        filtered: dict[str, object] = {}
        for key, value in updates.items():
            if key == "recurring_error_tags":
                existing = inferred.get(key) or []
                if list(existing) != value:
                    filtered[key] = value
                continue
            if inferred.get(key) != value:
                filtered[key] = value
        return filtered

    def _recurring_error_tags(self, errors: list[ErrorRecord]) -> list[str]:
        tags: list[str] = []
        for error in errors:
            tags.extend(self._extract_tags(error))
        if not tags:
            return []
        counter = Counter(tags)
        recurring = [tag for tag, count in counter.items() if count >= 2]
        recurring.sort(key=lambda item: (-counter[item], item))
        return recurring[:self.MAX_TAGS]

    @staticmethod
    def _extract_tags(error: ErrorRecord) -> list[str]:
        tags: list[str] = []
        analysis = error.latest_analysis or {}
        if isinstance(analysis, dict):
            error_type = analysis.get("error_type")
            if error_type:
                tags.append(str(error_type))
        if not tags and error.cognitive_tags:
            tags.extend([str(tag) for tag in error.cognitive_tags if tag])
        return tags

    @staticmethod
    def _correction_rate(errors: list[ErrorRecord]) -> float:
        if not errors:
            return 0.0
        reviewed = sum(
            1
            for error in errors
            if (error.review_count or 0) > 0 or error.last_reviewed_at is not None
        )
        return reviewed / len(errors)
