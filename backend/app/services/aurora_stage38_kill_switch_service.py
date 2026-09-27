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
    stage="38",
    feature="err_replan",
    redis_key="err_replan_mode",
    settings_attr="AURORA_STAGE38_ERR_REPLAN_MODE",
    fallback_mode="shadow",
)

_PUSH_SCHEDULER_BINDING = KillSwitchBinding(
    stage="38",
    feature="push_scheduler",
    redis_key="push_scheduler_mode",
    settings_attr="AURORA_STAGE38_PUSH_SCHEDULER_MODE",
    fallback_mode="shadow",
)

# V3-FIX-443（wt730 扫雷接线）：runtime_v1 plan_turn 的 R8-P1-03 门此前调用
# get_feature_mode("aurora_runtime")，但本服务未注册该 feature——_resolve_binding
# 恒抛 ValueError 被调用方宽 except 吞掉、缺省 "shadow"，off 分支不可达（假开关）。
# 既有 test_plan_turn_kill_switch_off_returns_minimal_plan docstring 明文记载
# 「binding 接线属后续开关接入工作」，本绑定即该接线：tri-state
# AURORA_STAGE38_AURORA_RUNTIME_MODE 在场即唯一判据，legacy bool
# ENABLE_AURORA_RUNTIME_V1 仅缺席兜底（False → off → runtime 最小 TurnPlan）。
_AURORA_RUNTIME_BINDING = KillSwitchBinding(
    stage="38",
    feature="aurora_runtime",
    redis_key="aurora_runtime_mode",
    settings_attr="AURORA_STAGE38_AURORA_RUNTIME_MODE",
    legacy_bool_attr="ENABLE_AURORA_RUNTIME_V1",
    fallback_mode="live",
)


class AuroraStage38KillSwitchService:
    PREFIX = "aurora_stage38:"
    _BINDINGS = {
        "err_replan": _ERR_REPLAN_BINDING,
        "push_scheduler": _PUSH_SCHEDULER_BINDING,
        "aurora_runtime": _AURORA_RUNTIME_BINDING,
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
            "aurora_runtime_mode": await self.get_feature_mode("aurora_runtime"),
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
record_mode_gauge(
    _AURORA_RUNTIME_BINDING.stage,
    _AURORA_RUNTIME_BINDING.feature,
    resolve_settings_mode(_AURORA_RUNTIME_BINDING),
)
