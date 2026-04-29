from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.services.social_signal_types import SocialSignalsV1
from app.services.srl_phase_types import SRLPhaseHint
from app.state_aggregator.schema import MetacognitionHintV1


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class AdaptationRecord:
    what_changed: str
    why: str
    expected_effect: str
    user_facing_message: str
    source: str
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    record_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "what_changed": self.what_changed,
            "why": self.why,
            "expected_effect": self.expected_effect,
            "user_facing_message": self.user_facing_message,
            "source": self.source,
            "created_at": self.created_at,
        }
        if self.record_id:
            payload["record_id"] = self.record_id
        return payload


@dataclass(frozen=True)
class DualCoreRoutingInput:
    intent: str
    intent_confidence: float
    information_sufficient: bool
    primary_challenge_area: str | None
    recent_sentiment_distribution: dict[str, int]
    has_active_plan: bool
    plan_health_status: str | None
    recent_task_feedback_distribution: dict[str, int]
    behavior_pattern_names: list[str] = field(default_factory=list)
    behavior_pattern_types: dict[str, int] = field(default_factory=dict)
    behavior_pattern_details: list[dict[str, Any]] = field(default_factory=list)
    session_length_preference: int | None = None
    difficulty_preference: float | None = None
    emotional_block_detected: bool = False
    procrastination_pattern: bool = False
    cognitive_mode_suggested: bool = False
    suggested_verbosity: str | None = None
    current_guidance: str | None = None
    routing_profile: dict[str, float] = field(default_factory=dict)
    adaptive_adjustments: dict[str, Any] = field(default_factory=dict)
    social_signals: SocialSignalsV1 | None = None
    srl_phase_hint: SRLPhaseHint | None = None
    metacognition_hint: MetacognitionHintV1 | None = None
    cognitive_load: float | None = None
    capsule_preferences: dict[str, Any] = field(default_factory=dict)
    spine_active_states: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CognitiveAdjustment:
    """Structured cognitive adjustment from Dual-Core Router."""
    dimension: str  # tone, verbosity, challenge_level, explanation_depth, etc.
    value: str | int | float
    reason: str
    evidence: list[str] = field(default_factory=list)
    scope: str = "turn"  # turn, session, sprint
    user_visible: bool = False
    ttl: str | None = None

    def to_text(self) -> str:
        return f"{self.dimension}={self.value} ({self.reason})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "value": self.value,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "scope": self.scope,
            "user_visible": self.user_visible,
            "ttl": self.ttl,
        }


@dataclass(frozen=True)
class DualCoreDecision:
    mode: str
    reason: str
    cognitive_adjustments: list[str]
    execution_constraints: list[str]
    routing_debug: dict[str, Any] = field(default_factory=dict)
    strategy_adjustments: list[dict[str, Any]] = field(default_factory=list)
    structured_adjustments: list[CognitiveAdjustment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "reason": self.reason,
            "cognitive_adjustments": list(self.cognitive_adjustments),
            "structured_adjustments": [a.to_dict() for a in self.structured_adjustments],
            "execution_constraints": list(self.execution_constraints),
            "routing_debug": dict(self.routing_debug or {}),
            "strategy_adjustments": [dict(item) for item in self.strategy_adjustments if isinstance(item, dict)],
        }

    @property
    def ux_mode(self) -> str:
        if self.mode == "execution_first":
            return "execution"
        if self.mode == "cognitive_first":
            return "cognitive"
        return "balanced"

    @property
    def prompt_instruction(self) -> str:
        sections: list[str] = []
        if self.cognitive_adjustments:
            sections.append(
                "## 双核心认知调制\n"
                + "\n".join(f"- {item}" for item in self.cognitive_adjustments)
            )
        if self.structured_adjustments:
            lines = [f"- {adj.to_text()}" for adj in self.structured_adjustments]
            if lines:
                sections.append("## 结构化认知调整\n" + "\n".join(lines))
        if self.execution_constraints:
            sections.append(
                "## 双核心执行约束\n"
                + "\n".join(f"- {item}" for item in self.execution_constraints)
            )
        return "\n\n".join(section for section in sections if section).strip()


