from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User


class LtmRolloutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_enabled(self, user_id: UUID) -> bool:
        if not settings.ENABLE_LTM_ROLLOUT:
            return True

        user_id_str = str(user_id)
        allowlist = set(settings.LTM_ROLLOUT_USER_ALLOWLIST or [])
        if user_id_str in allowlist:
            return True

        cohort_tags = set(settings.LTM_ROLLOUT_COHORT_TAGS or [])
        if cohort_tags:
            user = await self._get_user(user_id)
            if user is not None and self._has_cohort_tag(user, cohort_tags):
                return True

        percent = max(0, min(100, settings.LTM_ROLLOUT_PERCENT or 0))
        if percent <= 0:
            return False
        if percent >= 100:
            return True

        bucket = self._stable_bucket(user_id_str)
        return bucket < percent

    async def _get_user(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def _has_cohort_tag(self, user: User, cohort_tags: set[str]) -> bool:
        tag_sources: list[str] = []
        tags_attr = getattr(user, "tags", None)
        if isinstance(tags_attr, list):
            tag_sources.extend(tags_attr)
        cohort_attr = getattr(user, "cohort_tags", None)
        if isinstance(cohort_attr, list):
            tag_sources.extend(cohort_attr)
        schedule_prefs = getattr(user, "schedule_preferences", None)
        if isinstance(schedule_prefs, dict):
            schedule_tags = schedule_prefs.get("cohort_tags")
            if isinstance(schedule_tags, list):
                tag_sources.extend(schedule_tags)
        return any(tag in cohort_tags for tag in tag_sources)

    def _stable_bucket(self, user_id: str) -> int:
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100
