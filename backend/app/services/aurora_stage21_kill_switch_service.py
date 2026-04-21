from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage21KillSwitchService:
    PREFIX = "aurora:stage21:killswitch:"
    DEFAULTS = {
        "skill_store_enabled": lambda: settings.SPARKLE_SKILL_STORE_ENABLED,
        "skill_selection_enabled": lambda: settings.SPARKLE_SKILL_SELECTION_ENABLED,
        "skill_share_enabled": lambda: settings.SPARKLE_SKILL_SHARE_ENABLED,
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
            if updates.get("skill_store_enabled") is not None:
                settings.SPARKLE_SKILL_STORE_ENABLED = bool(updates["skill_store_enabled"])
            if updates.get("skill_selection_enabled") is not None:
                settings.SPARKLE_SKILL_SELECTION_ENABLED = bool(updates["skill_selection_enabled"])
            if updates.get("skill_share_enabled") is not None:
                settings.SPARKLE_SKILL_SHARE_ENABLED = bool(updates["skill_share_enabled"])
        return await self.get_all()
