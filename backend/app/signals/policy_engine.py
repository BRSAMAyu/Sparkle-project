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
    CommunityDirective,
    ExecutionDirective,
    ModelWriteDirective,
    ModelWriteEntry,
    NotificationDirective,
    PlanDirective,
    PolicyDecision,
    ResponseDirective,
    RetrievalDirective,
    SkillDirective,
    UXDirective,
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
            "secondary_strategy": "insert_easy_win",
            "hard_constraints": {
                "max_task_duration_min": 20,
                "prefer_easy_wins": True,
            },
            "soft_biases": {
                "tone": "encouraging_low_pressure",
                "nudge_style": "gentle",
                "difficulty": "low",
            },
            "visibility": "status_band",
            "requires_user_confirmation": False,
            "reasoning_template": "最近进度变慢了，不急，先找一个轻松的切入点。",
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
    "community_partner_feedback": {
        "pacing_too_fast": {
            "primary_strategy": "adjust_partner_reported_pacing",
            "secondary_strategy": "reduce_next_48h_load",
            "hard_constraints": {
                "pace_direction": "slow_down",
                "partner_feedback": True,
            },
            "soft_biases": {
                "tone": "calm_direct",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你的学习伙伴观察到节奏可能偏快，接下来 48 小时先降一点负荷。",
        },
        "pacing_too_slow": {
            "primary_strategy": "adjust_partner_reported_pacing",
            "secondary_strategy": "increase_next_48h_activation",
            "hard_constraints": {
                "pace_direction": "speed_up",
                "partner_feedback": True,
            },
            "soft_biases": {
                "tone": "calm_direct",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你的学习伙伴观察到节奏可能偏慢，接下来 48 小时给你一个更清晰的启动安排。",
        },
        "focus_refocus_needed": {
            "primary_strategy": "apply_partner_focus_patch",
            "secondary_strategy": None,
            "hard_constraints": {
                "reduce_context_switching": True,
                "partner_feedback": True,
            },
            "soft_biases": {
                "tone": "calm_direct",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你的学习伙伴观察到注意力可能分散，本轮先收窄到关键主题。",
        },
        "difficulty_shift_needed": {
            "primary_strategy": "apply_partner_difficulty_patch",
            "secondary_strategy": None,
            "hard_constraints": {
                "partner_feedback": True,
            },
            "soft_biases": {
                "tone": "encouraging_diagnostic",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你的学习伙伴观察到难度可能不匹配，接下来 48 小时先微调题目难度。",
        },
        "morale_encouragement_needed": {
            "primary_strategy": "encourage_partner_observed_morale",
            "secondary_strategy": None,
            "hard_constraints": {
                "partner_feedback": True,
            },
            "soft_biases": {
                "tone": "encouraging_low_pressure",
            },
            "visibility": "receipt",
            "requires_user_confirmation": False,
            "reasoning_template": "你的学习伙伴观察到你可能有点低落，这一轮先给你一个低压力的推进方式。",
        },
    },
    "cognitive_load": {
        "high_load_detected": {
            "primary_strategy": "reduce_cognitive_pressure",
            "secondary_strategy": "simplify_context",
            "hard_constraints": {
                "max_explanation_length": "short",
                "prefer_review_over_new": True,
                "max_task_duration_min": 20,
            },
            "soft_biases": {
                "tone": "calm_direct",
                "difficulty": "low",
                "explanation_depth": "minimal",
            },
            "visibility": "inline_hint",
            "requires_user_confirmation": False,
            "reasoning_template": "你最近接触了比较多新内容，这轮先巩固不推进新知识点。",
        },
    },
    "affective_pressure": {
        "stress_detected": {
            "primary_strategy": "reduce_affective_pressure",
            "secondary_strategy": "insert_reassurance",
            "hard_constraints": {
                "avoid_new_chapter": True,
                "prefer_easy_wins": True,
                "max_task_duration_min": 20,
            },
            "soft_biases": {
                "tone": "encouraging_low_pressure",
                "nudge_style": "minimal",
            },
            "visibility": "status_band",
            "requires_user_confirmation": False,
            "reasoning_template": "看起来压力有点大，这轮我给你一个轻松一点的节奏。",
        },
        "burnout_risk": {
            "primary_strategy": "prevent_burnout",
            "secondary_strategy": "suggest_break",
            "hard_constraints": {
                "suggest_break": True,
                "max_task_duration_min": 15,
                "avoid_new_chapter": True,
            },
            "soft_biases": {
                "tone": "calm_caring",
                "nudge_style": "off",
            },
            "visibility": "receipt",
            "requires_user_confirmation": True,
            "reasoning_template": "你最近学得很拼，但节奏可能太快了。先休息一下，或者做一个最轻松的回顾？",
        },
    },
}

_DIRECTIVE_TARGET_MODULE = "task_generator"
_DIRECTIVE_SCOPE = "today"

# ── Risk Level Mapping ──────────────────────────────────────────────
# Tier 1-2 state_keys → "high", Tier 3-4 → "medium", rest → "low"
# goal_mode with exam_rescue → "critical"
_RISK_LEVEL_MAP: dict[str, str] = {
    "safety_boundary": "critical",
    "user_correction": "high",
    "deadline_pressure": "high",
    "exam_rescue": "critical",
    "goal_mode": "high",
    "task_granularity_fit": "medium",
    "knowledge_transfer": "medium",
    "recall_needed": "medium",
    "material_utilization": "low",
    "growth_momentum": "low",
    "community_cohort_pattern": "low",
    "community_resource_recommendation": "low",
    "community_partner_feedback": "medium",
    "cognitive_load": "medium",
    "affective_pressure": "high",
}

# ── Directive Activation Map ────────────────────────────────────────
# Which directive types to generate per state_key
_WHICH_DIRECTIVES: dict[str, dict[str, bool]] = {
    "task_granularity_fit": {
        "response": True, "execution": True, "ux": True, "model_write": True,
    },
    "material_utilization": {
        "retrieval": True, "response": True, "ux": True,
    },
    "goal_mode": {
        "response": True, "execution": True, "plan": True, "ux": True, "model_write": True,
    },
    "knowledge_transfer": {
        "response": True, "execution": True, "retrieval": True, "ux": True, "model_write": True, "skill": True,
    },
    "growth_momentum": {
        "response": True, "ux": True,
    },
    "recall_needed": {
        "notification": True, "response": True, "ux": True,
    },
    "community_cohort_pattern": {
        "response": True, "community": True, "ux": True,
    },
    "community_resource_recommendation": {
        "retrieval": True, "community": True, "ux": True,
    },
    "community_partner_feedback": {
        "response": True, "execution": True, "ux": True, "model_write": True,
    },
    "cognitive_load": {
        "response": True, "execution": True, "retrieval": True, "ux": True,
    },
    "affective_pressure": {
        "response": True, "execution": True, "ux": True, "notification": True,
    },
}


class PolicyEngine:
    """Signal → PolicyDecision → ExecutionDirective（固定规则版）。"""

    def __init__(self, reply_engine: Any | None = None):
        self._reply_engine = reply_engine

    def _apply_shadow_learning(
        self,
        rule: dict[str, Any],
        signal: ActionableSignal,
        recent_policy_effects: list[Any] | None,
    ) -> dict[str, Any]:
        """
        Shadow-mode learning: adjust rule output based on recent outcome history.

        Does NOT modify the global _RULE_TABLE. Returns a copy with adjustments.
        """
        if not recent_policy_effects:
            return rule

        strategy = rule["primary_strategy"]
        insufficient_count = sum(
            1 for pe in recent_policy_effects
            if getattr(pe, "policy_key", "") == strategy
            and getattr(pe, "attribution", "") == "insufficient"
        )

        if insufficient_count < 2:
            return rule

        # Check if user gave "can't understand" feedback on repeated failures
        has_understanding_issue = any(
            getattr(pe, "user_feedback_signal", None) == "cant_understand"
            for pe in recent_policy_effects
            if getattr(pe, "policy_key", "") == strategy
            and getattr(pe, "attribution", "") == "insufficient"
        )

        # Shadow adjustment: don't mechanically repeat the same intervention
        adjusted_rule = dict(rule)

        if has_understanding_issue:
            # Problem is knowledge explanation, not task length
            adjusted_rule["primary_strategy"] = "switch_to_worked_example"
            adjusted_rule["hard_constraints"] = {
                "avoid_new_chapter": True,
                "required_task_type": "worked_example_then_drill",
            }
            adjusted_rule["soft_biases"] = {
                "tone": "warm_direct",
                "difficulty": "low",
            }
            adjusted_rule["reasoning_template"] = (
                "之前的策略没解决问题。我之前判断是任务太长，"
                "但更可能是题型迁移没建立。改用 worked example。"
            )
            logger.info(
                "Shadow learning: switching strategy from {} to switch_to_worked_example "
                "(insufficient_count={}, has_understanding_issue={})",
                strategy, insufficient_count, has_understanding_issue,
            )
        else:
            # Repeated failure without specific feedback — try softer approach
            adjusted_rule["soft_biases"] = dict(rule.get("soft_biases", {}))
            adjusted_rule["soft_biases"]["tone"] = "warm_direct"
            adjusted_rule["reasoning_template"] = (
                "最近策略效果不理想，我调整一下方向。{consecutive}"
            )

        return adjusted_rule

    @staticmethod
    def _apply_belief_bias(
        rule: dict[str, Any],
        strategy_beliefs: list[Any] | None,
    ) -> dict[str, Any]:
        """
        v2.4: Adjust rule output based on Bayesian strategy beliefs.

        If the current strategy has low expected effectiveness and an alternative
        has high expected effectiveness, bias soft_biases toward the alternative's
        approach. Does NOT override hard constraints.
        """
        if not strategy_beliefs:
            return rule

        belief_map = {}
        for b in strategy_beliefs:
            key = getattr(b, "strategy_key", None)
            if key:
                eff = getattr(b, "expected_effectiveness", 0.5)
                evidence = getattr(b, "evidence_count", 0)
                belief_map[key] = {"effectiveness": eff, "evidence": evidence}

        current_strategy = rule.get("primary_strategy", "")
        current_info = belief_map.get(current_strategy)

        # Only bias if we have enough evidence that current strategy is weak
        if not current_info or current_info["evidence"] < 5:
            return rule

        if current_info["effectiveness"] >= 0.4:
            return rule  # Strategy is working well enough

        # Find best alternative from beliefs
        best_alt = None
        best_eff = 0.0
        for key, info in belief_map.items():
            if key != current_strategy and info["effectiveness"] > best_eff and info["evidence"] >= 3:
                best_alt = key
                best_eff = info["effectiveness"]

        if best_alt and best_eff > current_info["effectiveness"] + 0.15:
            adjusted_rule = dict(rule)
            adjusted_rule["soft_biases"] = dict(rule.get("soft_biases", {}))
            adjusted_rule["soft_biases"]["belief_biased_from"] = current_strategy
            adjusted_rule["soft_biases"]["belief_biased_to"] = best_alt
            adjusted_rule["soft_biases"]["tone"] = "warm_direct"
            return adjusted_rule

        return rule

    @staticmethod
    def _apply_aurora_decision_bias(
        rule: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Inject recent Aurora decisions as reversible soft policy bias."""
        if not context:
            return rule

        decisions = context.get("aurora_decisions")
        if not isinstance(decisions, list) or not decisions:
            return rule

        latest = decisions[-1]
        if not isinstance(latest, dict):
            return rule

        action = str(latest.get("action") or "").strip()
        surface = str(latest.get("surface") or "").strip()
        if not action and not surface:
            return rule

        adjusted = dict(rule)
        soft_biases = dict(rule.get("soft_biases", {}))
        if action:
            soft_biases["aurora_recent_action"] = action
        if surface:
            soft_biases["aurora_recent_surface"] = surface

        if action in {"reduce_load", "pause", "defer", "protect_user"} or "fatigue" in surface:
            soft_biases["tone"] = "low_pressure"
            soft_biases["nudge_style"] = "minimal"
            adjusted["reasoning_template"] = (
                str(rule.get("reasoning_template", ""))
                + " Aurora 最近判断需要降低负荷，因此本轮只做软性收敛。"
            )

        adjusted["soft_biases"] = soft_biases
        return adjusted

    @staticmethod
    def _apply_quality_cross_check(
        rule: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        P0-1b: 3-tier quality cross-check for momentum_high.

        Rule A: quality_ok → recognize consistency, allow slight challenge increase
        Rule B: declining_accuracy → avoid challenge, focus on mistake repair
        Rule C: overrun / high_pressure → protect sustainability, cap task duration
        """
        if not context:
            return rule

        accuracy_trend = context.get("accuracy_trend")  # "improving" / "stable" / "declining"
        time_overrun = context.get("time_overrun", False)
        high_pressure = context.get("high_pressure", False)
        quality_ok = context.get("quality_ok", True)  # default true when unknown

        adjusted = dict(rule)

        # Rule C: overrun or high pressure takes highest priority
        if time_overrun or high_pressure:
            adjusted["primary_strategy"] = "protect_sustainability"
            adjusted["secondary_strategy"] = None
            adjusted["hard_constraints"] = {"max_task_duration_min": 25}
            adjusted["soft_biases"] = {
                "tone": "low_pressure",
                "nudge_style": "minimal",
            }
            adjusted["reasoning_template"] = (
                "虽然节奏稳定，但最近有超时/压力大的情况，先保持当前节奏不加码。"
            )
            return adjusted

        # Rule B: momentum high but accuracy declining
        if accuracy_trend == "declining" or not quality_ok:
            adjusted["primary_strategy"] = "recognize_effort_but_repair_quality"
            adjusted["secondary_strategy"] = "mistake_repair_priority"
            adjusted["hard_constraints"] = {}
            adjusted["soft_biases"] = {
                "tone": "recognition_not_praise",
                "task_type": "mistake_repair",
            }
            adjusted["reasoning_template"] = (
                "连续做得不错，但准确率有下降趋势。先巩固错因，不急着加难度。"
            )
            return adjusted

        # Rule A: quality_ok (default) — standard momentum_high is fine
        # Already has: sustain_momentum, gradual_challenge_increase
        return adjusted

    async def evaluate(
        self,
        signal: ActionableSignal,
        context: dict[str, Any] | None = None,
        recent_policy_effects: list[Any] | None = None,
        strategy_beliefs: list[Any] | None = None,
    ) -> tuple[PolicyDecision, ExecutionDirective] | None:
        """
        根据固定规则将 ActionableSignal 转为 PolicyDecision + ExecutionDirective。

        Args:
            recent_policy_effects: Optional PolicyEffectEntry list for shadow-mode bias.
            strategy_beliefs: Optional StrategyBelief list for Bayesian bias.

        Returns:
            (PolicyDecision, ExecutionDirective) if rule matched, None otherwise.
        """
        rule_set = _RULE_TABLE.get(signal.state_key, {})
        rule = rule_set.get(signal.claim)
        if not rule:
            logger.debug("no rule for state_key={} claim={}", signal.state_key, signal.claim)
            return None

        # GOV-016: Allow high-priority signals through confidence gate, forcing receipt
        force_receipt = signal.confidence < 0.5 and signal.priority == "high"
        if signal.confidence < 0.5 and not force_receipt:
            logger.debug("signal confidence too low: {:.2f}", signal.confidence)
            return None

        # Shadow-mode learning: if recent policy effects show repeated failure,
        # adjust strategy instead of repeating the same intervention
        rule = self._apply_shadow_learning(rule, signal, recent_policy_effects)

        # v2.4: Bayesian strategy belief bias
        rule = self._apply_belief_bias(rule, strategy_beliefs)

        # Aurora → Spine feedback: Aurora decisions may soften tone/load, but
        # never bypass policy arbitration or mutate hard constraints directly.
        rule = self._apply_aurora_decision_bias(rule, context)

        # P0-1b: Achievement quality cross-check (3-tier rules for momentum_high)
        if signal.state_key == "growth_momentum" and signal.claim == "momentum_high":
            rule = self._apply_quality_cross_check(rule, context)

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
            visibility="receipt" if force_receipt else rule.get("visibility", "receipt"),
            requires_user_confirmation=force_receipt or rule.get("requires_user_confirmation", False),
            reasoning_summary=reasoning,
            risk_level=_RISK_LEVEL_MAP.get(signal.state_key, "medium"),
            which_directives=dict(_WHICH_DIRECTIVES.get(signal.state_key, {"response": True, "execution": True})),
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

    # Signal → retrieval mode mapping
    _RETRIEVAL_MAP: dict[str, dict[str, Any]] = {
        "material_underutilized": {
            "retrieval_mode": "targeted_source_rag",
            "source_scope": "user_selected",
            "pollution_guard": "strict",
            "reason": "你上传的课件最近几轮没被用到，我来按课件内容回答。",
        },
        "exam_rescue_detected": {
            "retrieval_mode": "task_bound_graph_rag",
            "source_scope": "task_bound",
            "pollution_guard": "strict",
            "reason": "考试抢救模式下只加载与任务直接相关的资料。",
        },
        "transfer_failure": {
            "retrieval_mode": "task_bound_graph_rag",
            "source_scope": "task_bound",
            "pollution_guard": "strict",
            "reason": "这个知识点需要巩固，只加载相关错因和例题。",
        },
        "pre_exam_silence": {
            "retrieval_mode": "task_bound_graph_rag",
            "source_scope": "task_bound",
            "pollution_guard": "permissive",
            "reason": "考前快速复习，加载高收益资料。",
        },
    }

    def build_retrieval_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> RetrievalDirective | None:
        """从 PolicyDecision 构建 RetrievalDirective — 控制 RAG 资料调用。"""
        params = self._RETRIEVAL_MAP.get(signal.claim)
        if not params:
            return None

        hard_constraints = decision.hard_constraints or {}
        retrieval_mode = hard_constraints.get("retrieval_mode", params["retrieval_mode"])
        source_scope = hard_constraints.get("source_scope", params["source_scope"])
        if signal.state_key == "material_utilization" and signal.claim == "material_underutilized":
            retrieval_mode = "targeted_source_rag"
            source_scope = source_scope or "user_selected"

        return RetrievalDirective(
            directive_id=_uid("rtd"),
            policy_decision_id=decision.policy_decision_id,
            retrieval_mode=retrieval_mode,
            source_scope=source_scope,
            pollution_guard=params["pollution_guard"],
            reason_for_user=params["reason"],
            scope="turn",
        )

    # Signal → plan action mapping
    _PLAN_ACTION_MAP: dict[str, dict[str, Any]] = {
        "recent_task_too_large": {
            "plan_action": "local_replan",
            "scope": "next_48h",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "preserve_deadline_strategy": True,
                "insert_recovery_task": True,
            },
        },
        "transfer_failure": {
            "plan_action": "local_replan",
            "scope": "current_sprint",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "avoid_new_chapter": True,
                "insert_practice_task": True,
            },
        },
        "exam_rescue_detected": {
            "plan_action": "full_replan",
            "scope": "current_sprint",
            "constraints": {
                "preserve_deadline_strategy": True,
                "prefer_high_yield": True,
                "max_task_duration_min": 30,
            },
        },
        "momentum_stalled": {
            "plan_action": "local_replan",
            "scope": "next_48h",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "insert_easy_win": True,
            },
        },
        "task_missed": {
            "plan_action": "insert_task",
            "scope": "next_48h",
            "constraints": {
                "recovery_task": True,
                "adjust_subsequent_deadlines": True,
            },
        },
        "pacing_too_fast": {
            "plan_action": "local_replan",
            "scope": "next_48h",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "pace_adjustment": "slow_down",
                "reduce_task_load": True,
                "partner_feedback": True,
            },
        },
        "pacing_too_slow": {
            "plan_action": "local_replan",
            "scope": "next_48h",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "pace_adjustment": "speed_up",
                "insert_starter_task": True,
                "partner_feedback": True,
            },
        },
        "focus_refocus_needed": {
            "plan_action": "local_replan",
            "scope": "current_sprint",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "reduce_context_switching": True,
                "partner_feedback": True,
            },
        },
        "difficulty_shift_needed": {
            "plan_action": "local_replan",
            "scope": "next_48h",
            "constraints": {
                "do_not_rebuild_entire_plan": True,
                "adjust_difficulty": True,
                "partner_feedback": True,
            },
        },
    }

    def build_plan_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> PlanDirective | None:
        """从 PolicyDecision 构建 PlanDirective — 控制计划和重规划。"""
        params = self._PLAN_ACTION_MAP.get(signal.claim)
        if not params:
            return None

        return PlanDirective(
            directive_id=_uid("pld"),
            policy_decision_id=decision.policy_decision_id,
            plan_action=params["plan_action"],
            scope=params["scope"],
            constraints=dict(params["constraints"]),
        )

    # Signal → model write mapping
    _MODEL_WRITE_MAP: dict[str, list[dict[str, Any]]] = {
        "recent_task_too_large": [
            {
                "target_model": "user_state",
                "claim_template": "当前冲刺下任务颗粒度可能偏大",
                "scope": "current_sprint",
                "confidence_source": "signal",
                "needs_user_confirmation": False,
                "ttl": "72h",
            },
            {
                "target_model": "sparkle_self_model",
                "claim_template": "长任务对该用户可能不适配",
                "scope": "strategy",
                "confidence_source": "signal_degraded",
                "needs_user_confirmation": False,
                "ttl": "168h",
            },
        ],
        "transfer_failure": [
            {
                "target_model": "user_state",
                "claim_template": "该知识点连续出错，需要巩固",
                "scope": "current_sprint",
                "confidence_source": "signal",
                "needs_user_confirmation": False,
                "ttl": "72h",
            },
        ],
        "exam_rescue_detected": [
            {
                "target_model": "user_state",
                "claim_template": "进入考试抢救模式",
                "scope": "current_sprint",
                "confidence_source": "signal",
                "needs_user_confirmation": True,
                "ttl": "168h",
            },
        ],
        "momentum_high": [
            {
                "target_model": "sparkle_self_model",
                "claim_template": "鼓励策略有效，用户节奏良好",
                "scope": "strategy",
                "confidence_source": "signal",
                "needs_user_confirmation": False,
                "ttl": "72h",
            },
        ],
    }

    def build_model_write_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> ModelWriteDirective | None:
        """从 PolicyDecision 构建 ModelWriteDirective — 控制写入哪个模型、写入多深。"""
        entries_config = self._MODEL_WRITE_MAP.get(signal.claim)
        if not entries_config:
            return None

        writes: list[ModelWriteEntry] = []
        for cfg in entries_config:
            confidence = signal.confidence
            if cfg.get("confidence_source") == "signal_degraded":
                confidence = round(confidence * 0.9, 2)
            writes.append(ModelWriteEntry(
                target_model=cfg["target_model"],
                claim=cfg["claim_template"],
                scope=cfg["scope"],
                confidence=confidence,
                needs_user_confirmation=cfg.get("needs_user_confirmation", False),
                ttl=cfg.get("ttl", "72h"),
            ))

        return ModelWriteDirective(
            directive_id=_uid("mwd"),
            policy_decision_id=decision.policy_decision_id,
            writes=writes[:5],  # cap at 5 entries
        )

    # Signal → UX state mapping
    _UX_STATE_MAP: dict[str, dict[str, Any]] = {
        "recent_task_too_large": {
            "status_band_state": "risk_detected",
            "show_strategy_receipt": True,
            "allow_full_aurora_wake": False,
        },
        "transfer_failure": {
            "status_band_state": "risk_detected",
            "show_strategy_receipt": True,
            "allow_full_aurora_wake": False,
        },
        "exam_rescue_detected": {
            "status_band_state": "strategy_active",
            "show_strategy_receipt": True,
            "allow_full_aurora_wake": True,
        },
        "momentum_high": {
            "status_band_state": "milestone",
            "show_strategy_receipt": False,
            "allow_full_aurora_wake": False,
        },
        "momentum_stalled": {
            "status_band_state": "risk_detected",
            "show_strategy_receipt": False,
            "allow_full_aurora_wake": False,
        },
        "undigested_material": {
            "status_band_state": "normal",
            "show_context_receipt": True,
            "allow_full_aurora_wake": False,
        },
        "task_not_started": {
            "status_band_state": "normal",
            "show_context_receipt": True,
            "allow_full_aurora_wake": False,
        },
        "task_missed": {
            "status_band_state": "risk_detected",
            "show_strategy_receipt": True,
            "allow_full_aurora_wake": False,
        },
        "pre_exam_silence": {
            "status_band_state": "strategy_active",
            "show_context_receipt": True,
            "allow_full_aurora_wake": False,
        },
        "material_underutilized": {
            "status_band_state": "normal",
            "show_context_receipt": True,
            "show_strategy_receipt": False,
            "allow_full_aurora_wake": False,
        },
        "cohort_mistake_detected": {
            "status_band_state": "normal",
            "show_context_receipt": False,
            "allow_full_aurora_wake": False,
        },
        "shared_resource_relevant": {
            "status_band_state": "normal",
            "show_context_receipt": False,
            "allow_full_aurora_wake": False,
        },
    }

    def build_ux_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> UXDirective | None:
        """从 PolicyDecision 构建 UXDirective — 控制状态带、回执、Aurora 可见性。"""
        params = self._UX_STATE_MAP.get(signal.claim)
        if not params:
            # Default UX for unmatched signals with status_band visibility
            if decision.visibility == "status_band":
                return UXDirective(
                    directive_id=_uid("uxd"),
                    policy_decision_id=decision.policy_decision_id,
                    status_band_state="normal",
                    show_context_receipt=True,
                    show_strategy_receipt=False,
                )
            # receipt/inline_hint signals without explicit mapping → default UX
            return UXDirective(
                directive_id=_uid("uxd"),
                policy_decision_id=decision.policy_decision_id,
                status_band_state="normal",
                show_context_receipt=True,
                show_strategy_receipt=decision.requires_user_confirmation,
            )

        # Populate predicted_reply_options from reply engine
        predicted_options: list[str] = []
        if self._reply_engine and decision.requires_user_confirmation:
            question = self._reply_engine.generate_options(signal)
            if question:
                predicted_options = [opt.label for opt in question.options]

        return UXDirective(
            directive_id=_uid("uxd"),
            policy_decision_id=decision.policy_decision_id,
            status_band_state=params.get("status_band_state", "normal"),
            show_context_receipt=params.get("show_context_receipt", True),
            show_strategy_receipt=params.get("show_strategy_receipt", False),
            allow_full_aurora_wake=params.get("allow_full_aurora_wake", False),
            predicted_reply_options=predicted_options,
        )

    # ── CommunityDirective ─────────────────────────────────────────────

    _COMMUNITY_MAP: dict[str, dict[str, Any]] = {
        "cohort_mistake_detected": {
            "cohort_hint_shown": True,
            "peer_context_mode": "anonymous",
            "max_frequency": "3_per_week",
            "resource_quality_filter": 0.5,
        },
        "shared_resource_relevant": {
            "cohort_hint_shown": False,
            "peer_context_mode": "anonymous",
            "max_frequency": "1_per_day",
            "resource_quality_filter": 0.7,
        },
    }

    def build_community_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> CommunityDirective | None:
        """从 PolicyDecision 构建 CommunityDirective — 控制社群信号如何进入个人上下文。"""
        if signal.state_key not in ("community_cohort_pattern", "community_resource_recommendation"):
            return None

        params = self._COMMUNITY_MAP.get(signal.claim)
        if not params:
            return None

        return CommunityDirective(
            directive_id=_uid("cmd"),
            policy_decision_id=decision.policy_decision_id,
            cohort_hint_shown=params["cohort_hint_shown"],
            resource_quality_filter=params["resource_quality_filter"],
            peer_context_mode=params["peer_context_mode"],
            max_frequency=params["max_frequency"],
        )

    # ── SkillDirective ─────────────────────────────────────────────────

    _SKILL_MAP: dict[str, dict[str, Any]] = {
        "recent_task_too_large": {
            "skill_action": "inject",
        },
        "momentum_high": {
            "skill_action": "extract",
            "extraction_trigger": "outcome_positive",
        },
        "transfer_failure": {
            "skill_action": "recommend",
        },
    }

    def build_skill_directive(
        self,
        decision: PolicyDecision,
        signal: ActionableSignal,
    ) -> SkillDirective | None:
        """从 PolicyDecision 构建 SkillDirective — 控制技能注入/提取/推荐。"""
        params = self._SKILL_MAP.get(signal.claim)
        if not params:
            return None

        return SkillDirective(
            directive_id=_uid("skd"),
            policy_decision_id=decision.policy_decision_id,
            skill_action=params.get("skill_action", "none"),
            extraction_trigger=params.get("extraction_trigger", ""),
        )
