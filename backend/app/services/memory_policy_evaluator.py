from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_memory_settings import UserMemorySettings


@dataclass(frozen=True)
class MemoryPolicyDecision:
    allowed: bool
    reason: str | None = None


class MemoryPolicyEvaluator:
    _ALIAS_MAP = {
        "preferred_focus_duration": "focus_duration_preference",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        user_id: UUID,
        kind: str,
        pref_key: str | None = None,
        source_type: str | None = None,
        source_lane: str | None = None,
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
        if kind == "episodic" and source_lane == "inferred_extraction":
            if not getattr(settings_record, "allow_inferred_episodic", True):
                return MemoryPolicyDecision(allowed=False, reason="inferred_episodic_disabled")

        blocked_pref_keys = settings_record.blocked_pref_keys or []
        if kind == "preference" and pref_key:
            candidate_keys = self._candidate_preference_keys(pref_key)
            if any(key in blocked_pref_keys for key in candidate_keys):
                return MemoryPolicyDecision(allowed=False, reason="pref_key_blocked")

        blocked_sources = settings_record.blocked_sources or []
        if source_type and source_type in blocked_sources:
            return MemoryPolicyDecision(allowed=False, reason="source_blocked")

        return MemoryPolicyDecision(allowed=True)

    async def _get_settings(self, user_id: UUID) -> UserMemorySettings | None:
        result = await self.db.execute(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id,
                UserMemorySettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _candidate_preference_keys(pref_key: str) -> set[str]:
        keys = {pref_key}
        if pref_key.endswith("_signal"):
            keys.add(pref_key.removesuffix("_signal"))
        alias = MemoryPolicyEvaluator._ALIAS_MAP.get(pref_key)
        if alias:
            keys.add(alias)
        return keys

    @staticmethod
    def expand_blocked_preference_key(pref_key: str) -> set[str]:
        keys = MemoryPolicyEvaluator._candidate_preference_keys(pref_key)
        if not pref_key.endswith("_signal"):
            keys.add(f"{pref_key}_signal")
        for inferred_key, explicit_key in MemoryPolicyEvaluator._ALIAS_MAP.items():
            if pref_key == explicit_key:
                keys.add(inferred_key)
        return keys
