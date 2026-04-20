from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage19KillSwitchService:
    PREFIX = "aurora:stage19:killswitch:"
    DEFAULTS = {
        "working_memory_enabled": lambda: settings.SPARKLE_WORKING_MEMORY_ENABLED,
        "llm_extractor_enabled": lambda: settings.SPARKLE_LLM_EXTRACTOR_ENABLED,
        "consolidation_enabled": lambda: settings.SPARKLE_CONSOLIDATION_ENABLED,
    }

    async def is_enabled(self, key: str) -> bool:
        default_getter = self.DEFAULTS[key]
        redis_client = cache_service.redis
        if redis_client is None:
            return bool(default_getter())
        raw = await redis_client.get(f"{self.PREFIX}{key}")
        if raw is None:
            return bool(default_getter())
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    async def get_all(self) -> dict[str, bool]:
        return {key: await self.is_enabled(key) for key in self.DEFAULTS}

    async def set_flags(self, updates: dict[str, Any]) -> dict[str, bool]:
        redis_client = cache_service.redis
        if redis_client is not None:
            for key, value in updates.items():
                if key in self.DEFAULTS and value is not None:
                    await redis_client.set(
                        f"{self.PREFIX}{key}",
                        "true" if bool(value) else "false",
                    )
        else:
            for key, value in updates.items():
                if key == "working_memory_enabled" and value is not None:
                    settings.SPARKLE_WORKING_MEMORY_ENABLED = bool(value)
                if key == "llm_extractor_enabled" and value is not None:
                    settings.SPARKLE_LLM_EXTRACTOR_ENABLED = bool(value)
                if key == "consolidation_enabled" and value is not None:
                    settings.SPARKLE_CONSOLIDATION_ENABLED = bool(value)
        return await self.get_all()
