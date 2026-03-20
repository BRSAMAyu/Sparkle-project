from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user_settings import UserSettings

DEFAULT_SETTINGS: dict[str, Any] = {
    "transparency_level": 0,
    "system_update_level": 1,
    "ai_reasoning_mode": "balanced",
    "task_reminders_enabled": True,
    "task_reminder_times": [1440, 60, 15],  # 1 day, 1 hour, 15 minutes
}


class UserSettingsService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

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

        # 清除相关缓存
        await self._invalidate_cache(user_id)

        return record

    async def get_ai_usage_summary(self, user_id: UUID) -> dict[str, Any]:
        redis_client = await self._ensure_redis()
        current_mode = "balanced"
        try:
            current_mode = (await self.get_or_create(user_id)).ai_reasoning_mode or "balanced"
        except Exception:
            current_mode = "balanced"

        mode_limits = {
            "fast": int(getattr(settings, "AI_MODE_FAST_DAILY_REQUEST_LIMIT", 120)),
            "balanced": int(getattr(settings, "AI_MODE_BALANCED_DAILY_REQUEST_LIMIT", 60)),
            "deep": int(getattr(settings, "AI_MODE_DEEP_DAILY_REQUEST_LIMIT", 24)),
        }

        items: list[dict[str, Any]] = []
        if redis_client is not None:
            from app.orchestration.token_tracker import get_token_tracker

            tracker = get_token_tracker(redis_client)
            items = await tracker.get_ai_usage_summary(str(user_id), mode_limits=mode_limits)
        else:
            items = [
                {
                    "mode": mode,
                    "label": {"fast": "敏捷", "balanced": "均衡", "deep": "深思"}[mode],
                    "requests_used": 0,
                    "requests_limit": limit,
                    "requests_remaining": limit,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }
                for mode, limit in mode_limits.items()
            ]

        from datetime import datetime

        return {
            "current_mode": current_mode,
            "items": items,
            "generated_at": datetime.utcnow(),
        }

    async def _invalidate_cache(self, user_id: UUID) -> None:
        """清除与用户设置相关的缓存"""
        if not self.redis:
            try:
                from app.core.cache import cache_service

                if cache_service.redis:
                    self.redis = cache_service.redis
            except Exception:
                pass

        if self.redis:
            try:
                # 清除日程相关缓存
                await self.redis.delete(f"schedule:active_hours:{user_id}")
                # 清除个性化配置缓存
                await self.redis.delete(f"personalization:{user_id}")
                logger.debug(f"Invalidated cache for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache for user {user_id}: {e}")

    async def _ensure_redis(self):
        if self.redis:
            return self.redis
        try:
            from app.core.cache import cache_service

            self.redis = cache_service.redis
        except Exception:
            self.redis = None
        return self.redis

    async def _get_settings(self, user_id: UUID) -> UserSettings | None:
        result = await self.db.execute(
            select(UserSettings).where(
                UserSettings.user_id == user_id,
                UserSettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
