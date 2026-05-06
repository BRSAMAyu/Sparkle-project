"""First-Minute Experience (FME) kill switch service.

Phase-0 foundation for the Entry Wire and Execution Wire vision tracks.
Following the AuroraStageNN pattern in backend/app/services/aurora_stage*.py
so that ops, drills, and rule guards can use the same primitives.

Tri-state modes (per CLAUDE.md governance):
  off    — legacy behavior, no analyzer/UI
  shadow — analyzer runs server-side and emits CausalTrace, UI unchanged
  live   — full UI + analyzer in user path
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
    """Tri-state kill switches for First-Minute Experience features.

    Two features registered in Phase 0:
      goal_first_minute      — natural-language intent analysis at goal creation
      task_card_protocol_v2  — render TaskCardProtocol fields in expanded card

    Additional features (entry_wire route, causal_receipt, etc.) will be
    appended in later phases. Per the Chief Architect's decision, we register
    incrementally rather than reserving empty switches.
    """

    PREFIX = "fme:"

    FEATURE_BINDINGS = {
        "goal_first_minute": KillSwitchBinding(
            stage="fme",
            feature="goal_first_minute",
            redis_key="goal_first_minute_mode",
            settings_attr="FME_GOAL_FIRST_MINUTE_MODE",
        ),
        "task_card_protocol_v2": KillSwitchBinding(
            stage="fme",
            feature="task_card_protocol_v2",
            redis_key="task_card_protocol_mode",
            settings_attr="FME_TASK_CARD_PROTOCOL_MODE",
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
            "task_card_protocol_v2": await self.get_feature_mode("task_card_protocol_v2"),
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
