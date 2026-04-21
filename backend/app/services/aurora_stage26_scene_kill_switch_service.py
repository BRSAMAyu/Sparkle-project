from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage26SceneKillSwitchService:
    PREFIX = "aurora:stage26:scene:"
    MODE_KEY = "mode"
    QUALITY_STREAK_KEY = "quality_below_threshold_streak"
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._normalize_mode(settings.AURORA_SCENE_MODE)
        raw = await redis_client.get(f"{self.PREFIX}{self.MODE_KEY}")
        if raw is None:
            return self._normalize_mode(settings.AURORA_SCENE_MODE)
        return self._normalize_mode(raw)

    async def set_mode(self, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.set(f"{self.PREFIX}{self.MODE_KEY}", normalized)
        else:
            settings.AURORA_SCENE_MODE = normalized
        return normalized

    async def record_quality_average(self, average_quality: float) -> str:
        normalized_quality = max(0.0, min(1.0, float(average_quality)))
        threshold = float(settings.AURORA_SCENE_QUALITY_THRESHOLD)
        redis_client = cache_service.redis
        if normalized_quality >= threshold:
            if redis_client is not None:
                await redis_client.delete(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}")
            else:
                settings._aurora_scene_quality_streak = 0
            return await self.get_mode()

        if redis_client is None:
            if self._normalize_mode(settings.AURORA_SCENE_MODE) == "live":
                streak = int(getattr(settings, "_aurora_scene_quality_streak", 0)) + 1
                settings._aurora_scene_quality_streak = streak
                if streak >= 3:
                    settings.AURORA_SCENE_MODE = "shadow"
            return self._normalize_mode(settings.AURORA_SCENE_MODE)

        streak = await redis_client.incr(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}")
        await redis_client.expire(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}", 86400)
        if int(streak) >= 3 and await self.get_mode() == "live":
            await redis_client.set(f"{self.PREFIX}{self.MODE_KEY}", "shadow")
            return "shadow"
        return await self.get_mode()

    async def reset_quality_streak(self) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}")
        elif hasattr(settings, "_aurora_scene_quality_streak"):
            settings._aurora_scene_quality_streak = 0

    @classmethod
    def _normalize_mode(cls, value: str | Any) -> str:
        normalized = str(value or "off").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "off"
        return normalized
