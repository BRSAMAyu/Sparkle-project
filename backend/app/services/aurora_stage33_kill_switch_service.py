from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage33KillSwitchService:
    PREFIX = "aurora_stage33:"
    MODE_KEY = "mode"
    FEATURE_KEYS = {
        "social": "social_mode",
        "srl": "srl_mode",
        "wm_prompt": "wm_prompt_mode",
        "events": "events_mode",
    }
    SETTINGS_ATTRS = {
        "mode": "AURORA_STAGE33_MODE",
        "social_mode": "AURORA_STAGE33_SOCIAL_MODE",
        "srl_mode": "AURORA_STAGE33_SRL_MODE",
        "wm_prompt_mode": "AURORA_STAGE33_WM_PROMPT_MODE",
        "events_mode": "AURORA_STAGE33_EVENTS_MODE",
    }
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        return await self._get_flag(self.MODE_KEY, settings.AURORA_STAGE33_MODE)

    async def set_mode(self, mode: str) -> str:
        return await self._set_flag(self.MODE_KEY, "AURORA_STAGE33_MODE", mode)

    async def get_feature_mode(self, feature: str) -> str:
        master_mode = await self.get_mode()
        if master_mode == "off":
            return "off"
        feature_key = self._normalize_feature(feature)
        setting_key = self.FEATURE_KEYS[feature_key]
        settings_attr = self.SETTINGS_ATTRS[setting_key]
        return await self._get_flag(setting_key, getattr(settings, settings_attr, master_mode))

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        feature_key = self._normalize_feature(feature)
        setting_key = self.FEATURE_KEYS[feature_key]
        settings_attr = self.SETTINGS_ATTRS[setting_key]
        return await self._set_flag(setting_key, settings_attr, mode)

    async def summary(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            "social": await self.get_feature_mode("social"),
            "srl": await self.get_feature_mode("srl"),
            "wm_prompt": await self.get_feature_mode("wm_prompt"),
            "events": await self.get_feature_mode("events"),
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
            raise ValueError(f"Unknown Stage33 feature: {feature}")
        return normalized
