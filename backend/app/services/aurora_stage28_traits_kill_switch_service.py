from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage28TraitsKillSwitchService:
    PREFIX = "aurora:stage28:traits:"
    MODE_KEY = "mode"
    NLP_MODE_KEY = "nlp_mode"
    COLDSTART_MODE_KEY = "coldstart_mode"
    BIAS_STREAK_KEY = "bias_above_threshold_streak"
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        return await self._get_flag(self.MODE_KEY, settings.AURORA_TRAITS_MODE)

    async def get_nlp_mode(self) -> str:
        if await self.get_mode() == "off":
            return "off"
        return await self._get_flag(self.NLP_MODE_KEY, settings.AURORA_TRAITS_NLP_MODE)

    async def get_coldstart_mode(self) -> str:
        if await self.get_mode() == "off":
            return "off"
        return await self._get_flag(self.COLDSTART_MODE_KEY, settings.AURORA_TRAITS_COLDSTART_MODE)

    async def set_mode(self, mode: str) -> str:
        return await self._set_flag(self.MODE_KEY, "AURORA_TRAITS_MODE", mode)

    async def set_nlp_mode(self, mode: str) -> str:
        normalized = await self._set_flag(self.NLP_MODE_KEY, "AURORA_TRAITS_NLP_MODE", mode)
        if normalized != "off":
            await self.reset_bias_streak()
        return normalized

    async def set_coldstart_mode(self, mode: str) -> str:
        return await self._set_flag(self.COLDSTART_MODE_KEY, "AURORA_TRAITS_COLDSTART_MODE", mode)

    async def record_bias_rate(self, bias_rate: float) -> str:
        normalized = max(0.0, min(1.0, float(bias_rate)))
        threshold = float(settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD)
        redis_client = cache_service.redis
        if normalized <= threshold:
            await self.reset_bias_streak()
            return await self.get_nlp_mode()

        if redis_client is None:
            streak = int(getattr(settings, "_aurora_traits_bias_streak", 0)) + 1
            settings._aurora_traits_bias_streak = streak
            if streak >= 3 and self._normalize_mode(settings.AURORA_TRAITS_NLP_MODE) != "off":
                settings.AURORA_TRAITS_NLP_MODE = "off"
            return self._normalize_mode(settings.AURORA_TRAITS_NLP_MODE)

        streak = await redis_client.incr(f"{self.PREFIX}{self.BIAS_STREAK_KEY}")
        await redis_client.expire(f"{self.PREFIX}{self.BIAS_STREAK_KEY}", 86400 * 7)
        if int(streak) >= 3 and await self.get_nlp_mode() != "off":
            await redis_client.set(f"{self.PREFIX}{self.NLP_MODE_KEY}", "off")
            return "off"
        return await self.get_nlp_mode()

    async def reset_bias_streak(self) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"{self.PREFIX}{self.BIAS_STREAK_KEY}")
            return
        settings._aurora_traits_bias_streak = 0

    async def _get_flag(self, key: str, fallback: str) -> str:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._normalize_mode(fallback)
        raw = await redis_client.get(f"{self.PREFIX}{key}")
        if raw is None:
            return self._normalize_mode(fallback)
        return self._normalize_mode(raw)

    async def _set_flag(self, key: str, settings_attr: str, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is None:
            setattr(settings, settings_attr, normalized)
        else:
            await redis_client.set(f"{self.PREFIX}{key}", normalized)
        return normalized

    @classmethod
    def _normalize_mode(cls, value: str | Any) -> str:
        normalized = str(value or "off").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "off"
        return normalized
