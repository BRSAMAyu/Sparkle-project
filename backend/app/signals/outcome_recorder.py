"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine Layer 8

Outcome Recorder — 记录干预结果，执行最小因果归因。
第一版用固定规则归因，不做因果推断。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.types import (
    CausalTrace,
    OutcomeRecord,
    _uid,
)


# ── 归因规则 ─────────────────────────────────────────────────────────
# 基于 expected_outcome 和 actual_outcome 字段的固定规则归因。

_ATTRIBUTION_RULES: dict[str, dict[str, Any]] = {
    "task_started_and_completed": {
        "effective_conditions": {
            "completed": True,
        },
        "effective_attribution": "effective",
        "effective_confidence": 0.8,
        "insufficient_conditions": {
            "completed": False,
            "started": True,
        },
        "insufficient_hypothesis": "task_completed_but_intervention_may_be_insufficient",
        "next_policy": "evaluate_knowledge_barrier",
    },
    "user_response": {
        "effective_conditions": {
            "user_responded": True,
        },
        "effective_attribution": "effective",
        "effective_confidence": 0.6,
        "insufficient_conditions": {
            "user_responded": False,
        },
        "insufficient_hypothesis": "user_did_not_respond",
        "next_policy": "reduce_frequency",
    },
    "behavioral_change": {
        "effective_conditions": {
            "behavior_changed": True,
        },
        "effective_attribution": "effective",
        "effective_confidence": 0.7,
        "insufficient_conditions": {
            "behavior_changed": False,
        },
        "insufficient_hypothesis": "no_behavioral_change_detected",
        "next_policy": "escalate_or_try_different_approach",
    },
}


class OutcomeRecorder:
    """记录干预结果并执行最小因果归因。"""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def record_outcome(
        self,
        *,
        trace: CausalTrace,
        intervention: str,
        reason: str,
        expected_outcome: str,
        actual_outcome: dict[str, Any],
    ) -> OutcomeRecord:
        """
        记录干预的实际结果，执行归因分析。

        Returns:
            OutcomeRecord with attribution filled in.
        """
        attribution, confidence, hypothesis, next_policy = self._attribute(
            expected_outcome, actual_outcome,
        )

        record = OutcomeRecord(
            outcome_id=_uid("or"),
            causal_trace_id=trace.trace_id,
            intervention=intervention,
            reason=reason,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            attribution=attribution,
            attribution_confidence=confidence,
            new_hypothesis=hypothesis,
            next_policy_suggestion=next_policy,
        )

        # Store outcome record
        import json
        key = f"spine:outcome:{record.outcome_id}"
        await self.redis.set(key, json.dumps(record.to_dict()), ex=720 * 3600)  # 30 days

        # Link to trace
        trace_key = f"spine:trace:{trace.trace_id}"
        raw = await self.redis.get(trace_key)
        if raw:
            trace_data = json.loads(raw)
            trace_data["outcome_record_id"] = record.outcome_id
            await self.redis.set(trace_key, json.dumps(trace_data), ex=720 * 3600)

        logger.info(
            "OutcomeRecord: {} trace={} attribution={} confidence={:.2f}",
            record.outcome_id, trace.trace_id,
            record.attribution, record.attribution_confidence,
        )

        return record

    async def get_outcome(self, outcome_id: str) -> OutcomeRecord | None:
        """获取 OutcomeRecord。"""
        import json
        raw = await self.redis.get(f"spine:outcome:{outcome_id}")
        if not raw:
            return None
        return OutcomeRecord.from_dict(json.loads(raw))

    async def get_outcome_for_trace(self, trace_id: str) -> OutcomeRecord | None:
        """获取 CausalTrace 对应的 OutcomeRecord。"""
        import json
        trace_key = f"spine:trace:{trace_id}"
        raw = await self.redis.get(trace_key)
        if not raw:
            return None
        trace_data = json.loads(raw)
        outcome_id = trace_data.get("outcome_record_id")
        if not outcome_id:
            return None
        return await self.get_outcome(outcome_id)

    def _attribute(
        self,
        expected_outcome: str,
        actual_outcome: dict[str, Any],
    ) -> tuple[str, float, str | None, str | None]:
        """
        固定规则归因。

        Returns:
            (attribution, confidence, new_hypothesis, next_policy_suggestion)
        """
        rules = _ATTRIBUTION_RULES.get(expected_outcome)
        if not rules:
            return "inconclusive", 0.0, None, None

        # Check effective conditions
        effective_conds = rules.get("effective_conditions", {})
        if self._conditions_met(effective_conds, actual_outcome):
            return (
                rules["effective_attribution"],
                rules["effective_confidence"],
                None,
                None,
            )

        # Check insufficient conditions
        insufficient_conds = rules.get("insufficient_conditions", {})
        if self._conditions_met(insufficient_conds, actual_outcome):
            return (
                "insufficient",
                0.6,
                rules.get("insufficient_hypothesis"),
                rules.get("next_policy"),
            )

        return "inconclusive", 0.3, "unexpected_outcome_pattern", None

    @staticmethod
    def _conditions_met(conditions: dict[str, Any], actual: dict[str, Any]) -> bool:
        """检查 actual 是否满足所有 conditions。"""
        for key, expected_value in conditions.items():
            if actual.get(key) != expected_value:
                return False
        return True
