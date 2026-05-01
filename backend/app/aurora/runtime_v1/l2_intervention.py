"""
L2 Mid Aurora — proactive intervention on accumulated state patterns.

Unlike L0 (pure rules, no state) and L1 (tone/length adjustment),
L2 detects escalation patterns across multiple StateRegister entries
and triggers structural interventions: ErrorReplanBridge, adaptive
replanning, or task-type changes.

L2 fires when:
  - A single high-impact state persists with high confidence (≥0.7)
  - Multiple states form an escalation pattern together
  - Previous L1 adjustments have not resolved the issue

L2 does NOT:
  - Use LLM reasoning (that's L3)
  - Change the user's long-term model
  - Override explicit user preferences
"""
from __future__ import annotations

from typing import Any

from loguru import logger


# Minimum interval between L2 interventions for the same pattern (seconds)
_L2_COOLDOWN_SECONDS = 3600  # 1 hour

# State patterns that trigger L2 intervention
_ESCALATION_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "knowledge_crisis",
        "requires": [
            {"state_key": "knowledge_bottleneck", "min_confidence": 0.7},
            {"state_key": "transfer_failure", "min_confidence": 0.7},
        ],
        "intervention": "error_replan_bridge",
        "reason": "Knowledge bottleneck detected — trigger worked example repair",
    },
    {
        "name": "execution_collapse",
        "requires": [{"state_key": "execution_consistency", "min_confidence": 0.7, "value": "task_abandoned"}],
        "and": [{"state_key": "growth_momentum", "min_confidence": 0.6, "value": "momentum_stalled"}],
        "intervention": "adaptive_replan",
        "reason": "Execution collapsed + momentum stalled — replan with easy wins",
    },
    {
        "name": "exam_underwater",
        "requires": [{"state_key": "deadline_pressure", "min_confidence": 0.8}],
        "and": [{"state_key": "execution_consistency", "min_confidence": 0.6}],
        "intervention": "adaptive_replan",
        "reason": "High deadline pressure + execution issues — emergency replan",
    },
    {
        "name": "burnout_risk",
        "requires": [{"state_key": "affective_pressure", "min_confidence": 0.7, "value": "burnout_risk"}],
        "intervention": "reduce_load",
        "reason": "Burnout risk detected — reduce task load immediately",
    },
]


class L2InterventionEngine:
    """Detect escalation patterns in StateRegister and trigger interventions."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def check_escalation(
        self,
        user_id: str,
        active_states: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Check active states for escalation patterns.

        Returns None if no pattern matched, or a dict with:
          pattern_name, intervention, reason, matched_states
        """
        if not active_states:
            return None

        state_map = self._build_state_map(active_states)

        for pattern in _ESCALATION_PATTERNS:
            if self._matches_pattern(pattern, state_map):
                # Check cooldown — don't re-trigger within the cooldown window
                if await self._is_cooled_down(user_id, pattern["name"]):
                    await self._mark_intervention(user_id, pattern["name"])
                    matched = self._get_matched_states(pattern, state_map)
                    result = {
                        "pattern_name": pattern["name"],
                        "intervention": pattern["intervention"],
                        "reason": pattern["reason"],
                        "matched_states": matched,
                        "energy_level": "L2",
                    }
                    logger.info(
                        "L2 escalation: user={} pattern={} intervention={}",
                        user_id, pattern["name"], pattern["intervention"],
                    )
                    return result

        return None

    def _build_state_map(self, active_states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Build state_key → {value, confidence, scope} map."""
        result = {}
        for st in active_states:
            key = str(st.get("state_key", ""))
            if key:
                result[key] = {
                    "value": str(st.get("value", "")),
                    "confidence": float(st.get("confidence", 0)),
                    "scope": str(st.get("scope", "")),
                }
        return result

    def _matches_pattern(self, pattern: dict[str, Any], state_map: dict[str, dict[str, Any]]) -> bool:
        """Check if the pattern's required states are present with sufficient confidence."""
        # Check 'requires' (single condition sufficient)
        requires = pattern.get("requires", [])
        if not requires:
            return False

        requires_met = any(self._state_matches(req, state_map) for req in requires)
        if not requires_met:
            return False

        # Check 'and' conditions (all must match)
        and_conditions = pattern.get("and", [])
        if and_conditions:
            if not all(self._state_matches(cond, state_map) for cond in and_conditions):
                return False

        # Check 'or' conditions (at least one must match, if present)
        or_conditions = pattern.get("or", [])
        if or_conditions:
            if not any(self._state_matches(cond, state_map) for cond in or_conditions):
                return False

        return True

    def _state_matches(self, condition: dict[str, Any], state_map: dict[str, dict[str, Any]]) -> bool:
        """Check if a single state condition is satisfied."""
        key = condition.get("state_key", "")
        min_conf = condition.get("min_confidence", 0)
        required_value = condition.get("value")

        state = state_map.get(key)
        if not state:
            return False
        if state["confidence"] < min_conf:
            return False
        if required_value and state["value"] != required_value:
            return False
        return True

    def _get_matched_states(self, pattern: dict[str, Any], state_map: dict[str, dict[str, Any]]) -> list[str]:
        """Get list of state_keys that matched the pattern."""
        matched = []
        for condition in pattern.get("requires", []) + pattern.get("and", []) + pattern.get("or", []):
            key = condition.get("state_key", "")
            if key in state_map:
                matched.append(key)
        return list(set(matched))

    async def _is_cooled_down(self, user_id: str, pattern_name: str) -> bool:
        """Check if enough time has passed since the last intervention of this type."""
        key = f"spine:l2_intervention:{user_id}:{pattern_name}"
        try:
            existing = await self.redis.get(key)
            return existing is None
        except Exception:
            return True

    async def _mark_intervention(self, user_id: str, pattern_name: str) -> None:
        """Record that an L2 intervention was triggered (for cooldown tracking)."""
        key = f"spine:l2_intervention:{user_id}:{pattern_name}"
        try:
            await self.redis.set(key, "1", ex=_L2_COOLDOWN_SECONDS)
        except Exception:
            pass
