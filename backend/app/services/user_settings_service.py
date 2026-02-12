from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_settings import UserSettings

DEFAULT_SETTINGS: dict[str, Any] = {
    "transparency_level": 0,
    "system_update_level": 1,
    "task_reminders_enabled": True,
    "task_reminder_times": [1440, 60, 15],  # 1 day, 1 hour, 15 minutes
}


class UserSettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: UUID) -> UserSettings:
        record = await self._get_settings(user_id)
        if record:
            return record
        record = UserSettings(user_id=user_id, **DEFAULT_SETTINGS)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_settings(
        self,
        user_id: UUID,
        updates: dict[str, Any],
    ) -> UserSettings:
        record = await self.get_or_create(user_id)
        for key, value in updates.items():
            if value is None:
                continue
            if hasattr(record, key):
                setattr(record, key, value)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def _get_settings(self, user_id: UUID) -> UserSettings | None:
        result = await self.db.execute(
            select(UserSettings).where(
                UserSettings.user_id == user_id,
                UserSettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
