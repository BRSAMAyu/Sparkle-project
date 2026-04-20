from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_push_opt_in import UserPushOptIn


DEFAULTS = {
    "enabled": False,
    "allow_commitment_follow_up": False,
    "allow_engagement_recovery": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "timezone": "Asia/Shanghai",
}


class UserPushOptInService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: UUID) -> UserPushOptIn:
        result = await self.db.execute(
            select(UserPushOptIn).where(
                UserPushOptIn.user_id == user_id,
                UserPushOptIn.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is not None:
            return record
        record = UserPushOptIn(user_id=user_id, **DEFAULTS)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update(self, user_id: UUID, updates: dict) -> UserPushOptIn:
        record = await self.get_or_create(user_id)
        for key, value in updates.items():
            if value is None:
                continue
            if hasattr(record, key):
                setattr(record, key, value)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def disable_category(self, user_id: UUID, category: str) -> UserPushOptIn:
        record = await self.get_or_create(user_id)
        if category == "commitment_follow_up":
            record.allow_commitment_follow_up = False
        if category == "engagement_recovery":
            record.allow_engagement_recovery = False
        if not record.allow_commitment_follow_up and not record.allow_engagement_recovery:
            record.enabled = False
        await self.db.commit()
        await self.db.refresh(record)
        return record

