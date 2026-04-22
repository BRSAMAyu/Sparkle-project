from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service
from app.core.metrics import KILL_SWITCH_MODE


def _mode_value(mode: str) -> int:
    normalized = str(mode or "off").strip().lower()
    if normalized == "live":
        return 2
    if normalized == "shadow":
        return 1
    return 0


class AuroraStage39KillSwitchService:
    PREFIX = "aurora_stage39:"
    MODE_KEY = "mode"
    FEATURE_KEYS = {
        "scaffolding_prompt": "scaffolding_prompt_mode",
        "cogload_route": "cogload_route_mode",
        "galaxy_inject": "galaxy_inject_mode",
    }
    SETTINGS_ATTRS = {
        "mode": "AURORA_STAGE39_MODE",
        "scaffolding_prompt_mode": "AURORA_STAGE39_SCAFFOLDING_PROMPT_MODE",
        "cogload_route_mode": "AURORA_STAGE39_COGLOAD_ROUTE_MODE",
        "galaxy_inject_mode": "AURORA_STAGE39_GALAXY_INJECT_MODE",
    }
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        mode = await self._get_flag(self.MODE_KEY, settings.AURORA_STAGE39_MODE)
        self._record_gauge("mode", mode)
        return mode

    async def set_mode(self, mode: str) -> str:
        normalized = await self._set_flag(self.MODE_KEY, "AURORA_STAGE39_MODE", mode)
        self._record_gauge("mode", normalized)
        return normalized

    async def get_feature_mode(self, feature: str) -> str:
        master_mode = await self.get_mode()
        if master_mode == "off":
            self._record_gauge(feature, "off")
            return "off"
        feature_key = self._normalize_feature(feature)
        setting_key = self.FEATURE_KEYS[feature_key]
        settings_attr = self.SETTINGS_ATTRS[setting_key]
        mode = await self._get_flag(setting_key, getattr(settings, settings_attr, master_mode))
        self._record_gauge(feature_key, mode)
        return mode

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        feature_key = self._normalize_feature(feature)
        setting_key = self.FEATURE_KEYS[feature_key]
        settings_attr = self.SETTINGS_ATTRS[setting_key]
        normalized = await self._set_flag(setting_key, settings_attr, mode)
        self._record_gauge(feature_key, normalized)
        return normalized

    async def summary(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            "scaffolding_prompt_mode": await self.get_feature_mode("scaffolding_prompt"),
            "cogload_route_mode": await self.get_feature_mode("cogload_route"),
            "galaxy_inject_mode": await self.get_feature_mode("galaxy_inject"),
        }

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
            raise ValueError(f"Unknown Stage39 feature: {feature}")
        return normalized

    @staticmethod
    def _record_gauge(feature: str, mode: str) -> None:
        KILL_SWITCH_MODE.labels(stage="39", feature=feature).set(_mode_value(mode))
