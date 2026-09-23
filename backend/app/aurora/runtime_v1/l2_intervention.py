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

A-01 契约接线（aurora_decision.v1）：L2 是 Aurora 控制决策面的第一个契约化
决策点——模式命中时 ``check_escalation`` 的结果 dict 携带 ``aurora_decision``
（``AuroraDecisionContract.to_dict()``），``decide()`` 则对全部结局（命中/
无命中/冷却）返回契约（含 no_action）。可观测性：两条 decision_id 结构化
日志（check_escalation/decide 各一）；``pipeline_context["l2_escalation"]``
键写后暂无生产读者，喂入 spine 真通道（feed_aurora_decision）属 A-04——
见 RUNTIME_MAP S-01「写后待 A-04 喂」。映射纪律见
v3-output/A-01/RUNTIME_MAP.md：cognition_tier=l2_intervention，
evidence=signal://<state_key>，governance_mode=live（经 spine 实际生效）。
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.aurora_decision import AuroraDecisionContract
from app.models.execution_intent import ExecutionMode

# Minimum interval between L2 interventions for the same pattern (seconds)
_L2_COOLDOWN_SECONDS = 3600  # 1 hour

#: L2 内部干预名 → AURORA_V3 §2 干预目录映射（A-01 契约词表成员；冻结面：
#: 新增 _ESCALATION_PATTERNS 干预时必须同步此映射，wiring 测试强制全员覆盖）。
#: error_replan_bridge/adaptive_replan 都是计划级结构干预 → rescope；
#: reduce_load 是负荷抑制 → pause（状态不好时更克制）。
L2_INTERVENTION_TO_CATALOG: dict[str, str] = {
    "error_replan_bridge": "rescope",
    "adaptive_replan": "rescope",
    "reduce_load": "pause",
}

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
          pattern_name, intervention, reason, matched_states,
          energy_level, aurora_decision (A-01: 契约载荷，仅当 user_id 可解析为
          UUID 时携带——生产 spine 链路恒为 UUID；解析失败时保持纯 legacy dict)
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
                    contract = self._build_decision_contract(user_id, pattern, matched, active_states)
                    if contract is not None:
                        result["aurora_decision"] = contract.to_dict()
                    # P2-3（R2 返修）：契约决策的最小生产可观测点——结构化 decision_id
                    # 日志（pipeline_context["l2_escalation"] 的喂入通道归 A-04，见
                    # RUNTIME_MAP S-01「写后待 A-04 喂」）。
                    logger.info(
                        "L2 escalation: user={} pattern={} intervention={} aurora_decision_id={} catalog={}",
                        user_id,
                        pattern["name"],
                        pattern["intervention"],
                        contract.decision_id_or_compute() if contract is not None else "-",
                        contract.intervention_type if contract is not None else "-",
                    )
                    return result

        return None

    # ── A-01 契约面 ─────────────────────────────────────────────────────

    async def decide(self, user_id: str, active_states: list[dict[str, Any]]) -> AuroraDecisionContract | None:
        """AuroraDecisionContract 视图：对全部 L2 结局给出契约（含 no_action）。

        纯决策面、无副作用（不写冷却键、不发干预）；生效路径仍是
        ``check_escalation``（legacy 语义 + 契约载荷）。返回 None 当且仅当：
        (a) user_id 不可解析为 UUID（契约前置不满足），(b) 干预未登记目录映射，
        或 (c) 内部异常（不 raise，与 spine 既有降级路径一致）。governance_mode
        恒为 live——L2 干预经 spine 管道实际生效。
        """
        try:
            parsed = self._parse_user_uuid(user_id)
            if parsed is None:
                return None

            if not active_states:
                return self._no_action_contract(parsed, "no_active_states", (), None, active_states)

            state_map = self._build_state_map(active_states)
            for pattern in _ESCALATION_PATTERNS:
                if self._matches_pattern(pattern, state_map):
                    matched = self._get_matched_states(pattern, state_map)
                    if await self._is_cooled_down(user_id, pattern["name"]):
                        fired = self._build_decision_contract(user_id, pattern, matched, active_states)
                        # P2-3：与 check_escalation 同款 decision_id 结构化日志（纯决策面
                        # 的观测点；本方法无副作用、不写冷却键）。
                        logger.info(
                            "L2 decide (fired): user={} pattern={} aurora_decision_id={} catalog={}",
                            user_id,
                            pattern["name"],
                            fired.decision_id_or_compute() if fired is not None else "-",
                            fired.intervention_type if fired is not None else "-",
                        )
                        return fired
                    # 命中但冷却中：显式 no_action（证据保留，供观测冷却压制量）
                    return self._no_action_contract(
                        parsed, "cooldown_active", tuple(f"signal://{key}" for key in matched),
                        str(pattern["name"]), active_states,
                    )
            return self._no_action_contract(parsed, "no_matching_pattern", (), None, active_states)
        except Exception as exc:  # noqa: BLE001 — resilience: decide 永不 raise
            logger.warning("L2 decide() degraded (user={}): {}", user_id, exc)
            return None

    def _build_decision_contract(
        self,
        user_id: str,
        pattern: dict[str, Any],
        matched_states: list[str],
        active_states: list[dict[str, Any]],
    ) -> AuroraDecisionContract | None:
        """把一次命中的 L2 模式映射为 aurora_decision.v1 契约（映射冻结于
        L2_INTERVENTION_TO_CATALOG；user_id 非 UUID → None 保持 legacy 行为）。"""
        parsed = self._parse_user_uuid(user_id)
        if parsed is None:
            logger.debug("L2 decision contract skipped for non-UUID user_id: {}", user_id)
            return None
        intervention = str(pattern["intervention"])
        catalog_type = L2_INTERVENTION_TO_CATALOG.get(intervention)
        if catalog_type is None:
            # 新增干预未登记映射：宁可无契约也不产词表外 intervention_type
            logger.warning("L2 intervention {!r} has no catalog mapping; contract skipped", intervention)
            return None
        return AuroraDecisionContract(
            user_id=parsed,
            intervention_type=catalog_type,
            rationale_summary=str(pattern["reason"]),
            cognition_tier="l2_intervention",
            execution_mode=ExecutionMode.HYBRID,
            governance_mode="live",
            trigger_point="l2_escalation",
            input_context_hash=self._context_hash(active_states),
            evidence_refs=tuple(f"signal://{key}" for key in matched_states),
            annotations={"l2_intervention": intervention, "pattern": str(pattern["name"])},
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )

    def _no_action_contract(
        self,
        parsed_user_id: UUID,
        reason: str,
        evidence_refs: tuple[str, ...],
        pattern_name: str | None,
        active_states: list[dict[str, Any]],
    ) -> AuroraDecisionContract:
        annotations = {"l2_intervention": "none"}
        if pattern_name:
            annotations["pattern"] = pattern_name
        return AuroraDecisionContract(
            user_id=parsed_user_id,
            intervention_type="no_action",
            rationale_summary=f"L2 escalation check: {reason}",
            cognition_tier="l2_intervention",
            execution_mode=None,
            governance_mode="live",
            trigger_point="l2_escalation",
            input_context_hash=self._context_hash(active_states),
            evidence_refs=evidence_refs,
            no_action_reason=reason,
            annotations=annotations,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )

    @staticmethod
    def _parse_user_uuid(user_id: str) -> UUID | None:
        try:
            return UUID(str(user_id))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _context_hash(active_states: list[dict[str, Any]]) -> str:
        """输入状态集的规范化短哈希（decision_id 的输入锚点；不含 PII 原文）。"""
        canonical = sorted(
            (
                str(state.get("state_key") or ""),
                str(state.get("value") or ""),
                round(float(state.get("confidence") or 0.0), 4),
            )
            for state in active_states
        )
        return hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]

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
            logger.opt(exception=True).warning(
                "L2 intervention cooldown write failed for user={} pattern={}", user_id, pattern_name
            )
