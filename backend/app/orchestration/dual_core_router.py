from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timezone, datetime
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    session_length_preference: int | None = None
    difficulty_preference: float | None = None


@dataclass(frozen=True)
class DualCoreDecision:
    mode: str
    reason: str
    cognitive_adjustments: list[str]
    execution_constraints: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "reason": self.reason,
            "cognitive_adjustments": list(self.cognitive_adjustments),
            "execution_constraints": list(self.execution_constraints),
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
        if self.execution_constraints:
            sections.append(
                "## 双核心执行约束\n"
                + "\n".join(f"- {item}" for item in self.execution_constraints)
            )
        return "\n\n".join(section for section in sections if section).strip()


class DualCoreRouter:
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

    def route(self, routing_input: DualCoreRoutingInput) -> DualCoreDecision:
        goal_clear = self._goal_is_clear(routing_input)
        emotional_block = self._has_emotional_block(routing_input)
        procrastination_pattern = self._has_procrastination_pattern(routing_input)
        cognitive_load_present = routing_input.primary_challenge_area in {"cognitive", "execution"}

        cognitive_adjustments: list[str] = []
        execution_constraints: list[str] = []

        if emotional_block:
            cognitive_adjustments.append("先处理用户当前的情绪阻力，再进入计划讨论。")
        if not goal_clear:
            cognitive_adjustments.append("先帮助用户澄清目标、约束和成功标准，再进入具体方案。")
        if procrastination_pattern:
            cognitive_adjustments.append("先识别最近的执行阻力，并把建议收敛为更容易启动的动作。")

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

        if (
            goal_clear
            and routing_input.information_sufficient
            and not emotional_block
            and not procrastination_pattern
        ):
            return DualCoreDecision(
                mode="execution_first",
                reason="目标清晰、信息充分，且当前没有明显情绪或执行阻塞，适合直接推进执行路径。",
                cognitive_adjustments=cognitive_adjustments[:2],
                execution_constraints=execution_constraints[:3],
            )

        if (
            not routing_input.information_sufficient
            or emotional_block
            or procrastination_pattern
            or (not goal_clear and routing_input.intent_confidence < 0.6)
        ):
            return DualCoreDecision(
                mode="cognitive_first",
                reason=self._cognitive_reason(
                    goal_clear=goal_clear,
                    information_sufficient=routing_input.information_sufficient,
                    emotional_block=emotional_block,
                    procrastination_pattern=procrastination_pattern,
                ),
                cognitive_adjustments=cognitive_adjustments[:3],
                execution_constraints=execution_constraints[:2],
            )

        balanced_reason = "当前同时存在推进任务和理解用户状态的需求，先保持双核心并行。"
        if goal_clear and cognitive_load_present:
            balanced_reason = "目标已经清楚，但当前还存在认知或执行摩擦，先在推进方案时同时做状态调制。"
        elif not goal_clear:
            balanced_reason = "目标还有部分边界要澄清，但已经可以先给出轻量推进方向。"
        return DualCoreDecision(
            mode="balanced",
            reason=balanced_reason,
            cognitive_adjustments=cognitive_adjustments[:2],
            execution_constraints=execution_constraints[:3],
        )

    def _goal_is_clear(self, routing_input: DualCoreRoutingInput) -> bool:
        intent = (routing_input.intent or "").strip().lower()
        return intent in self.CLEAR_INTENTS and routing_input.intent_confidence >= 0.72

    def _has_emotional_block(self, routing_input: DualCoreRoutingInput) -> bool:
        sentiments = routing_input.recent_sentiment_distribution or {}
        negative = sum(
            count for sentiment, count in sentiments.items()
            if sentiment in self.NEGATIVE_SENTIMENTS
        )
        total = sum(sentiments.values())
        ratio = (negative / total) if total else 0.0
        return (
            routing_input.primary_challenge_area == "emotional"
            or negative >= 2
            or ratio >= 0.5
        )

    def _has_procrastination_pattern(self, routing_input: DualCoreRoutingInput) -> bool:
        feedback = routing_input.recent_task_feedback_distribution or {}
        friction_signals = (
            feedback.get("too_long", 0)
            + feedback.get("unclear", 0)
            + feedback.get("irrelevant", 0)
        )
        return (
            friction_signals >= 3
            or feedback.get("too_difficult", 0) >= 3
            or routing_input.plan_health_status == "critical"
        )

    def _cognitive_reason(
        self,
        *,
        goal_clear: bool,
        information_sufficient: bool,
        emotional_block: bool,
        procrastination_pattern: bool,
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
        if not reasons:
            return "当前更适合先做状态澄清，再进入执行路径。"
        return "；".join(reasons) + "，所以这轮先走认知支持路径。"


dual_core_router = DualCoreRouter()
