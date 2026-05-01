from __future__ import annotations


from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraStage30MetacognitionKillSwitchService:
    PREFIX = "aurora:stage30:metacognition:"
    MASTER_BINDING = KillSwitchBinding(
        stage="30",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_METACOG_MODE",
    )
    FEATURE_BINDINGS = {
        "dashboard": KillSwitchBinding(
            stage="30",
            feature="dashboard",
            redis_key="dashboard",
            settings_attr="AURORA_METACOG_DASHBOARD_MODE",
        ),
        "process_scaffolding": KillSwitchBinding(
            stage="30",
            feature="process_scaffolding",
            redis_key="process_scaffolding",
            settings_attr="AURORA_METACOG_PROCESS_SCAFFOLDING_MODE",
        ),
        "fsm_combine": KillSwitchBinding(
            stage="30",
            feature="fsm_combine",
            redis_key="fsm_combine",
            settings_attr="AURORA_METACOG_FSM_COMBINE_MODE",
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
        if await self.get_mode() == "off":
            record_mode_gauge("30", self._normalize_feature(feature), "off")
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

    async def disable_all(self) -> dict[str, str]:
        await self.set_mode("off")
        states = {"mode": "off"}
        for feature in self.FEATURE_BINDINGS:
            states[feature] = await self.set_feature_mode(feature, "off")
        return states

    async def auto_disable_on_diagnostic_hit(
        self, hit_count: int
    ) -> dict[str, str] | None:
        if int(hit_count) <= 0:
            return None
        return await self.disable_all()

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_BINDINGS:
            raise ValueError(f"Unknown metacognition feature: {feature}")
        return normalized
