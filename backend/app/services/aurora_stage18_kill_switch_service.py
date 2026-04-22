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


class AuroraStage18KillSwitchService:
    PREFIX = "aurora:stage18:killswitch:"
    BINDINGS = {
        "aggregator_enabled": KillSwitchBinding(
            stage="18",
            feature="aggregator",
            redis_key="aggregator_mode",
            settings_attr="AURORA_STAGE18_AGGREGATOR_MODE",
            legacy_bool_attr="SPARKLE_AGGREGATOR_ENABLED",
        ),
        "push_policy_enabled": KillSwitchBinding(
            stage="18",
            feature="push_policy",
            redis_key="push_policy_mode",
            settings_attr="AURORA_STAGE18_PUSH_POLICY_MODE",
            legacy_bool_attr="SPARKLE_PUSH_POLICY_ENABLED",
        ),
        "push_delivery_enabled": KillSwitchBinding(
            stage="18",
            feature="push_delivery",
            redis_key="push_delivery_mode",
            settings_attr="AURORA_STAGE18_PUSH_DELIVERY_MODE",
            legacy_bool_attr="SPARKLE_PUSH_DELIVERY_ENABLED",
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
