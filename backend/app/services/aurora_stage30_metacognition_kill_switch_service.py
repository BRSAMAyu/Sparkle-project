from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage30MetacognitionKillSwitchService:
    PREFIX = "aurora:stage30:metacognition:"
    MODE_KEY = "mode"
    FEATURE_KEYS = {
        "dashboard": "dashboard_mode",
        "process_scaffolding": "process_scaffolding_mode",
        "fsm_combine": "fsm_combine_mode",
    }
    SETTINGS_ATTRS = {
        "mode": "AURORA_METACOG_MODE",
        "dashboard_mode": "AURORA_METACOG_DASHBOARD_MODE",
        "process_scaffolding_mode": "AURORA_METACOG_PROCESS_SCAFFOLDING_MODE",
        "fsm_combine_mode": "AURORA_METACOG_FSM_COMBINE_MODE",
    }
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        return await self._get_flag(self.MODE_KEY, settings.AURORA_METACOG_MODE)

    async def set_mode(self, mode: str) -> str:
        return await self._set_flag(self.MODE_KEY, "AURORA_METACOG_MODE", mode)

    async def get_feature_mode(self, feature: str) -> str:
        if await self.get_mode() == "off":
            return "off"
        feature_key = self._normalize_feature(feature)
        settings_attr = self.SETTINGS_ATTRS[self.FEATURE_KEYS[feature_key]]
        return await self._get_flag(
            feature_key, getattr(settings, settings_attr, "off")
        )

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        feature_key = self._normalize_feature(feature)
        settings_attr = self.SETTINGS_ATTRS[self.FEATURE_KEYS[feature_key]]
        return await self._set_flag(feature_key, settings_attr, mode)

    async def disable_all(self) -> dict[str, str]:
        await self.set_mode("off")
        states = {"mode": "off"}
        for feature in self.FEATURE_KEYS:
            states[feature] = await self.set_feature_mode(feature, "off")
        return states

    async def auto_disable_on_diagnostic_hit(
        self, hit_count: int
    ) -> dict[str, str] | None:
        if int(hit_count) <= 0:
            return None
        return await self.disable_all()

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

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_KEYS:
            raise ValueError(f"Unknown metacognition feature: {feature}")
        return normalized
