from __future__ import annotations

from typing import Any

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    is_enabled_mode,
    normalize_mode,
    read_mode,
    record_mode_gauge,
    write_mode,
)

_STAGE37_BINDING = KillSwitchBinding(
    stage="37",
    feature="llm_safety",
    redis_key="aurora:stage37:llm_safety",
    settings_attr="AURORA_STAGE37_LLM_SAFETY_MODE",
    legacy_bool_attr=None,
    fallback_mode="live",
    enabled_mode="live",
)


class AuroraStage37LLMSafetyKillSwitchService:
    def __init__(self) -> None:
        self._cached_mode: str | None = None

    async def get_mode(self) -> str:
        redis_client = cache_service.redis
        mode = await read_mode(
            redis_client=redis_client,
            prefix="sparkle:",
            binding=_STAGE37_BINDING,
        )
        self._cached_mode = mode
        return mode

    async def set_mode(self, mode: Any) -> str:
        redis_client = cache_service.redis
        normalized = await write_mode(
            redis_client=redis_client,
            prefix="sparkle:",
            binding=_STAGE37_BINDING,
            mode=mode,
        )
        self._cached_mode = normalized
        return normalized

    async def get_enabled(self) -> bool:
        mode = await self.get_mode()
        return is_enabled_mode(mode)

    def current_enabled(self) -> bool:
        mode = self._cached_mode
        if mode is None:
            from app.config import settings

            mode = normalize_mode(
                getattr(settings, _STAGE37_BINDING.settings_attr, _STAGE37_BINDING.fallback_mode),
                fallback=_STAGE37_BINDING.fallback_mode,
            )
            self._cached_mode = mode
        record_mode_gauge(_STAGE37_BINDING.stage, _STAGE37_BINDING.feature, mode)
        return is_enabled_mode(mode)

    def current_mode(self) -> str:
        mode = self._cached_mode
        if mode is None:
            from app.config import settings

            mode = normalize_mode(
                getattr(settings, _STAGE37_BINDING.settings_attr, _STAGE37_BINDING.fallback_mode),
                fallback=_STAGE37_BINDING.fallback_mode,
            )
            self._cached_mode = mode
        record_mode_gauge(_STAGE37_BINDING.stage, _STAGE37_BINDING.feature, mode)
        return mode

    async def set_enabled(self, enabled: bool) -> bool:
        await self.set_mode("live" if enabled else "off")
        return enabled

    def reset_local_cache(self) -> None:
        self._cached_mode = None


aurora_stage37_llm_safety_kill_switch_service = AuroraStage37LLMSafetyKillSwitchService()
