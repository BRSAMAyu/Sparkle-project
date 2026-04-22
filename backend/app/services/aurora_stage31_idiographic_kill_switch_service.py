from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage31IdiographicKillSwitchService:
    PREFIX = "aurora:stage31:idiographic:"
    MODE_KEY = "mode"
    SETTINGS_ATTR = "AURORA_IDIOGRAPHIC_MODE"
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        return await self._get_flag(self.MODE_KEY, settings.AURORA_IDIOGRAPHIC_MODE)

    async def set_mode(self, mode: str) -> str:
        return await self._set_flag(self.MODE_KEY, mode)

    async def disable(self) -> str:
        return await self.set_mode("off")

    async def auto_downgrade_on_disconfirm_rate(self, ratio: float) -> str | None:
        if float(ratio or 0.0) <= 0.30:
            return None
        if await self.get_mode() != "live":
            return None
        return await self.set_mode("shadow")

    async def _get_flag(self, key: str, fallback: str) -> str:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._normalize_mode(fallback)
        raw = await redis_client.get(f"{self.PREFIX}{key}")
        if raw is None:
            return self._normalize_mode(fallback)
        return self._normalize_mode(raw)

    async def _set_flag(self, key: str, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is None:
            setattr(settings, self.SETTINGS_ATTR, normalized)
        else:
            await redis_client.set(f"{self.PREFIX}{key}", normalized)
        return normalized

    @classmethod
    def _normalize_mode(cls, value: str | Any) -> str:
        normalized = str(value or "off").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "off"
        return normalized
