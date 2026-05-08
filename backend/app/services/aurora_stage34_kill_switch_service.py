from __future__ import annotations

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraStage34KillSwitchService:
    PREFIX = "aurora_stage34:"
    MASTER_BINDING = KillSwitchBinding(
        stage="34",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_STAGE34_MODE",
    )
    FEATURE_BINDINGS = {
        "error_bridge": KillSwitchBinding(
            stage="34",
            feature="error_bridge",
            redis_key="error_bridge_mode",
            settings_attr="AURORA_STAGE34_ERROR_BRIDGE_MODE",
        ),
        "capsule": KillSwitchBinding(
            stage="34",
            feature="capsule",
            redis_key="capsule_mode",
            settings_attr="AURORA_STAGE34_CAPSULE_MODE",
        ),
        "journey_subscribers": KillSwitchBinding(
            stage="34",
            feature="journey_subscribers",
            redis_key="journey_subscribers_enabled",
            settings_attr="AURORA_STAGE34_JOURNEY_SUBSCRIBERS_MODE",
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
            record_mode_gauge("34", self._normalize_feature(feature), "off")
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
            "error_bridge_mode": await self.get_feature_mode("error_bridge"),
            "capsule_mode": await self.get_feature_mode("capsule"),
            "journey_subscribers_enabled": await self.get_feature_mode("journey_subscribers"),
        }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_BINDINGS:
            raise ValueError(f"Unknown Stage34 feature: {feature}")
        return normalized
