from __future__ import annotations

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraStage35KillSwitchService:
    PREFIX = "aurora_stage35:"
    MASTER_BINDING = KillSwitchBinding(
        stage="35",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_STAGE35_MODE",
    )
    FEATURE_BINDINGS = {
        "metacog_router": KillSwitchBinding(
            stage="35",
            feature="metacog_router",
            redis_key="metacog_router_mode",
            settings_attr="AURORA_STAGE35_METACOG_ROUTER_MODE",
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
        master_mode = await self.get_mode()
        if master_mode == "off":
            record_mode_gauge("35", self._normalize_feature(feature), "off")
            return "off"
        feature_key = self._normalize_feature(feature)
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

    async def summary(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            "metacog_router_mode": await self.get_feature_mode("metacog_router"),
        }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_BINDINGS:
            raise ValueError(f"Unknown Stage35 feature: {feature}")
        return normalized
