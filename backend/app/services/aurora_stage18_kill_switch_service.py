from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage18KillSwitchService:
    PREFIX = "aurora:stage18:killswitch:"
    DEFAULTS = {
        "aggregator_enabled": lambda: settings.SPARKLE_AGGREGATOR_ENABLED,
        "push_policy_enabled": lambda: settings.SPARKLE_PUSH_POLICY_ENABLED,
        "push_delivery_enabled": lambda: settings.SPARKLE_PUSH_DELIVERY_ENABLED,
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
                    await redis_client.set(f"{self.PREFIX}{key}", "true" if bool(value) else "false")
        else:
            for key, value in updates.items():
                if key == "aggregator_enabled" and value is not None:
                    settings.SPARKLE_AGGREGATOR_ENABLED = bool(value)
                if key == "push_policy_enabled" and value is not None:
                    settings.SPARKLE_PUSH_POLICY_ENABLED = bool(value)
                if key == "push_delivery_enabled" and value is not None:
                    settings.SPARKLE_PUSH_DELIVERY_ENABLED = bool(value)
        return await self.get_all()

