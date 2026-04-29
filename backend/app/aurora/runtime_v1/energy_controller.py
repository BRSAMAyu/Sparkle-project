"""
Core: execution
Phase: clarify→adapt
Stage: T3.1.6-T3.1.7 Energy Level Decision + Cost Control

T3.1.6: Every turn records Aurora energy level and upgrade/no-upgrade reason.
T3.1.7: L3/L4 have quota, cooldown, and fallback mechanisms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.aurora.runtime_v1.state import AuroraEnergyState, AuroraEnergyStore
from app.signals.types import _uid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── Energy Level Decision (T3.1.6) ─────────────────────────────────

@dataclass
class EnergyDecision:
    """Records the energy level decision for a single turn."""
    user_id: str
    current_level: str            # L0/L1/L2/L3
    previous_level: str           # what it was before
    upgrade_reason: str           # "not_upgraded" or specific reason
    wake_score: float = 0.0
    decided_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_level": self.current_level,
            "previous_level": self.previous_level,
            "upgrade_reason": self.upgrade_reason,
            "wake_score": self.wake_score,
            "decided_at": self.decided_at,
        }


class EnergyLevelDecider:
    """T3.1.6: Decides Aurora energy level each turn and records reason.

    This runs every turn and writes the decision to CausalTrace.
    Upgrade reasons:
    - "risk_detected" — L2 escalation pattern found
    - "l3_wake_eligible" — L3 wake conditions met
    - "not_upgraded" — stays at current level
    - "cooled_down" — was in cooldown, now L0
    - "aurora_inactive" — Aurora not enabled
    """

    # L2 escalation indicators → reason to upgrade to L2
    L2_TRIGGERS = {
        "knowledge_bottleneck": "knowledge_crisis",
        "transfer_failure": "knowledge_crisis",
        "execution_consistency": "execution_risk",
        "affective_pressure": "burnout_risk",
        "deadline_pressure": "deadline_risk",
    }

    def decide(
        self,
        *,
        user_id: str,
        energy: AuroraEnergyState,
        active_states: list[dict[str, Any]],
        aurora_active: bool = True,
        l3_wake_eligible: bool = False,
    ) -> EnergyDecision:
        """Determine energy level and reason for this turn."""
        previous = energy.current_level

        if not aurora_active:
            return EnergyDecision(
                user_id=user_id,
                current_level="L0",
                previous_level=previous,
                upgrade_reason="aurora_inactive",
                wake_score=0.0,
            )

        if energy.is_cooling_down:
            return EnergyDecision(
                user_id=user_id,
                current_level="L0",
                previous_level=previous,
                upgrade_reason="cooled_down",
                wake_score=energy.wake_score,
            )

        # Check L3 first (highest priority)
        if l3_wake_eligible and energy.can_user_wake:
            return EnergyDecision(
                user_id=user_id,
                current_level="L3",
                previous_level=previous,
                upgrade_reason="l3_wake_eligible",
                wake_score=energy.wake_score,
            )

        # Check L2 triggers
        state_keys = {s.get("state_key", ""): s for s in active_states}
        for key, reason in self.L2_TRIGGERS.items():
            state = state_keys.get(key)
            if state and state.get("confidence", 0) >= 0.7:
                return EnergyDecision(
                    user_id=user_id,
                    current_level="L2",
                    previous_level=previous,
                    upgrade_reason=f"risk_detected:{reason}",
                    wake_score=energy.wake_score,
                )

        # Default: L1 (light aurora always runs when active)
        return EnergyDecision(
            user_id=user_id,
            current_level="L1",
            previous_level=previous,
            upgrade_reason="not_upgraded",
            wake_score=energy.wake_score,
        )


# ── Cost Controller (T3.1.7) ────────────────────────────────────────

# Quota and cooldown limits per tier
_COST_LIMITS: dict[str, dict[str, Any]] = {
    "L3": {
        "daily_quota": 3,
        "cooldown_minutes": 360,    # 6 hours
        "min_interval_minutes": 60, # minimum 1h between L3 sessions
        "fallback": "L1_quick_calibration",
    },
    "L4": {
        "daily_quota": 5,
        "cooldown_minutes": 120,    # 2 hours
        "min_interval_minutes": 30,
        "fallback": "L4_deferred",
    },
}


class CostController:
    """T3.1.7: Enforces quota, cooldown, and fallback for L3/L4.

    Prevents resource overuse. When quota exhausted or cooldown active,
    returns fallback action instead of blocking.
    """

    def check_l3_allowed(
        self,
        energy: AuroraEnergyState,
        *,
        sprint_mode: str = "default",
    ) -> dict[str, Any]:
        """Check if L3 session is allowed. Returns decision + fallback."""
        limits = _COST_LIMITS["L3"]
        sprint_quotas = AuroraEnergyStore.DAILY_QUOTA
        quota = sprint_quotas.get(sprint_mode, limits["daily_quota"])

        if energy.is_cooling_down:
            return {
                "allowed": False,
                "reason": "cooldown_active",
                "fallback": limits["fallback"],
                "quota_remaining": max(0, quota - energy.l3_session_count_today),
            }

        remaining = max(0, quota - energy.l3_session_count_today)
        if remaining <= 0:
            return {
                "allowed": False,
                "reason": "quota_exhausted",
                "fallback": limits["fallback"],
                "quota_remaining": 0,
            }

        return {
            "allowed": True,
            "reason": "within_limits",
            "fallback": None,
            "quota_remaining": remaining,
        }

    def check_l4_allowed(
        self,
        l4_run_count_today: int = 0,
    ) -> dict[str, Any]:
        """Check if L4 analysis run is allowed."""
        limits = _COST_LIMITS["L4"]
        remaining = max(0, limits["daily_quota"] - l4_run_count_today)

        if remaining <= 0:
            return {
                "allowed": False,
                "reason": "quota_exhausted",
                "fallback": limits["fallback"],
                "quota_remaining": 0,
            }

        return {
            "allowed": True,
            "reason": "within_limits",
            "fallback": None,
            "quota_remaining": remaining,
        }

    def get_fallback_action(
        self,
        *,
        blocked_level: str,
        reason: str,
    ) -> dict[str, Any]:
        """Get the fallback action when L3/L4 is blocked."""
        if blocked_level == "L3":
            return {
                "action": "quick_calibration",
                "message": "深度校准暂时不可用，已为你安排快速校准",
                "level": "L1",
            }
        return {
            "action": "defer",
            "message": "后台分析将在下次可用时运行",
            "level": "L4",
        }
