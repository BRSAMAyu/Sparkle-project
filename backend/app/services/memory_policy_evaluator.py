from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_memory_settings import UserMemorySettings


@dataclass(frozen=True)
class MemoryPolicyDecision:
    allowed: bool
    reason: Optional[str] = None


class MemoryPolicyEvaluator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        user_id: UUID,
        kind: str,
        pref_key: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> MemoryPolicyDecision:
        settings_record = await self._get_settings(user_id)
        if settings_record is None:
            return MemoryPolicyDecision(allowed=True)

        if not settings_record.enabled:
            return MemoryPolicyDecision(allowed=False, reason="disabled")

        if kind == "preference" and not settings_record.allow_preferences:
            return MemoryPolicyDecision(allowed=False, reason="preferences_disabled")
        if kind == "goal" and not settings_record.allow_goals:
            return MemoryPolicyDecision(allowed=False, reason="goals_disabled")
        if kind == "episodic" and not settings_record.allow_episodic:
            return MemoryPolicyDecision(allowed=False, reason="episodic_disabled")

        blocked_pref_keys = settings_record.blocked_pref_keys or []
        if kind == "preference" and pref_key and pref_key in blocked_pref_keys:
            return MemoryPolicyDecision(allowed=False, reason="pref_key_blocked")

        blocked_sources = settings_record.blocked_sources or []
        if source_type and source_type in blocked_sources:
            return MemoryPolicyDecision(allowed=False, reason="source_blocked")

        return MemoryPolicyDecision(allowed=True)

    async def _get_settings(self, user_id: UUID) -> Optional[UserMemorySettings]:
        result = await self.db.execute(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id,
                UserMemorySettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
