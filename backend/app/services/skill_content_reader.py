from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.aurora_stage21 import UserSkill


class SkillContentReader:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def fetch(self, *, skill_id: UUID, user_id: UUID) -> UserSkill | None:
        if not settings.SPARKLE_SKILL_STORE_ENABLED:
            return None
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.id == skill_id,
                UserSkill.user_id == user_id,
                UserSkill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
