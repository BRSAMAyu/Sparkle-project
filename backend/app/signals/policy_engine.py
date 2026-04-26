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
    NotificationDirective,
    PolicyDecision,
    ResponseDirective,
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
    "material_utilization": {
        "material_underutilized": {
            "primary_strategy": "activate_material_retrieval",
            "secondary_strategy": None,
            "hard_constraints": {
                "retrieval_mode": "targeted_source_rag",
                "source_scope": "user_selected",
            },
            "soft_biases": {
                "tone": "helpful_suggestion",
            },
            "visibility": "receipt",
            "requires_user_confirmation": True,
            "reasoning_template": "你上传的课件最近几轮没被用到，我来按课件内容回答。",
        },
    },
    "goal_mode": {
        "exam_rescue_detected": {
            "primary_strategy": "exam_rescue_sprint",
            "secondary_strategy": "minimum_pass_path",
            "hard_constraints": {
                "sprint_policy": "seven_day_survival",
                "defer_low_roi_topics": True,
                "max_task_duration_min": 30,
            },
            "soft_biases": {
                "tone": "calm_urgent",
                "skip_full_form": True,
            },
            "visibility": "receipt",
            "requires_user_confirmation": True,
            "reasoning_template": "检测到考试紧急情况，进入抢救模式。",
        },
    },
    "knowledge_transfer": {
        "transfer_failure": {
            "primary_strategy": "repair_knowledge_bottleneck",
            "secondary_strategy": "prevent_new_chapter",
            "hard_constraints": {
                "avoid_new_chapter": True,
                "required_task_type": "worked_example_then_drill",
                "max_task_duration_min": 30,
            },
            "soft_biases": {
                "tone": "encouraging_diagnostic",
                "difficulty": "low_medium",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "这个知识点你连续出错了，我先帮你巩固，不急着推进新内容。",
        },
    },
    "growth_momentum": {
        "momentum_high": {
            "primary_strategy": "sustain_momentum",
            "secondary_strategy": "gradual_challenge_increase",
            "hard_constraints": {},
            "soft_biases": {
                "tone": "recognition_not_praise",
                "nudge_style": "lighter",
                "challenge": "slight_increase",
            },
            "visibility": "status_band",
            "requires_user_confirmation": False,
            "reasoning_template": "你最近节奏不错，我会适当减少催促，试试稍有点挑战的内容。",
        },
        "momentum_stalled": {
            "primary_strategy": "rekindle_engagement",
            "secondary_strategy": None,
            "hard_constraints": {},
            "soft_biases": {
                "tone": "encouraging_low_pressure",
                "nudge_style": "gentle",
            },
            "visibility": "status_band",
            "requires_user_confirmation": False,
            "reasoning_template": "最近进度变慢了，但不急，先找一个轻松的切入点。",
        },
    },
    "recall_needed": {
        "undigested_material": {
            "primary_strategy": "prompt_diagnostic",
            "secondary_strategy": None,
            "hard_constraints": {},
            "soft_biases": {
                "message_strategy": "low_effort_next_step",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你上传了资料但还没看，我帮你花几分钟诊断一下？",
        },
        "task_not_started": {
            "primary_strategy": "nudge_task_start",
            "secondary_strategy": None,
            "hard_constraints": {},
            "soft_biases": {
                "message_strategy": "low_effort_next_step",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你的任务在等你，先看 5 分钟也行。",
        },
        "task_missed": {
            "primary_strategy": "recover_from_missed_task",
            "secondary_strategy": "adjust_plan",
            "hard_constraints": {},
            "soft_biases": {
                "message_strategy": "recovery_offer",
            },
            "visibility": "receipt",
            "requires_user_confirmation": True,
            "reasoning_template": "这张任务错过了，要调整计划还是跳过？",
        },
        "pre_exam_silence": {
            "primary_strategy": "urgent_exam_prep",
            "secondary_strategy": "high_yield_review",
            "hard_constraints": {
                "prefer_high_yield_review": True,
                "avoid_new_chapter": True,
            },
            "soft_biases": {
                "tone": "calm_urgent",
                "message_strategy": "quick_review_offer",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "快考试了，我帮你快速过一遍最可能考的要点。",
        },
    },
    "community_cohort_pattern": {
        "cohort_mistake_detected": {
            "primary_strategy": "show_cohort_hint",
            "secondary_strategy": None,
            "hard_constraints": {},
            "soft_biases": {
                "tone": "youre_not_alone",
                "message_strategy": "shared_explanation_offer",
            },
            "visibility": "inline_hint",
            "requires_user_confirmation": False,
            "reasoning_template": "这个知识点不少同学都容易搞混，你不是一个人。来看看常见陷阱？",
        },
    },
    "community_resource_recommendation": {
        "shared_resource_relevant": {
            "primary_strategy": "show_peer_resource",
            "secondary_strategy": None,
            "hard_constraints": {},
            "soft_biases": {
                "message_strategy": "peer_curated_recommendation",
            },
            "visibility": "inline_hint",
            "requires_user_confirmation": False,
            "reasoning_template": "跟你同考的同学在看这个资料，也许对你也有帮助。",
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
        try:
            reasoning = rule["reasoning_template"].format(consecutive=consecutive)
        except KeyError:
            reasoning = rule["reasoning_template"]

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

    def build_response_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> ResponseDirective | None:
        """
        从 PolicyDecision 的 soft_biases 构建 ResponseDirective。
        不是所有策略都需要 ResponseDirective（e.g. status_band 级别不需要）。
        """
        biases = decision.soft_biases
        tone = biases.get("tone", "calm_direct")

        # Derive must_acknowledge from signal context
        must_acknowledge: list[str] = []
        if signal.state_key == "task_granularity_fit":
            must_acknowledge = ["recent_overrun"]
        elif signal.state_key == "knowledge_transfer":
            must_acknowledge = ["repeated_errors"]
        elif signal.state_key == "goal_mode":
            must_acknowledge = ["exam_situation"]

        # Derive avoid list from tone
        avoid: list[str] = []
        if tone in ("encouraging_diagnostic", "encouraging_low_pressure"):
            avoid = ["generic_encouragement", "pressure_language"]
        elif tone in ("calm_urgent", "calm_direct"):
            avoid = ["generic_encouragement"]
        if tone == "recognition_not_praise":
            avoid = ["empty_praise", "generic_encouragement"]

        # Only produce ResponseDirective for receipt/inline visibility
        if decision.visibility == "status_band":
            return None

        return ResponseDirective(
            directive_id=_uid("rdsp"),
            policy_decision_id=decision.policy_decision_id,
            tone=tone,
            length="short" if decision.visibility == "inline_hint" else "medium",
            must_acknowledge=must_acknowledge,
            avoid=avoid,
            include_user_options=decision.requires_user_confirmation,
            scope="turn",
        )

    # Trigger → notification params mapping
    _NOTIFICATION_MAP: dict[str, dict[str, str]] = {
        "undigested_material": {
            "trigger": "undigested_material",
            "message_strategy": "low_effort_next_step",
            "max_frequency": "1_per_day",
        },
        "task_not_started": {
            "trigger": "first_task_not_started",
            "message_strategy": "low_effort_next_step",
            "max_frequency": "1_per_day",
        },
        "task_missed": {
            "trigger": "task_missed",
            "message_strategy": "recovery_offer",
            "max_frequency": "2_per_day",
        },
        "pre_exam_silence": {
            "trigger": "pre_exam_silence",
            "message_strategy": "quick_review_offer",
            "max_frequency": "2_per_day",
        },
    }

    def build_notification_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> NotificationDirective | None:
        """
        从 PolicyDecision 构建通知指令。
        只对 recall_needed 和特定策略生成。
        """
        if signal.state_key not in ("recall_needed", "deadline_pressure", "goal_mode"):
            return None

        claim = signal.claim
        params = self._NOTIFICATION_MAP.get(claim)
        if not params:
            # goal_mode/exam_rescue → allow urgent notifications
            if signal.state_key == "goal_mode" and "exam" in claim:
                params = {
                    "trigger": "exam_rescue_urgent",
                    "message_strategy": "quick_review_offer",
                    "max_frequency": "2_per_day",
                }
            else:
                return None

        return NotificationDirective(
            directive_id=_uid("nd"),
            policy_decision_id=decision.policy_decision_id,
            allowed=True,
            channel="push",
            respect_quiet_hours=True,
            trigger=params["trigger"],
            message_strategy=params["message_strategy"],
            max_frequency=params["max_frequency"],
            scope="today",
        )
