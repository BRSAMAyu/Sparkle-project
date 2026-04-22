from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aurora_stage21 import UserSkill
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService


class SkillContentReader:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.kill_switches = AuroraStage21KillSwitchService()

    async def fetch(self, *, skill_id: UUID, user_id: UUID) -> UserSkill | None:
        if not await self.kill_switches.is_enabled("skill_store_enabled"):
            return None
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.id == skill_id,
                UserSkill.user_id == user_id,
                UserSkill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
