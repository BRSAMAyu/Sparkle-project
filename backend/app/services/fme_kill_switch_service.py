"""First-Minute Experience (FME) kill switch service.

Phase-0 foundation for the Entry Wire vision track.
Following the AuroraStageNN pattern in backend/app/services/aurora_stage*.py
so that ops, drills, and rule guards can use the same primitives.

Tri-state modes (per CLAUDE.md governance):
  off    — legacy behavior, no analyzer/UI
  shadow — analyzer runs server-side and emits CausalTrace, UI unchanged
  live   — full UI + analyzer in user path

V3-FIX-345 如实化裁决（wt655，FIX-341 假开关先例）：
只注册有真实读者的特性。原 task_card_protocol_v2 绑定全仓零读者
（TaskCardProtocol 渲染链 tasks.py card-protocol 端点不查开关），且渲染
协议无 analyzer 语义、三态对其无定义，已撤——勿在补齐渲染链读者前挂回。

翻转面如实：本服务无运行时翻转 API（set_feature_mode 零生产调用方）。
部署期翻转 = 改 FME_GOAL_FIRST_MINUTE_MODE 后重启（env 判据）；运维临场
覆盖 = 直接写 Redis 键 fme:goal_first_minute_mode（read_mode 每次读取）。
"""

from __future__ import annotations

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class FmeKillSwitchService:
    """Tri-state kill switch for First-Minute Experience features.

    One feature registered in Phase 0:
      goal_first_minute — natural-language intent analysis at goal creation
      (reader: app/api/v1/goal_intent.py analyze_goal_intent)

    Additional features will be appended only together with their production
    reader (registered-iff-read contract, guarded by
    tests/unit/test_v3_fix345_fme_dead_switch_removed.py and
    scripts/guards/check_rule_fme_kill_switch_registered.py). Per the Chief
    Architect's decision, we register incrementally rather than reserving
    empty switches.
    """

    PREFIX = "fme:"

    FEATURE_BINDINGS = {
        "goal_first_minute": KillSwitchBinding(
            stage="fme",
            feature="goal_first_minute",
            redis_key="goal_first_minute_mode",
            settings_attr="FME_GOAL_FIRST_MINUTE_MODE",
        ),
    }

    async def get_feature_mode(self, feature: str) -> str:
        feature_key = self._normalize_feature(feature)
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.FEATURE_BINDINGS[feature_key],
        )

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        """运维翻转面（当前零生产调用方：无 admin 运行时 API，仅工具/演练可用）."""
        feature_key = self._normalize_feature(feature)
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.FEATURE_BINDINGS[feature_key],
            mode=mode,
        )

    async def summary(self) -> dict[str, str]:
        return {
            "goal_first_minute": await self.get_feature_mode("goal_first_minute"),
        }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        normalized = str(feature or "").strip().lower()
        if normalized not in cls.FEATURE_BINDINGS:
            raise ValueError(f"Unknown FME feature: {feature}")
        return normalized

    @staticmethod
    def record_gauge(feature: str, mode: str) -> None:
        """Helper for callers that resolved mode locally and want a gauge sample."""
        record_mode_gauge("fme", feature, mode)


fme_kill_switch_service = FmeKillSwitchService()
