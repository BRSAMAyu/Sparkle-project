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


class AuroraStage20KillSwitchService:
    PREFIX = "aurora:stage20:killswitch:"
    BINDINGS = {
        "sufficiency_judge": KillSwitchBinding(
            stage="20",
            feature="sufficiency_judge",
            redis_key="sufficiency_judge_mode",
            settings_attr="AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE",
            legacy_bool_attr="SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED",
        ),
        "conflict_resolver": KillSwitchBinding(
            stage="20",
            feature="conflict_resolver",
            redis_key="conflict_resolver_mode",
            settings_attr="AURORA_STAGE20_CONFLICT_RESOLVER_MODE",
            legacy_bool_attr="SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE",
            enabled_legacy_modes=frozenset({"shadow", "live"}),
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
