from __future__ import annotations

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    resolve_settings_mode,
    write_mode,
)

_ERR_REPLAN_BINDING = KillSwitchBinding(
    stage="stage38",
    feature="err_replan",
    redis_key="err_replan_mode",
    settings_attr="AURORA_STAGE38_ERR_REPLAN_MODE",
    fallback_mode="shadow",
)

_PUSH_SCHEDULER_BINDING = KillSwitchBinding(
    stage="stage38",
    feature="push_scheduler",
    redis_key="push_scheduler_mode",
    settings_attr="AURORA_STAGE38_PUSH_SCHEDULER_MODE",
    fallback_mode="shadow",
)


class AuroraStage38KillSwitchService:
    PREFIX = "aurora_stage38:"
    _BINDINGS = {
        "err_replan": _ERR_REPLAN_BINDING,
        "push_scheduler": _PUSH_SCHEDULER_BINDING,
    }

    async def get_feature_mode(self, feature: str) -> str:
        binding = self._resolve_binding(feature)
        mode = await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=binding,
        )
        return mode

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        binding = self._resolve_binding(feature)
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=binding,
            mode=mode,
        )

    async def summary(self) -> dict[str, str]:
        return {
            "err_replan_mode": await self.get_feature_mode("err_replan"),
            "push_scheduler_mode": await self.get_feature_mode("push_scheduler"),
        }

    @classmethod
    def _resolve_binding(cls, feature: str) -> KillSwitchBinding:
        key = str(feature or "").strip().lower()
        if key not in cls._BINDINGS:
            raise ValueError(f"Unknown Stage38 feature: {feature}")
        return cls._BINDINGS[key]


record_mode_gauge(
    _ERR_REPLAN_BINDING.stage,
    _ERR_REPLAN_BINDING.feature,
    resolve_settings_mode(_ERR_REPLAN_BINDING),
)
record_mode_gauge(
    _PUSH_SCHEDULER_BINDING.stage,
    _PUSH_SCHEDULER_BINDING.feature,
    resolve_settings_mode(_PUSH_SCHEDULER_BINDING),
)
