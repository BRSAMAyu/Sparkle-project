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


class AuroraStage38KillSwitchService:
    PREFIX = "aurora_stage38:"
    FEATURE_KEYS = {
        "err_replan": "err_replan_mode",
        "push_scheduler": "push_scheduler_mode",
    }
    SETTINGS_ATTRS = {
        "err_replan_mode": "AURORA_STAGE38_ERR_REPLAN_MODE",
        "push_scheduler_mode": "AURORA_STAGE38_PUSH_SCHEDULER_MODE",
    }
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_feature_mode(self, feature: str) -> str:
        feature_key = self._normalize_feature(feature)
        key = self.FEATURE_KEYS[feature_key]
        settings_attr = self.SETTINGS_ATTRS[key]
        mode = await self._get_flag(key, getattr(settings, settings_attr, "shadow"))
        self._record_gauge(feature_key, mode)
        return mode

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        feature_key = self._normalize_feature(feature)
        key = self.FEATURE_KEYS[feature_key]
        settings_attr = self.SETTINGS_ATTRS[key]
        normalized = await self._set_flag(key, settings_attr, mode)
        self._record_gauge(feature_key, normalized)
        return normalized

    async def summary(self) -> dict[str, str]:
        return {
            "err_replan_mode": await self.get_feature_mode("err_replan"),
            "push_scheduler_mode": await self.get_feature_mode("push_scheduler"),
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
        normalized = str(value or "shadow").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "shadow"
        return normalized

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_KEYS:
            raise ValueError(f"Unknown Stage38 feature: {feature}")
        return normalized

    @staticmethod
    def _record_gauge(feature: str, mode: str) -> None:
        KILL_SWITCH_MODE.labels(stage="38", feature=feature).set(_mode_value(mode))
