from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage27ForesightKillSwitchService:
    PREFIX = "aurora:stage27:foresight:"
    MODE_KEY = "mode"
    FEATURE_KEYS = {
        "attractor": "attractor",
        "deviation": "deviation",
        "jitai": "jitai",
    }
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._normalize_mode(settings.AURORA_FORESIGHT_MODE)
        raw = await redis_client.get(f"{self.PREFIX}{self.MODE_KEY}")
        if raw is None:
            return self._normalize_mode(settings.AURORA_FORESIGHT_MODE)
        return self._normalize_mode(raw)

    async def set_mode(self, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.set(f"{self.PREFIX}{self.MODE_KEY}", normalized)
        else:
            settings.AURORA_FORESIGHT_MODE = normalized
        return normalized

    async def get_feature_mode(self, feature: str) -> str:
        normalized_feature = self._normalize_feature(feature)
        redis_client = cache_service.redis
        if redis_client is not None:
            raw = await redis_client.get(f"{self.PREFIX}{normalized_feature}")
            if raw is not None:
                return self._normalize_mode(raw)
        return self._default_feature_mode(normalized_feature)

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        normalized_feature = self._normalize_feature(feature)
        normalized_mode = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.set(f"{self.PREFIX}{normalized_feature}", normalized_mode)
        else:
            setattr(settings, f"AURORA_FORESIGHT_{normalized_feature.upper()}", normalized_mode)
        return normalized_mode

    async def is_feature_enabled(self, feature: str) -> bool:
        if await self.get_mode() == "off":
            return False
        return await self.get_feature_mode(feature) in {"shadow", "live"}

    async def is_feature_live(self, feature: str) -> bool:
        return await self.get_mode() == "live" and await self.get_feature_mode(feature) == "live"

    async def get_all(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            **{
                feature: await self.get_feature_mode(feature)
                for feature in self.FEATURE_KEYS
            },
        }

    @classmethod
    def _normalize_mode(cls, value: str | Any) -> str:
        normalized = str(value or "off").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "off"
        return normalized

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_KEYS:
            raise ValueError(f"Unknown foresight feature: {feature}")
        return normalized

    @staticmethod
    def _default_feature_mode(feature: str) -> str:
        return AuroraStage27ForesightKillSwitchService._normalize_mode(
            getattr(settings, f"AURORA_FORESIGHT_{feature.upper()}", "live")
        )
