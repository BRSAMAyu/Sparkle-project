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


class AuroraStage34KillSwitchService:
    PREFIX = "aurora_stage34:"
    MODE_KEY = "mode"
    FEATURE_KEYS = {
        "error_bridge": "error_bridge_mode",
        "capsule": "capsule_mode",
        "journey_subscribers": "journey_subscribers_enabled",
    }
    SETTINGS_ATTRS = {
        "mode": "AURORA_STAGE34_MODE",
        "error_bridge_mode": "AURORA_STAGE34_ERROR_BRIDGE_MODE",
        "capsule_mode": "AURORA_STAGE34_CAPSULE_MODE",
        "journey_subscribers_enabled": "AURORA_STAGE34_JOURNEY_SUBSCRIBERS_ENABLED",
    }
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        mode = await self._get_flag(self.MODE_KEY, settings.AURORA_STAGE34_MODE)
        self._record_gauge("mode", mode)
        return mode

    async def set_mode(self, mode: str) -> str:
        normalized = await self._set_flag(self.MODE_KEY, "AURORA_STAGE34_MODE", mode)
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
            "error_bridge_mode": await self.get_feature_mode("error_bridge"),
            "capsule_mode": await self.get_feature_mode("capsule"),
            "journey_subscribers_enabled": await self.get_feature_mode("journey_subscribers"),
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
            raise ValueError(f"Unknown Stage34 feature: {feature}")
        return normalized

    @staticmethod
    def _record_gauge(feature: str, mode: str) -> None:
        KILL_SWITCH_MODE.labels(stage="34", feature=feature).set(_mode_value(mode))
