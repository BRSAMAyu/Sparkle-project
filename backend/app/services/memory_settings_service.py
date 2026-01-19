from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.business_metrics import MEMORY_SETTINGS_UPDATE_TOTAL
from app.models.user_memory_settings import UserMemorySettings


DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": True,
    "allow_preferences": True,
    "allow_goals": True,
    "allow_episodic": True,
    "capture_level": "medium",
    "blocked_pref_keys": [],
    "blocked_sources": [],
}


class MemorySettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: UUID) -> UserMemorySettings:
        record = await self._get_settings(user_id)
        if record:
            return record
        record = UserMemorySettings(user_id=user_id, **DEFAULT_SETTINGS)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_settings(
        self,
        user_id: UUID,
        updates: Dict[str, Any],
    ) -> UserMemorySettings:
        record = await self.get_or_create(user_id)
        before = _snapshot(record)

        for key, value in updates.items():
            if value is None:
                continue
            if hasattr(record, key):
                setattr(record, key, value)

        await self.db.commit()
        await self.db.refresh(record)
        diff = _diff_snapshot(before, _snapshot(record))
        if diff:
            MEMORY_SETTINGS_UPDATE_TOTAL.inc()
            logger.info(
                "Memory settings updated user_id={user_id} changes={changes}",
                user_id=user_id,
                changes=diff,
            )
        return record

    async def _get_settings(self, user_id: UUID) -> Optional[UserMemorySettings]:
        result = await self.db.execute(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id,
                UserMemorySettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


def _snapshot(record: UserMemorySettings) -> Dict[str, Any]:
    return {
        "enabled": record.enabled,
        "allow_preferences": record.allow_preferences,
        "allow_goals": record.allow_goals,
        "allow_episodic": record.allow_episodic,
        "capture_level": record.capture_level,
        "blocked_pref_keys": list(record.blocked_pref_keys or []),
        "blocked_sources": list(record.blocked_sources or []),
    }


def _diff_snapshot(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    for key, value in after.items():
        if before.get(key) != value:
            if key in {"blocked_pref_keys", "blocked_sources"}:
                diff[key] = {
                    "from_count": len(before.get(key, [])),
                    "to_count": len(value or []),
                }
            else:
                diff[key] = {"from": before.get(key), "to": value}
    return diff
