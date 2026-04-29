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
    PolicyEffectEntry,
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
    "user_wellbeing": {
        "harmful_conditions": {
            "user_reported_negative": True,
        },
        "harmful_attribution": "harmful",
        "harmful_confidence": 0.8,
        "needs_confirmation_conditions": {
            "ambiguous_outcome": True,
        },
        "needs_confirmation_attribution": "needs_confirmation",
        "needs_confirmation_confidence": 0.5,
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
        Idempotent: if an outcome already exists for this trace+intervention,
        returns the existing record instead of creating a duplicate.

        Returns:
            OutcomeRecord with attribution filled in.
        """
        import json as _json

        # Idempotency guard: check if outcome already recorded for this trace+intervention
        idem_key = f"spine:outcome_idem:{trace.trace_id}:{intervention}"
        try:
            existing_id = await self.redis.get(idem_key)
            if existing_id:
                existing = await self.get_outcome(existing_id)
                if existing:
                    logger.debug(
                        "OutcomeRecorder idempotent skip: trace={} intervention={} existing={}",
                        trace.trace_id, intervention, existing_id,
                    )
                    return existing
        except Exception:
            logger.debug("OutcomeRecorder idem check failed, proceeding", exc_info=True)
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

        # Set idempotency marker (same TTL as outcome)
        try:
            await self.redis.set(idem_key, record.outcome_id, nx=True, ex=720 * 3600)
        except Exception:
            logger.debug("OutcomeRecorder idem marker set failed", exc_info=True)

        # Write PolicyEffectLedger entry for learning loop
        if record.attribution not in ("inconclusive", "needs_confirmation"):
            await self._write_policy_effect(record)

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

        try:
            from app.core.business_metrics import SPINE_OUTCOME_ATTRIBUTION_TOTAL
            SPINE_OUTCOME_ATTRIBUTION_TOTAL.labels(
                directive_type=intervention,
                attribution=record.attribution,
            ).inc()
        except Exception:
            logger.debug("outcome_recorder: Prometheus metric inc failed")

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

        # Check harmful conditions first (highest priority)
        harmful_conds = rules.get("harmful_conditions", {})
        if harmful_conds and self._conditions_met(harmful_conds, actual_outcome):
            return (
                rules.get("harmful_attribution", "harmful"),
                rules.get("harmful_confidence", 0.8),
                "intervention_caused_harm",
                "immediate_retraction_and_apology",
            )

        # Check needs_confirmation conditions (ambiguous outcomes)
        nc_conds = rules.get("needs_confirmation_conditions", {})
        if nc_conds and self._conditions_met(nc_conds, actual_outcome):
            return (
                rules.get("needs_confirmation_attribution", "needs_confirmation"),
                rules.get("needs_confirmation_confidence", 0.5),
                "outcome_requires_user_confirmation",
                "request_user_feedback",
            )

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
        insufficient_conds = rules.get("insufficient_conditions")
        if insufficient_conds and self._conditions_met(insufficient_conds, actual_outcome):
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
        return all(actual.get(key) == expected_value for key, expected_value in conditions.items())

    async def _write_policy_effect(self, record: OutcomeRecord) -> None:
        """Write a PolicyEffectLedger entry from an outcome record."""
        import json

        feedback_signal = None
        feedback = record.actual_outcome.get("user_feedback", "")
        if feedback:
            if "看不懂" in feedback or "不懂" in feedback:
                feedback_signal = "cant_understand"
            elif "太难" in feedback or "too_hard" in feedback:
                feedback_signal = "too_hard"
            elif "太短" in feedback or "too_short" in feedback:
                feedback_signal = "too_short"
            elif "完成" in feedback or "completed" in feedback:
                feedback_signal = "completed"
            else:
                feedback_signal = feedback[:50]

        entry = PolicyEffectEntry(
            entry_id=_uid("pe"),
            policy_key=record.reason,
            intervention_summary=record.intervention,
            attribution=record.attribution,
            attribution_confidence=record.attribution_confidence,
            user_feedback_signal=feedback_signal,
            new_hypothesis=record.new_hypothesis,
        )

        entry_key = f"spine:policy_effect:{entry.entry_id}"
        await self.redis.set(entry_key, json.dumps(entry.to_dict()), ex=720 * 3600)

        trace_key = f"spine:trace:{record.causal_trace_id}"
        raw = await self.redis.get(trace_key)
        if raw:
            ledger_key = f"spine:policy_effect_ledger:{record.causal_trace_id}"
            await self.redis.lpush(ledger_key, entry.entry_id)
            await self.redis.ltrim(ledger_key, 0, 19)
            await self.redis.expire(ledger_key, 720 * 3600)

        logger.info(
            "PolicyEffectLedger: {} policy={} attribution={} feedback={}",
            entry.entry_id, entry.policy_key, entry.attribution, feedback_signal,
        )

    async def get_recent_policy_effects(
        self,
        user_id: str,
        limit: int = 5,
    ) -> list[PolicyEffectEntry]:
        """Get recent PolicyEffectEntries for a user's traces."""
        import json

        entries: list[PolicyEffectEntry] = []
        user_traces_key = f"spine:user_traces:{user_id}"
        trace_ids = await self.redis.lrange(user_traces_key, 0, limit - 1)

        for tid in trace_ids:
            ledger_key = f"spine:policy_effect_ledger:{tid}"
            effect_ids = await self.redis.lrange(ledger_key, 0, limit - 1)
            for eid in effect_ids:
                raw = await self.redis.get(f"spine:policy_effect:{eid}")
                if raw:
                    entries.append(PolicyEffectEntry.from_dict(json.loads(raw)))

        return entries[:limit]

    async def get_insufficient_count_for_policy(
        self,
        user_id: str,
        policy_key: str,
    ) -> int:
        """Count how many times a policy was insufficient for a user."""
        effects = await self.get_recent_policy_effects(user_id, limit=20)
        return sum(
            1 for e in effects
            if e.policy_key == policy_key and e.attribution == "insufficient"
        )

    # ── 神性时刻: 承认误判

    @staticmethod
    def build_self_correction_receipt(record: OutcomeRecord) -> dict[str, Any] | None:
        """
        Build a self-correction receipt when outcome is "insufficient".

        Divine moment: the system admits it was wrong and explains what it's changing.
        """
        if record.attribution not in ("insufficient", "harmful"):
            return None

        original_assumption = record.reason
        feedback_signal = record.actual_outcome.get("user_feedback", "")
        hypothesis = record.new_hypothesis or "strategy_mismatch"
        correction_map = {
            "intervention_caused_harm": {
                "correction": "立即撤回该策略，检查用户状态，降低后续干预强度",
                "new_action": "retract_and_reduce",
            },
            "task_completed_but_intervention_may_be_insufficient": {
                "correction": "不再机械重复相同策略，改为检查具体执行障碍",
                "new_action": "diagnostic_check",
            },
            "user_did_not_respond": {
                "correction": "减少提醒频率，改用更自然的引导方式",
                "new_action": "reduce_nudge_frequency",
            },
            "no_behavioral_change_detected": {
                "correction": "换一种更直接的方式帮助用户行动",
                "new_action": "escalate_or_try_different_approach",
            },
            "knowledge_explanation_failure": {
                "correction": "换成一步步演示 + 练习模式，不再单纯讲解",
                "new_action": "worked_example_then_drill",
            },
        }

        matched = correction_map.get(hypothesis, {
            "correction": "调整策略方向",
            "new_action": "reassess_and_adjust",
        })

        return {
            "type": "divine_moment_self_correction",
            "outcome_id": record.outcome_id,
            "original_assumption": original_assumption,
            "feedback_signal": feedback_signal,
            "correction": matched["correction"],
            "new_action": matched["new_action"],
            "message": (
                f"我需要修正一下。之前把问题理解成「{original_assumption}」，"
                f"但你的反馈说明更可能是「{hypothesis}」。"
                f"所以我改成：{matched['correction']}。"
            ),
        }