class DualCoreRouter:
    DEFAULT_ROUTING_PROFILE = {
        "procrastination_threshold": 0.6,
        "emotional_sensitivity": 0.5,
        "directness_preference": 0.5,
    }
    NEGATIVE_SENTIMENTS = {
        "anxious",
        "burnout",
        "depressed",
        "stressed",
        "overwhelmed",
        "frustrated",
        "negative",
        "sad",
    }
    CLEAR_INTENTS = {
        "plan",
        "task",
        "sprint_plan",
        "error_diagnosis",
        "translation",
        "knowledge",
    }
    PROCRASTINATION_KEYWORDS = {
        "procrast",
        "avoid",
        "拖延",
        "回避",
        "启动困难",
        "执行阻力",
    }
    PERFECTIONISM_KEYWORDS = {
        "perfection",
        "完美主义",
        "过度打磨",
        "高标准卡住",
    }
    PLANNING_FALLACY_KEYWORDS = {
        "planning fallacy",
        "计划谬误",
        "时间估计偏差",
        "低估耗时",
    }

    def route(self, routing_input: DualCoreRoutingInput) -> DualCoreDecision:
        profile = self._resolved_profile(routing_input)
        goal_clarity_score = self._goal_clarity_score(routing_input)
        goal_clear_threshold = self._goal_clear_threshold(profile)
        low_conf_threshold = self._low_confidence_threshold(profile)
        emotional_block_score = self._emotional_block_score(routing_input)
        procrastination_score = self._procrastination_score(routing_input)

        goal_clear = goal_clarity_score >= goal_clear_threshold
        emotional_block = self._has_emotional_block(routing_input, emotional_block_score, profile)
        procrastination_pattern = self._has_procrastination_pattern(
            routing_input,
            procrastination_score,
            profile,
        )
        cognitive_mode_suggested = bool(routing_input.cognitive_mode_suggested)
        pattern_guidance = self._pattern_guidance(routing_input)
        cognitive_load_value = float(routing_input.cognitive_load or 0.0)
        high_cognitive_load = routing_input.cognitive_load is not None and cognitive_load_value >= 0.55
        very_high_cognitive_load = routing_input.cognitive_load is not None and cognitive_load_value >= 0.78
        capsule_preferences = self._normalized_capsule_preferences(routing_input)
        capsule_method_preferences = capsule_preferences.get("method_preferences", [])

        cognitive_adjustments: list[str] = []
        execution_constraints: list[str] = []
        strategy_adjustments: list[dict[str, Any]] = []
        confidence_gate = round(max(0.55, min(0.95, float(routing_input.intent_confidence or 0.7))), 2)

        def recommend_strategy(field: str, recommended_value: Any, *, reason: str) -> None:
            if any(str(item.get("field") or "").strip() == field for item in strategy_adjustments):
                return
            strategy_adjustments.append(
                {
                    "field": field,
                    "recommended_value": recommended_value,
                    "target_layer": "session",
                    "reversible": True,
                    "confidence_gate": confidence_gate,
                    "reason": reason,
                    "source": "dual_core_router",
                }
            )

        if emotional_block:
            cognitive_adjustments.append("先处理用户当前的情绪阻力，再进入计划讨论。")
            recommend_strategy(
                "session_mode",
                "recovery",
                reason="Emotional blockage should switch the session into a lighter recovery stance before planning.",
            )
            recommend_strategy(
                "intervention_intensity",
                "low",
                reason="High-friction turns need softer intervention intensity so the move stays reversible.",
            )
        if not goal_clear:
            cognitive_adjustments.append("先帮助用户澄清目标、约束和成功标准，再进入具体方案。")
            recommend_strategy(
                "explanation_style",
                "step_by_step",
                reason="When the goal boundary is still blurry, the explanation path should slow down and clarify one step at a time.",
            )
        if procrastination_pattern:
            cognitive_adjustments.append("先识别最近的执行阻力，并把建议收敛为更容易启动的动作。")
            recommend_strategy(
                "difficulty_level",
                2,
                reason="Execution friction should lower the startup bar before the system asks for another push.",
            )
        if cognitive_mode_suggested:
            cognitive_adjustments.append("先校准理解偏差或概念卡点，再决定执行方案。")
            recommend_strategy(
                "explanation_style",
                "step_by_step",
                reason="Conceptual confusion benefits from a slower, incremental explanation mode.",
            )
        cognitive_adjustments.extend(pattern_guidance["cognitive"])
        if routing_input.suggested_verbosity == "supportive":
            cognitive_adjustments.append("表达上更支持、更低压力，避免把建议说成必须立刻完成。")
            recommend_strategy(
                "push_vs_support",
                0.25,
                reason="Supportive delivery should reduce pressure and keep the tone on the user's side.",
            )
        if high_cognitive_load:
            cognitive_adjustments.append("当前认知负荷偏高，先降低方案复杂度，再给更容易启动的下一步。")
            recommend_strategy(
                "explanation_style",
                "step_by_step",
                reason="High cognitive load benefits from simpler, more incremental explanations.",
            )
            recommend_strategy(
                "intervention_intensity",
                "low",
                reason="High cognitive load should lower intervention intensity so the turn stays easy to absorb.",
            )
            if very_high_cognitive_load:
                recommend_strategy(
                    "planning_granularity",
                    "startup_ready",
                    reason="Very high cognitive load should compress planning into the smallest viable starting slice.",
                )
        social_signals = routing_input.social_signals
        metacognition_hint = routing_input.metacognition_hint
        if social_signals is not None:
            if social_signals.pending_commitments_count > 0:
                execution_constraints.append("若要安排下一步，请先兼容用户已有的对外承诺，避免叠加新的长期负债。")
            if (
                social_signals.social_learning_preference is not None
                and social_signals.social_learning_preference >= 0.65
                and social_signals.mention_count > 0
            ):
                execution_constraints.append("若任务天然适合协作，可允许用户借助同伴或群组来启动，但不要把社交化当成硬要求。")
            if social_signals.relationship_count > 0:
                cognitive_adjustments.append("涉及他人或协作情境时，保持边界感，不要替用户许诺或推断他人立场。")

        srl_phase_hint = routing_input.srl_phase_hint
        reflection_phase_detected = False
        if srl_phase_hint is not None:
            if srl_phase_hint.current_phase == "forethought":
                cognitive_adjustments.append("用户当前处在前瞻准备阶段，先帮他明确目标、约束和启动标准，再展开细节。")
                recommend_strategy(
                    "planning_granularity",
                    "startup_ready",
                    reason="Forethought users benefit from tighter success criteria and a clear launch point before more detail is added.",
                )
            elif srl_phase_hint.current_phase == "performance":
                execution_constraints.append("用户当前处在执行监控阶段，优先维持连续执行，给出能立刻开始的短步动作。")
                recommend_strategy(
                    "execution_window",
                    "momentum_preserving",
                    reason="Performance-phase support should preserve momentum instead of reopening broad planning loops.",
                )
            elif srl_phase_hint.current_phase == "reflection":
                reflection_phase_detected = srl_phase_hint.confidence >= 0.55
                cognitive_adjustments.append("用户当前处在复盘反思阶段，先帮助总结哪里有效、哪里失灵，再决定下一轮怎么改。")
                recommend_strategy(
                    "session_mode",
                    "reflection",
                    reason="Reflection-phase turns should surface what worked or failed before pushing the user back into execution.",
                )

        low_metacognition_accuracy = False
        strong_metacognition_execution_bias = False
        if metacognition_hint is not None:
            low_metacognition_accuracy = metacognition_hint.accuracy < 0.5
            strong_metacognition_execution_bias = (
                metacognition_hint.accuracy > 0.8 and metacognition_hint.awareness == "strong"
            )
            if low_metacognition_accuracy:
                cognitive_adjustments.append("用户最近对自己状态或耗时的判断偏差较大，先校准判断，再进入执行推进。")
                recommend_strategy(
                    "intervention_intensity",
                    "low",
                    reason="Low metacognitive accuracy means the system should reduce proactive pushing and recalibrate first.",
                )
                recommend_strategy(
                    "push_vs_support",
                    0.2,
                    reason="When self-monitoring is noisy, the delivery should skew toward support instead of pressure.",
                )
            elif strong_metacognition_execution_bias:
                execution_constraints.append("用户对自身状态的觉察较强，减少重复确认与打扰，直接给出可执行下一步。")
                recommend_strategy(
                    "check_in_frequency",
                    "minimal",
                    reason="Strong metacognitive awareness allows the system to reduce interruptions and trust the user to self-monitor.",
                )
                recommend_strategy(
                    "intervention_intensity",
                    "low",
                    reason="High metacognitive accuracy supports a lower-friction execution path with fewer interruptions.",
                )

        # ── Spine StateRegister signals ──
        spine_states = routing_input.spine_active_states
        spine_fatigue_detected = False
        spine_execution_low = False
        spine_knowledge_bottleneck = False
        for ss in spine_states:
            key = str(ss.get("state_key", ""))
            value = str(ss.get("value", ""))
            conf = float(ss.get("confidence", 0))
            if conf < 0.45:
                continue
            if (
                key in ("fatigue_accumulated", "affective_pressure", "cognitive_load", "notification_fatigue")
                or value in {"high_load", "high_load_detected", "overloaded", "anxious", "tense"}
            ) and conf >= 0.6:
                spine_fatigue_detected = True
                cognitive_adjustments.append("Spine 检测到累积疲劳或情绪压力，优先降负荷、给恢复建议。")
                recommend_strategy(
                    "intervention_intensity",
                    "low",
                    reason="Spine fatigue signal suggests reducing proactive pressure and offering recovery-oriented support.",
                )
            if key in ("execution_consistency", "task_granularity_fit") and conf >= 0.55:
                spine_execution_low = True
                execution_constraints.append("Spine 检测到执行连贯性或任务粒度偏差，优先给更容易启动的短步动作。")
                recommend_strategy(
                    "planning_granularity",
                    "startup_ready",
                    reason="Spine execution-consistency signal suggests preserving momentum with smaller steps.",
                )
            if key in ("knowledge_bottleneck", "knowledge_transfer") and conf >= 0.55:
                spine_knowledge_bottleneck = True
                cognitive_adjustments.append("Spine 检测到知识瓶颈，先帮助理解核心概念再推进。")
                recommend_strategy(
                    "explanation_style",
                    "step_by_step",
                    reason="Knowledge bottleneck should slow down explanation and focus on foundational understanding.",
                )
            if key == "reward_engagement" and conf >= 0.55:
                recommend_strategy(
                    "push_vs_support",
                    0.6,
                    reason="Recent reward engagement indicates user is invested; moderate encouragement can sustain momentum.",
                )
            if key == "deadline_pressure" and conf >= 0.6:
                execution_constraints.append("Spine 检测到截止日期压力，优先安排与截止日期相关的复习或冲刺任务。")
                recommend_strategy(
                    "planning_granularity",
                    "startup_ready",
                    reason="Deadline pressure should focus planning into immediately actionable steps.",
                )
                recommend_strategy(
                    "execution_window",
                    "momentum_preserving",
                    reason="Deadline pressure should preserve momentum and avoid opening new planning loops.",
                )

        if routing_input.session_length_preference and routing_input.session_length_preference <= 25:
            execution_constraints.append(
                f"用户偏好短冲刺，单次任务默认控制在 {routing_input.session_length_preference} 分钟以内。"
            )
        if (
            routing_input.difficulty_preference is not None
            and routing_input.difficulty_preference < 0.4
        ):
            execution_constraints.append("降低任务初始难度，避免一开始就给高压挑战。")
        if routing_input.recent_task_feedback_distribution.get("too_difficult", 0) >= 2:
            execution_constraints.append("近期连续反馈“太难”，当前回复避免再加码任务强度。")
        if routing_input.recent_task_feedback_distribution.get("too_long", 0) >= 2:
            execution_constraints.append("近期连续反馈“太长”，优先拆成更短、更容易启动的步骤。")
        if capsule_method_preferences:
            top_method = capsule_method_preferences[0]
            method_label = str(top_method.get("label") or "").strip()
            method_key = str(top_method.get("key") or "").strip()
            if method_label:
                execution_constraints.append(
                    f"用户偏好{method_label}；当本轮适合安排学习或执行节奏时，优先用该方法组织下一步，但不要强行套用。"
                )
                recommend_strategy(
                    "execution_method",
                    method_key or method_label,
                    reason="Favorite capsule history indicates this execution method is personally salient for the user.",
                )
        execution_constraints.extend(pattern_guidance["execution"])

        # Translate numeric adaptive adjustments from ParameterCompiler
        if routing_input.adaptive_adjustments:
            diff_shift = routing_input.adaptive_adjustments.get("difficulty_shift", 0.0)
            if diff_shift < 0:
                cognitive_adjustments.append("建议降低子任务的难度，提供更简单、容易上手的步骤。")
            elif diff_shift > 0:
                cognitive_adjustments.append("建议适当提高挑战性，给出更进阶的内容或任务。")

            time_mult = routing_input.adaptive_adjustments.get("time_multiplier", 1.0)
            if time_mult > 1.0:
                extra_pct = int((time_mult - 1.0) * 100)
                execution_constraints.append(f"执行时间预估应增加 {extra_pct}%，留出更多缓冲时间。")
            elif time_mult < 1.0:
                less_pct = int((1.0 - time_mult) * 100)
                execution_constraints.append(f"执行时间预估可减少 {less_pct}%，建议更紧凑的节奏。")

            if routing_input.adaptive_adjustments.get("insert_prerequisite_review"):
                execution_constraints.append("必须插入前置知识的复习步骤。")

            max_tasks = routing_input.adaptive_adjustments.get("max_concurrent_tasks")
            if max_tasks is not None and max_tasks < 3:
                execution_constraints.append(f"控制并发任务数量，单次推进不要超过 {max_tasks} 个任务。")

        routing_debug = {
            "goal_clarity_score": round(goal_clarity_score, 3),
            "goal_clear_threshold": round(goal_clear_threshold, 3),
            "procrastination_score": round(procrastination_score, 3),
            "procrastination_threshold": round(profile["procrastination_threshold"], 3),
            "emotional_block_score": round(emotional_block_score, 3),
            "emotional_sensitivity": round(profile["emotional_sensitivity"], 3),
            "directness_preference": round(profile["directness_preference"], 3),
            "explicit_procrastination_signal": bool(routing_input.procrastination_pattern),
            "explicit_emotional_signal": bool(routing_input.emotional_block_detected),
            "explicit_cognitive_signal": cognitive_mode_suggested,
            "explicit_social_signal": social_signals is not None,
            "social_signal_payload": social_signals.to_payload() if social_signals is not None else None,
            "explicit_srl_signal": srl_phase_hint is not None,
            "srl_phase_payload": srl_phase_hint.to_payload() if srl_phase_hint is not None else None,
            "explicit_metacognition_signal": metacognition_hint is not None,
            "cognitive_load": round(cognitive_load_value, 4) if routing_input.cognitive_load is not None else None,
            "metacognition_hint_payload": (
                {
                    "accuracy": round(metacognition_hint.accuracy, 4),
                    "awareness": metacognition_hint.awareness,
                    "last_updated": metacognition_hint.last_updated.isoformat(),
                }
                if metacognition_hint is not None
                else None
            ),
            "explicit_capsule_signal": bool(capsule_preferences),
            "capsule_preferences": capsule_preferences or None,
            "capsule_method_preferences": capsule_method_preferences,
            "explicit_spine_state_signal": bool(spine_states),
            "spine_state_count": len(spine_states),
            "spine_fatigue_detected": spine_fatigue_detected,
            "spine_execution_low": spine_execution_low,
            "spine_knowledge_bottleneck": spine_knowledge_bottleneck,
            "spine_state_keys": [
                str(item.get("state_key", ""))
                for item in spine_states[:8]
                if isinstance(item, dict) and item.get("state_key")
            ],
        }
        if social_signals is not None:
            routing_debug["social_relationship_count"] = social_signals.relationship_count
            routing_debug["social_pending_commitments_count"] = social_signals.pending_commitments_count
            routing_debug["social_learning_preference"] = social_signals.social_learning_preference
        if srl_phase_hint is not None:
            routing_debug["srl_phase"] = srl_phase_hint.current_phase
            routing_debug["srl_confidence"] = srl_phase_hint.confidence
        if metacognition_hint is not None:
            routing_debug["metacognition_accuracy"] = round(metacognition_hint.accuracy, 4)
            routing_debug["metacognition_awareness"] = metacognition_hint.awareness

        if (
            (goal_clear or strong_metacognition_execution_bias)
            and routing_input.information_sufficient
            and not emotional_block
            and not procrastination_pattern
            and not cognitive_mode_suggested
            and not reflection_phase_detected
            and not low_metacognition_accuracy
            and not high_cognitive_load
            and not spine_fatigue_detected
            and not spine_knowledge_bottleneck
        ):
            return DualCoreDecision(
                mode="execution_first",
                reason=(
                    "用户对自身状态觉察稳定，且当前没有明显情绪或执行阻塞，适合减少打扰并直接推进执行路径。"
                    if strong_metacognition_execution_bias
                    else "目标清晰、信息充分，且当前没有明显情绪或执行阻塞，适合直接推进执行路径。"
                ),
                cognitive_adjustments=cognitive_adjustments[:2],
                execution_constraints=execution_constraints[:3],
                routing_debug=routing_debug,
                strategy_adjustments=strategy_adjustments[:5],
            )

        if (
            not routing_input.information_sufficient
            or emotional_block
            or procrastination_pattern
            or reflection_phase_detected
            or low_metacognition_accuracy
            or very_high_cognitive_load
            or spine_fatigue_detected
            or spine_knowledge_bottleneck
            or (cognitive_mode_suggested and not goal_clear)
            or (not goal_clear and routing_input.intent_confidence < low_conf_threshold)
        ):
            return DualCoreDecision(
                mode="cognitive_first",
                reason=self._cognitive_reason(
                    goal_clear=goal_clear,
                    information_sufficient=routing_input.information_sufficient,
                    emotional_block=emotional_block,
                    procrastination_pattern=procrastination_pattern,
                    cognitive_mode_suggested=cognitive_mode_suggested,
                ),
                cognitive_adjustments=cognitive_adjustments[:3],
                execution_constraints=execution_constraints[:2],
                routing_debug=routing_debug,
                strategy_adjustments=strategy_adjustments[:5],
            )

        balanced_reason = "当前同时存在推进任务和理解用户状态的需求，先保持双核心并行。"
        if goal_clear and high_cognitive_load:
            balanced_reason = "目标已经清楚，但当前还存在认知或执行摩擦，先在推进方案时同时做状态调制。"
        elif spine_execution_low:
            balanced_reason = "目标可以推进，但 Spine 状态寄存器提示近期执行连续性或任务颗粒度有风险，先压缩下一步。"
        elif not goal_clear:
            balanced_reason = "目标还有部分边界要澄清，但已经可以先给出轻量推进方向。"
        return DualCoreDecision(
            mode="balanced",
            reason=balanced_reason,
            cognitive_adjustments=cognitive_adjustments[:2],
            execution_constraints=execution_constraints[:3],
            routing_debug=routing_debug,
            strategy_adjustments=strategy_adjustments[:5],
        )

    def _goal_clarity_score(self, routing_input: DualCoreRoutingInput) -> float:
        intent = (routing_input.intent or "").strip().lower()
        base = float(routing_input.intent_confidence or 0.0)
        if intent not in self.CLEAR_INTENTS:
            base *= 0.7
        if routing_input.procrastination_pattern:
            base -= 0.1
        if routing_input.cognitive_mode_suggested:
            base -= 0.08
        return max(0.0, min(base, 1.0))

    def _has_emotional_block(
        self,
        routing_input: DualCoreRoutingInput,
        emotional_block_score: float,
        profile: dict[str, float],
    ) -> bool:
        if routing_input.emotional_block_detected:
            return True
        return emotional_block_score >= profile["emotional_sensitivity"]

    def _emotional_block_score(self, routing_input: DualCoreRoutingInput) -> float:
        sentiments = routing_input.recent_sentiment_distribution or {}
        negative = sum(
            count for sentiment, count in sentiments.items()
            if sentiment in self.NEGATIVE_SENTIMENTS
        )
        total = sum(sentiments.values())
        ratio = (negative / total) if total else 0.0
        score = ratio
        if routing_input.primary_challenge_area == "emotional":
            score = max(score, 0.75)
        if negative >= 2:
            score = max(score, 0.6)
        if self._pattern_details_include(routing_input, {"overload", "burnout", "anxiety"}):
            score = max(score, 0.7)
        return max(0.0, min(score, 1.0))

    def _has_procrastination_pattern(
        self,
        routing_input: DualCoreRoutingInput,
        procrastination_score: float,
        profile: dict[str, float],
    ) -> bool:
        if routing_input.procrastination_pattern:
            return True
        return procrastination_score >= profile["procrastination_threshold"]

    def _procrastination_score(self, routing_input: DualCoreRoutingInput) -> float:
        feedback = routing_input.recent_task_feedback_distribution or {}
        friction_signals = (
            feedback.get("too_long", 0)
            + feedback.get("unclear", 0)
            + feedback.get("irrelevant", 0)
        )
        pattern_names = self._normalized_pattern_names(routing_input)
        score = min(0.95, friction_signals * 0.18)
        if feedback.get("too_difficult", 0) >= 3:
            score = max(score, 0.72)
        if routing_input.plan_health_status == "critical":
            score = max(score, 0.68)
        if self._contains_any(pattern_names, self.PROCRASTINATION_KEYWORDS):
            score = max(score, 0.78)
        if self._pattern_details_include(
            routing_input,
            {"procrastination", "avoidance", "focus_decay", "perfectionism_avoidance"},
        ):
            score = max(score, 0.8)
        return max(0.0, min(score, 1.0))

    def _pattern_guidance(self, routing_input: DualCoreRoutingInput) -> dict[str, list[str]]:
        pattern_names = self._normalized_pattern_names(routing_input)
        pattern_types = routing_input.behavior_pattern_types or {}
        cognitive: list[str] = []
        execution: list[str] = []

        if self._contains_any(pattern_names, self.PROCRASTINATION_KEYWORDS):
            cognitive.append("结合你最近的执行型模式信号，先把第一步降到几分钟内可启动。")
        if self._contains_any(pattern_names, self.PERFECTIONISM_KEYWORDS):
            cognitive.append("先缓解“必须一次做到最好”的压力，再讨论下一步。")
            execution.append("给出最小可交付版本，明确“先完成再优化”的边界。")
        if self._contains_any(pattern_names, self.PLANNING_FALLACY_KEYWORDS):
            execution.append("对时间预估加入缓冲，避免按理想速度承诺。")
        if pattern_types.get("emotional", 0) >= 2:
            cognitive.append("近期情绪型模式较集中，先用更稳的节奏降低心理摩擦。")
        if pattern_types.get("execution", 0) >= 2:
            execution.append("把建议压缩成更具体的动作和检查点，减少执行摩擦。")
        if pattern_types.get("cognitive", 0) >= 2:
            cognitive.append("先澄清理解偏差和决策依据，再推进复杂方案。")

        return {
            "cognitive": cognitive,
            "execution": execution,
        }

    @staticmethod
    def _normalized_capsule_preferences(routing_input: DualCoreRoutingInput) -> dict[str, Any]:
        raw = routing_input.capsule_preferences if isinstance(routing_input.capsule_preferences, dict) else {}
        if not raw:
            return {}

        methods: list[dict[str, Any]] = []
        for method in list(raw.get("method_preferences") or raw.get("capsule_method_preferences") or []):
            if not isinstance(method, dict):
                continue
            label = str(method.get("label") or method.get("name") or "").strip()
            if not label:
                continue
            methods.append(
                {
                    "key": str(method.get("key") or label).strip(),
                    "label": label,
                    "count": int(method.get("count") or 1),
                    "confidence": float(method.get("confidence") or 0.6),
                }
            )

        summaries = [
            str(item).strip()
            for item in list(raw.get("method_preference_summary") or [])
            if str(item).strip()
        ]
        if not methods:
            for summary in summaries:
                label = summary.replace("用户偏好", "", 1).strip()
                if label:
                    methods.append({"key": label, "label": label, "count": 1, "confidence": 0.6})

        normalized = {
            "favorite_count": int(raw.get("favorite_count") or 0),
            "content_depth_preference": str(raw.get("content_depth_preference") or "").strip() or None,
            "subject_affinity": [
                str(subject).strip()
                for subject in list(raw.get("subject_affinity") or raw.get("content_subject_affinities") or [])
                if str(subject).strip()
            ][:3],
            "method_preferences": methods[:3],
            "method_preference_summary": summaries[:3]
            or [f"用户偏好{method['label']}" for method in methods[:3]],
        }
        return normalized if any(normalized.values()) else {}

    def _normalized_pattern_names(self, routing_input: DualCoreRoutingInput) -> list[str]:
        names = [
            str(name).strip().lower()
            for name in (routing_input.behavior_pattern_names or [])
            if str(name).strip()
        ]
        for item in routing_input.behavior_pattern_details or []:
            if not isinstance(item, dict):
                continue
            for key in ("pattern_name", "raw_pattern_name", "canonical_key"):
                raw = str(item.get(key) or "").strip().lower()
                if raw:
                    names.append(raw)
        return names

    def _contains_any(self, pattern_names: list[str], keywords: set[str]) -> bool:
        if not pattern_names:
            return False
        return any(
            keyword in name
            for name in pattern_names
            for keyword in keywords
        )

    def _pattern_details_include(
        self,
        routing_input: DualCoreRoutingInput,
        keywords: set[str],
    ) -> bool:
        for item in routing_input.behavior_pattern_details or []:
            if not isinstance(item, dict):
                continue
            haystacks = [
                str(item.get("canonical_key") or "").strip().lower(),
                str(item.get("raw_pattern_name") or "").strip().lower(),
                str(item.get("pattern_name") or "").strip().lower(),
                str(item.get("description") or "").strip().lower(),
            ]
            if any(keyword in haystack for haystack in haystacks for keyword in keywords):
                return True
        return False

    def _resolved_profile(self, routing_input: DualCoreRoutingInput) -> dict[str, float]:
        profile = dict(self.DEFAULT_ROUTING_PROFILE)
        raw = routing_input.routing_profile or {}
        for key, default in self.DEFAULT_ROUTING_PROFILE.items():
            value = raw.get(key, default)
            if isinstance(value, (int, float)):
                profile[key] = max(0.2, min(0.85, float(value)))
        return profile

    @staticmethod
    def _goal_clear_threshold(profile: dict[str, float]) -> float:
        directness = profile.get("directness_preference", 0.5)
        return max(0.55, min(0.8, 0.72 - (directness - 0.5) * 0.2))

    @staticmethod
    def _low_confidence_threshold(profile: dict[str, float]) -> float:
        directness = profile.get("directness_preference", 0.5)
        return max(0.35, min(0.7, 0.6 - (directness - 0.5) * 0.2))

    def _cognitive_reason(
        self,
        *,
        goal_clear: bool,
        information_sufficient: bool,
        emotional_block: bool,
        procrastination_pattern: bool,
        cognitive_mode_suggested: bool,
    ) -> str:
        reasons: list[str] = []
        if not goal_clear:
            reasons.append("目标还不够清晰")
        if not information_sufficient:
            reasons.append("当前信息还不够支撑高质量方案")
        if emotional_block:
            reasons.append("当前存在明显情绪阻力")
        if procrastination_pattern:
            reasons.append("最近的执行反馈显示阻力在累积")
        if cognitive_mode_suggested:
            reasons.append("当前更像是理解卡点而不是单纯执行问题")
        if not reasons:
            return "当前更适合先做状态澄清，再进入执行路径。"
        return "；".join(reasons) + "，所以这轮先走认知支持路径。"


dual_core_router = DualCoreRouter()
