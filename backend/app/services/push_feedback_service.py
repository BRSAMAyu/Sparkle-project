"""
推送反馈服务 - 处理推送交互并更新推断偏好
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, UTC
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.notification import PushHistory
from app.models.user import PushPreference
from app.services.profile_write_service import ProfileWriteService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PushFeedbackService:
    """推送反馈服务"""

    WINDOW_DAYS = 7
    MIN_SAMPLE = 5
    IGNORE_RATE_THRESHOLD = 0.7
    CURIOSITY_IGNORE_THRESHOLD = 0.8
    INACTIVE_HOUR_IGNORE_COUNT = 3

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client or cache_service.redis
        self.profile_write_service = ProfileWriteService(db, self.redis)

    async def process_interaction(
        self,
        user_id: UUID,
        push_id: UUID,
        action: str,
        timestamp: datetime | None = None,
    ) -> None:
        action = self._normalize_action(action)
        if action is None:
            logger.warning("Unknown push interaction action=%s user_id=%s", action, user_id)
            return

        ts = timestamp or _utcnow()
        trigger_type = await self._record_push_history(user_id, push_id, action, ts)
        await self._store_interaction(user_id, push_id, action, ts, trigger_type)
        await self._backfill_ignored(user_id, ts)

        interactions = await self._load_recent_interactions(user_id)
        updates = self._build_inferred_updates(interactions)
        if updates:
            await self.profile_write_service.update_inferred_preference(
                user_id=user_id,
                updates=updates,
                source="ai_inferred",
            )
            await self._sync_consecutive_ignores(user_id, updates.get("consecutive_ignores"))

    async def _record_push_history(
        self,
        user_id: UUID,
        push_id: UUID,
        action: str,
        timestamp: datetime,
    ) -> str | None:
        if not push_id:
            return None
        result = await self.db.execute(
            select(PushHistory).where(
                PushHistory.id == push_id,
                PushHistory.user_id == user_id,
            )
        )
        history = result.scalar_one_or_none()
        if history is None:
            return None

        history.interaction_type = action
        history.status = self._map_status(action)
        history.interacted_at = timestamp
        await self.db.commit()
        return history.trigger_type

    async def _sync_consecutive_ignores(self, user_id: UUID, value: int | None) -> None:
        if value is None:
            return
        result = await self.db.execute(
            select(PushPreference).where(PushPreference.user_id == user_id)
        )
        push_pref = result.scalar_one_or_none()
        if push_pref is None:
            return
        push_pref.consecutive_ignores = int(value)
        await self.db.commit()

    async def _backfill_ignored(self, user_id: UUID, now: datetime) -> None:
        cutoff = now - timedelta(hours=2)
        result = await self.db.execute(
            select(PushHistory).where(
                PushHistory.user_id == user_id,
                PushHistory.status == "sent",
                PushHistory.created_at <= cutoff,
            )
        )
        histories = list(result.scalars().all())
        if not histories:
            return
        for history in histories:
            history.interaction_type = "ignored"
            history.status = self._map_status("ignored")
            history.interacted_at = now
            await self._store_interaction(
                user_id=user_id,
                push_id=history.id,
                action="ignored",
                timestamp=history.interacted_at or now,
                trigger_type=history.trigger_type,
            )
        await self.db.commit()

    async def _store_interaction(
        self,
        user_id: UUID,
        push_id: UUID,
        action: str,
        timestamp: datetime,
        trigger_type: str | None,
    ) -> None:
        if not self.redis:
            return
        day_key = timestamp.strftime("%Y%m%d")
        key = f"user:push:interaction:{user_id}:{day_key}"
        entry = {
            "push_id": str(push_id),
            "action": action,
            "timestamp": timestamp.isoformat(),
            "hour": timestamp.hour,
            "trigger_type": trigger_type,
        }
        try:
            await self.redis.rpush(key, json.dumps(entry, ensure_ascii=False))
            await self.redis.expire(key, self.WINDOW_DAYS * 24 * 3600)
        except Exception as exc:
            logger.warning("Failed to cache push interaction: %s", exc)

    async def _load_recent_interactions(self, user_id: UUID) -> list[dict[str, object]]:
        if not self.redis:
            return []
        now = _utcnow()
        interactions: list[dict[str, object]] = []
        for day_offset in range(self.WINDOW_DAYS):
            day = now - timedelta(days=day_offset)
            key = f"user:push:interaction:{user_id}:{day.strftime('%Y%m%d')}"
            try:
                values = await self.redis.lrange(key, 0, -1)
            except Exception as exc:
                logger.warning("Failed to load push interactions: %s", exc)
                continue
            for raw in values or []:
                try:
                    parsed = json.loads(raw)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    interactions.append(parsed)
        return interactions

    def _build_inferred_updates(self, interactions: list[dict[str, object]]) -> dict[str, object]:
        if not interactions:
            return {}

        total = len(interactions)
        ignored = sum(
            1 for item in interactions
            if str(item.get("action")) in {"dismissed", "ignored"}
        )
        ignore_rate = ignored / total if total else 0.0

        updates: dict[str, object] = {}

        if total >= self.MIN_SAMPLE and ignore_rate > self.IGNORE_RATE_THRESHOLD:
            consecutive = self._count_consecutive_ignores(interactions)
            updates["consecutive_ignores"] = consecutive
            updates["push_receptivity"] = round(1 - ignore_rate, 3)
            updates["push_receptivity_last_updated"] = _utcnow().isoformat()

        curiosity_updates = self._curiosity_ignore_rate(interactions)
        if curiosity_updates:
            updates.update(curiosity_updates)

        inactive_hours = self._inactive_hours(interactions)
        if inactive_hours:
            updates["inactive_push_hours"] = inactive_hours

        return updates

    def _curiosity_ignore_rate(self, interactions: list[dict[str, object]]) -> dict[str, object]:
        curiosity = [
            item for item in interactions
            if str(item.get("trigger_type")) == "curiosity"
        ]
        if not curiosity:
            return {}
        total = len(curiosity)
        ignored = sum(
            1 for item in curiosity
            if str(item.get("action")) in {"dismissed", "ignored"}
        )
        if total >= 3 and (ignored / total) > self.CURIOSITY_IGNORE_THRESHOLD:
            return {"curiosity_push_receptivity": "low"}
        return {}

    def _inactive_hours(self, interactions: list[dict[str, object]]) -> list[int]:
        counter: Counter[int] = Counter()
        for item in interactions:
            if str(item.get("action")) not in {"dismissed", "ignored"}:
                continue
            hour_raw = item.get("hour")
            if hour_raw is None:
                continue
            try:
                hour = int(hour_raw)
            except (TypeError, ValueError):
                continue
            if 0 <= hour <= 23:
                counter[hour] += 1
        inactive = [
            hour for hour, count in counter.items()
            if count >= self.INACTIVE_HOUR_IGNORE_COUNT
        ]
        return sorted(inactive)

    @staticmethod
    def _count_consecutive_ignores(interactions: list[dict[str, object]]) -> int:
        sorted_items = sorted(
            interactions,
            key=lambda item: str(item.get("timestamp") or ""),
            reverse=True,
        )
        count = 0
        for item in sorted_items:
            action = str(item.get("action"))
            if action in {"dismissed", "ignored"}:
                count += 1
            elif action == "opened":
                break
        return count

    @staticmethod
    def _normalize_action(action: str) -> str | None:
        action = str(action or "").strip().lower()
        if action in {"opened", "clicked"}:
            return "opened"
        if action in {"dismissed", "ignored"}:
            return action
        return None

    @staticmethod
    def _map_status(action: str) -> str:
        if action == "opened":
            return "clicked"
        if action in {"dismissed", "ignored"}:
            return "dismissed"
        return "sent"
