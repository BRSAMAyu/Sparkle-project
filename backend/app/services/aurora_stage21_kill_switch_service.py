from __future__ import annotations

from typing import Any

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    is_enabled_mode,
    is_live_mode,
    read_mode,
    write_mode,
)


class AuroraStage21KillSwitchService:
    PREFIX = "aurora:stage21:killswitch:"
    BINDINGS = {
        "skill_store_enabled": KillSwitchBinding(
            stage="21",
            feature="skill_store",
            redis_key="skill_store_mode",
            settings_attr="AURORA_STAGE21_SKILL_STORE_MODE",
            legacy_bool_attr="SPARKLE_SKILL_STORE_ENABLED",
        ),
        "skill_selection_enabled": KillSwitchBinding(
            stage="21",
            feature="skill_selection",
            redis_key="skill_selection_mode",
            settings_attr="AURORA_STAGE21_SKILL_SELECTION_MODE",
            legacy_bool_attr="SPARKLE_SKILL_SELECTION_ENABLED",
            enabled_legacy_modes=frozenset({"live"}),
        ),
        "skill_share_enabled": KillSwitchBinding(
            stage="21",
            feature="skill_share",
            redis_key="skill_share_mode",
            settings_attr="AURORA_STAGE21_SKILL_SHARE_MODE",
            legacy_bool_attr="SPARKLE_SKILL_SHARE_ENABLED",
            enabled_legacy_modes=frozenset({"live"}),
        ),
    }

    async def get_feature_mode(self, key: str) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BINDINGS[key],
        )

    async def is_enabled(self, key: str) -> bool:
        return is_enabled_mode(await self.get_feature_mode(key))

    async def is_live(self, key: str) -> bool:
        return is_live_mode(await self.get_feature_mode(key))

    async def get_all(self) -> dict[str, str]:
        return {key: await self.get_feature_mode(key) for key in self.BINDINGS}

    async def set_flags(self, updates: dict[str, Any]) -> dict[str, str]:
        for key, value in updates.items():
            if key in self.BINDINGS and value is not None:
                await write_mode(
                    redis_client=cache_service.redis,
                    prefix=self.PREFIX,
                    binding=self.BINDINGS[key],
                    mode=value,
                )
        return await self.get_all()
