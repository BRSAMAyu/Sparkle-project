from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage23KillSwitchService:
    PREFIX = "aurora:stage23:killswitch:"
    MODE_KEY = "bayesian_mode"
    DEFAULT_MODES = {"off", "shadow", "live_canary"}

    async def get_mode(self) -> str:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._normalize_mode(settings.AURORA_BAYESIAN_MODE)
        raw = await redis_client.get(f"{self.PREFIX}{self.MODE_KEY}")
        if raw is None:
            return self._normalize_mode(settings.AURORA_BAYESIAN_MODE)
        return self._normalize_mode(raw)

    async def set_mode(self, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.set(f"{self.PREFIX}{self.MODE_KEY}", normalized)
        else:
            settings.AURORA_BAYESIAN_MODE = normalized
        return normalized

    async def get_all(self) -> dict[str, Any]:
        return {
            "bayesian_mode": await self.get_mode(),
            "live_canary_percent": self.live_canary_percent(),
        }

    @staticmethod
    def live_canary_percent() -> int:
        try:
            return max(0, min(5, int(settings.AURORA_BAYESIAN_LIVE_CANARY_PERCENT)))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _normalize_mode(cls, value: str | Any) -> str:
        normalized = str(value or "off").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "off"
        return normalized
