from __future__ import annotations


from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraStage33KillSwitchService:
    PREFIX = "aurora_stage33:"
    MASTER_BINDING = KillSwitchBinding(
        stage="33",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_STAGE33_MODE",
    )
    FEATURE_BINDINGS = {
        "social": KillSwitchBinding(
            stage="33",
            feature="social",
            redis_key="social_mode",
            settings_attr="AURORA_STAGE33_SOCIAL_MODE",
        ),
        "srl": KillSwitchBinding(
            stage="33",
            feature="srl",
            redis_key="srl_mode",
            settings_attr="AURORA_STAGE33_SRL_MODE",
        ),
        "wm_prompt": KillSwitchBinding(
            stage="33",
            feature="wm_prompt",
            redis_key="wm_prompt_mode",
            settings_attr="AURORA_STAGE33_WM_PROMPT_MODE",
        ),
        "events": KillSwitchBinding(
            stage="33",
            feature="events",
            redis_key="events_mode",
            settings_attr="AURORA_STAGE33_EVENTS_MODE",
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
            record_mode_gauge("33", self._normalize_feature(feature), "off")
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
            "social": await self.get_feature_mode("social"),
            "srl": await self.get_feature_mode("srl"),
            "wm_prompt": await self.get_feature_mode("wm_prompt"),
            "events": await self.get_feature_mode("events"),
        }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_BINDINGS:
            raise ValueError(f"Unknown Stage33 feature: {feature}")
        return normalized
