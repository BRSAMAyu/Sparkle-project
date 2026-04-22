from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service
from app.core.metrics import KILL_SWITCH_MODE


class AuroraStage37LLMSafetyKillSwitchService:
    PREFIX = "aurora_stage37:"
    KEY = "llm_safety_enabled"

    def __init__(self) -> None:
        self._cached_enabled: bool | None = None

    async def get_enabled(self) -> bool:
        redis_client = cache_service.redis
        if redis_client is None:
            enabled = self._normalize_enabled(settings.AURORA_STAGE37_LLM_SAFETY_ENABLED)
            self._cached_enabled = enabled
            self._record_gauge(enabled)
            return enabled

        raw = await redis_client.get(f"{self.PREFIX}{self.KEY}")
        enabled = self._normalize_enabled(
            settings.AURORA_STAGE37_LLM_SAFETY_ENABLED if raw is None else raw
        )
        self._cached_enabled = enabled
        self._record_gauge(enabled)
        return enabled

    async def set_enabled(self, enabled: bool) -> bool:
        normalized = self._normalize_enabled(enabled)
        redis_client = cache_service.redis
        if redis_client is None:
            settings.AURORA_STAGE37_LLM_SAFETY_ENABLED = normalized
        else:
            await redis_client.set(f"{self.PREFIX}{self.KEY}", "true" if normalized else "false")
        self._cached_enabled = normalized
        self._record_gauge(normalized)
        return normalized

    def current_enabled(self) -> bool:
        enabled = self._cached_enabled
        if enabled is None:
            enabled = self._normalize_enabled(settings.AURORA_STAGE37_LLM_SAFETY_ENABLED)
            self._cached_enabled = enabled
        self._record_gauge(enabled)
        return enabled

    def reset_local_cache(self) -> None:
        self._cached_enabled = None

    @staticmethod
    def _normalize_enabled(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        return normalized not in {"", "0", "false", "off", "no"}

    @staticmethod
    def _record_gauge(enabled: bool) -> None:
        KILL_SWITCH_MODE.labels(stage="37", feature="llm_safety").set(1 if enabled else 0)


aurora_stage37_llm_safety_kill_switch_service = AuroraStage37LLMSafetyKillSwitchService()
