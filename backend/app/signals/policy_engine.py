"""
Core: execution
Phase: clarify→plan
Stage: Signal-to-Action Spine M1-Step3

Policy Engine — 固定规则策略仲裁。
第一版规则化，不等 LLM 推断。

PolicyDecision 输出结构化 hard_constraints / soft_biases。
ExecutionDirective 下游模块必须以结构化参数消费。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.types import (
    ActionableSignal,
    ExecutionDirective,
    PolicyDecision,
    _uid,
)

# ── 固定规则映射表 ──────────────────────────────────────────────────
# 每个 state_key + claim 组合映射到确定性策略。

_RULE_TABLE: dict[str, dict[str, dict[str, Any]]] = {
    "task_granularity_fit": {
        "recent_task_too_large": {
            "primary_strategy": "recover_execution_rhythm",
            "secondary_strategy": "repair_current_bottleneck",
            "hard_constraints": {
                "max_task_duration_min": 25,
                "avoid_new_chapter": True,
                "required_task_type": "worked_example_then_drill",
            },
            "soft_biases": {
                "tone": "direct_but_reassuring",
                "difficulty": "medium_low",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "最近 {consecutive} 次任务超时，先恢复可完成节奏。",
        },
    },
}

_DIRECTIVE_TARGET_MODULE = "task_generator"
_DIRECTIVE_SCOPE = "today"


class PolicyEngine:
    """Signal → PolicyDecision → ExecutionDirective（固定规则版）。"""

    async def evaluate(
        self,
        signal: ActionableSignal,
        context: dict[str, Any] | None = None,
    ) -> tuple[PolicyDecision, ExecutionDirective] | None:
        """
        根据固定规则将 ActionableSignal 转为 PolicyDecision + ExecutionDirective。

        Returns:
            (PolicyDecision, ExecutionDirective) if rule matched, None otherwise.
        """
        rule_set = _RULE_TABLE.get(signal.state_key, {})
        rule = rule_set.get(signal.claim)
        if not rule:
            logger.debug("no rule for state_key={} claim={}", signal.state_key, signal.claim)
            return None

        # 检查置信度门槛
        if signal.confidence < 0.5:
            logger.debug("signal confidence too low: {:.2f}", signal.confidence)
            return None

        consecutive = context.get("consecutive", 2) if context else 2
        reasoning = rule["reasoning_template"].format(consecutive=consecutive)

        decision = PolicyDecision(
            policy_decision_id=_uid("pd"),
            primary_strategy=rule["primary_strategy"],
            secondary_strategy=rule.get("secondary_strategy"),
            hard_constraints=dict(rule["hard_constraints"]),
            soft_biases=dict(rule.get("soft_biases", {})),
            visibility=rule.get("visibility", "receipt"),
            requires_user_confirmation=rule.get("requires_user_confirmation", False),
            reasoning_summary=reasoning,
        )

        directive = ExecutionDirective(
            directive_id=_uid("ed"),
            policy_decision_id=decision.policy_decision_id,
            target_module=_DIRECTIVE_TARGET_MODULE,
            scope=_DIRECTIVE_SCOPE,
            hard_constraints=dict(rule["hard_constraints"]),
            user_visible_reason=reasoning,
        )

        logger.info(
            "PolicyDecision: {} strategy={}",
            decision.policy_decision_id, decision.primary_strategy,
        )
        logger.info(
            "ExecutionDirective: {} target={} constraints={}",
            directive.directive_id, directive.target_module,
            list(directive.hard_constraints.keys()),
        )

        return decision, directive
