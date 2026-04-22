from __future__ import annotations

from typing import Any

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    is_enabled_mode,
    is_live_mode,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraStage27ForesightKillSwitchService:
    PREFIX = "aurora:stage27:foresight:"
    MASTER_BINDING = KillSwitchBinding(
        stage="27",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_FORESIGHT_MODE",
    )
    FEATURE_BINDINGS = {
        "attractor": KillSwitchBinding(
            stage="27",
            feature="attractor",
            redis_key="attractor",
            settings_attr="AURORA_FORESIGHT_ATTRACTOR",
        ),
        "deviation": KillSwitchBinding(
            stage="27",
            feature="deviation",
            redis_key="deviation",
            settings_attr="AURORA_FORESIGHT_DEVIATION",
        ),
        "jitai": KillSwitchBinding(
            stage="27",
            feature="jitai",
            redis_key="jitai",
            settings_attr="AURORA_FORESIGHT_JITAI",
        ),
    }

    async def get_mode(self) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
        )

    async def set_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
            mode=mode,
        )

    async def get_feature_mode(self, feature: str) -> str:
        feature_key = self._normalize_feature(feature)
        if await self.get_mode() == "off":
            record_mode_gauge("27", feature_key, "off")
            return "off"
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.FEATURE_BINDINGS[feature_key],
        )

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        feature_key = self._normalize_feature(feature)
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.FEATURE_BINDINGS[feature_key],
            mode=mode,
        )

    async def is_feature_enabled(self, feature: str) -> bool:
        return is_enabled_mode(await self.get_feature_mode(feature))

    async def is_feature_live(self, feature: str) -> bool:
        return is_live_mode(await self.get_feature_mode(feature))

    async def get_all(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            **{
                feature: await self.get_feature_mode(feature)
                for feature in self.FEATURE_BINDINGS
            },
        }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_BINDINGS:
            raise ValueError(f"Unknown foresight feature: {feature}")
        return normalized
