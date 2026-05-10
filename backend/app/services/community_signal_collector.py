"""
Community signal collector - infer social learning preferences from community activity.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.cache import cache_service
from app.core.datetime_utils import _utcnow
from app.db.session import AsyncSessionLocal
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import classify_band_with_hysteresis, recency_weight


class CommunitySignalCollector:
    """Collect community interactions and update inferred preferences."""

    WINDOW_SIZE = 40
    WINDOW_TTL_SECONDS = 14 * 24 * 3600
    UPDATE_EVERY = 8
    MIN_SAMPLE = 5

    def __init__(self, redis=None) -> None:
        self.redis = redis or cache_service.redis

    async def record_interaction(
        self,
        user_id: UUID,
        action: str,
        context: str,
        timestamp: datetime | None = None,
    ) -> None:
        if not self.redis:
            return

        ts = timestamp or _utcnow()
        entry = {
            "ts": ts.isoformat(),
            "hour": ts.hour,
            "action": str(action or "").lower(),
            "context": str(context or "group").lower(),
        }
        await self._store_entry(user_id, entry)

        counter = await self._increment_counter(user_id)
        if counter % self.UPDATE_EVERY != 0:
            return

        entries = await self._load_entries(user_id)
        if not entries:
            return

        updates = await self._build_updates(user_id, entries)
        if not updates:
            return

        try:
            async with AsyncSessionLocal() as db:
                service = ProfileWriteService(db, self.redis)
                await service.update_inferred_preference(
                    user_id=user_id,
                    updates=updates,
                    source="ai_inferred",
                )
        except Exception as exc:
            logger.warning("CommunitySignalCollector failed to persist updates: %s", exc)

    async def _store_entry(self, user_id: UUID, entry: dict[str, Any]) -> None:
        key = f"user:community:signals:{user_id}"
        try:
            await self.redis.lpush(key, json.dumps(entry, ensure_ascii=False))
            await self.redis.ltrim(key, 0, self.WINDOW_SIZE - 1)
            await self.redis.expire(key, self.WINDOW_TTL_SECONDS)
        except Exception as exc:
            logger.warning("Failed to cache community signal entry: %s", exc)

    async def _increment_counter(self, user_id: UUID) -> int:
        key = f"user:community:signals:count:{user_id}"
        try:
            counter = await self.redis.incr(key)
            await self.redis.expire(key, self.WINDOW_TTL_SECONDS)
            return int(counter)
        except Exception as exc:
            logger.warning("Failed to increment community signal counter: %s", exc)
            return 0

    async def _load_entries(self, user_id: UUID) -> list[dict[str, Any]]:
        key = f"user:community:signals:{user_id}"
        try:
            raw_entries = await self.redis.lrange(key, 0, self.WINDOW_SIZE - 1)
        except Exception as exc:
            logger.warning("Failed to load community signal entries: %s", exc)
            return []
        entries: list[dict[str, Any]] = []
        for raw in raw_entries or []:
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            if isinstance(parsed, dict):
                entries.append(parsed)
        return list(reversed(entries))

    async def _build_updates(self, user_id: UUID, entries: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(entries)
        if total < self.MIN_SAMPLE:
            return {}

        weighted_total = 0.0
        weighted_group = 0.0
        weighted_contribution = 0.0
        for entry in entries:
            weight = self._entry_weight(entry)
            weighted_total += weight
            if entry.get("context") == "group":
                weighted_group += weight
            if entry.get("action") in {"post", "comment"}:
                weighted_contribution += weight

        if weighted_total < self.MIN_SAMPLE * 0.6:
            return {}

        previous_engagement = await self._current_inferred_value(user_id, "community_engagement_level")
        engagement_level = classify_band_with_hysteresis(
            weighted_total,
            previous_engagement if isinstance(previous_engagement, str) else None,
            low_enter=6.0,
            high_enter=18.0,
            low_exit=8.0,
            high_exit=16.0,
            low_label="passive",
            mid_label="moderate",
            high_label="active",
        )
        social_preference = weighted_group / weighted_total if weighted_total else 0.0
        contribution_rate = weighted_contribution / weighted_total if weighted_total else 0.0

        return {
            "community_engagement_level": engagement_level,
            "social_learning_preference": round(social_preference, 3),
            "content_contribution_rate": round(contribution_rate, 3),
        }

    @staticmethod
    def _entry_weight(entry: dict[str, Any]) -> float:
        raw_ts = entry.get("ts")
        if not raw_ts:
            return 0.25
        try:
            parsed = datetime.fromisoformat(str(raw_ts))
        except Exception:
            return 0.25
        return recency_weight(parsed, now=_utcnow(), half_life_days=5.0, min_weight=0.25)

    async def _current_inferred_value(self, user_id: UUID, key: str) -> object | None:
        try:
            async with AsyncSessionLocal() as db:
                service = ProfileWriteService(db, self.redis)
                prefs = await service.pref_service.get_preferences(user_id)
        except Exception:
            return None
        inferred = prefs.inferred or {}
        return inferred.get(key)
