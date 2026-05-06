"""
CrisisModeFSM — formal state machine for pressure control across goal types.

State order:
normal -> warning -> crisis -> recovery -> normal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CrisisState(StrEnum):
    """Canonical crisis mode states."""

    NORMAL = "normal"
    WARNING = "warning"
    CRISIS = "crisis"
    RECOVERY = "recovery"


@dataclass(frozen=True)
class CrisisSignals:
    """Inputs used by the crisis FSM."""

    deadline_pressure: str = "none"  # none | low | medium | high | critical
    knowledge_gap: str = "none"  # none | minor | moderate | major
    fatigue: str = "none"  # none | low | medium | high | critical
    stress: str = "none"  # none | medium | high
    deadline_passed: bool = False
    user_declared_recovered: bool = False
    goal_type: str = "exam"
    scope_bloat: bool = False  # project: scope exploded past 2x
    interview_imminent: bool = False  # job_search: interview in <=2 days
    injury_risk: bool = False  # fitness: injury detected
    skip_streak: int = 0  # fitness/habit: consecutive skips

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> CrisisSignals:
        if not payload:
            return cls()
        return cls(
            deadline_pressure=str(payload.get("deadline_pressure") or "none"),
            knowledge_gap=str(payload.get("knowledge_gap") or "none"),
            fatigue=str(payload.get("fatigue") or "none"),
            stress=str(payload.get("stress") or "none"),
            deadline_passed=bool(payload.get("deadline_passed", False)),
            user_declared_recovered=bool(payload.get("user_declared_recovered", False)),
            goal_type=str(payload.get("goal_type") or "exam"),
            scope_bloat=bool(payload.get("scope_bloat", False)),
            interview_imminent=bool(payload.get("interview_imminent", False)),
            injury_risk=bool(payload.get("injury_risk", False)),
            skip_streak=int(payload.get("skip_streak") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "deadline_pressure": self.deadline_pressure,
            "knowledge_gap": self.knowledge_gap,
            "fatigue": self.fatigue,
            "stress": self.stress,
            "deadline_passed": self.deadline_passed,
            "user_declared_recovered": self.user_declared_recovered,
            "goal_type": self.goal_type,
            "scope_bloat": self.scope_bloat,
            "interview_imminent": self.interview_imminent,
            "injury_risk": self.injury_risk,
            "skip_streak": self.skip_streak,
        }


@dataclass(frozen=True)
class CrisisModeSnapshot:
    """Serializable output from CrisisModeFSM."""

    state: CrisisState
    previous_state: CrisisState
    trigger_matched: bool
    exit_reason: str | None
    status_band_label: str
    status_band_explanation: str
    policy_constraints: dict[str, Any] = field(default_factory=dict)
    entered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "previous_state": self.previous_state.value,
            "trigger_matched": self.trigger_matched,
            "exit_reason": self.exit_reason,
            "status_band_label": self.status_band_label,
            "status_band_explanation": self.status_band_explanation,
            "policy_constraints": dict(self.policy_constraints),
            "entered_at": self.entered_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CrisisModeSnapshot:
        return cls(
            state=CrisisState(payload["state"]),
            previous_state=CrisisState(payload.get("previous_state", payload["state"])),
            trigger_matched=bool(payload.get("trigger_matched", False)),
            exit_reason=payload.get("exit_reason"),
            status_band_label=str(payload.get("status_band_label") or ""),
            status_band_explanation=str(payload.get("status_band_explanation") or ""),
            policy_constraints=dict(payload.get("policy_constraints") or {}),
            entered_at=str(payload.get("entered_at") or datetime.now(UTC).isoformat()),
        )


_GOAL_STATUS_LABELS: dict[str, dict[CrisisState, str]] = {
    "exam": {
        CrisisState.NORMAL: "正常模式",
        CrisisState.WARNING: "考试高压预警",
        CrisisState.CRISIS: "危机模式中",
        CrisisState.RECOVERY: "危机恢复中",
    },
    "project": {
        CrisisState.NORMAL: "正常模式",
        CrisisState.WARNING: "项目高压预警",
        CrisisState.CRISIS: "项目危机模式",
        CrisisState.RECOVERY: "恢复节奏中",
    },
    "job_search": {
        CrisisState.NORMAL: "正常模式",
        CrisisState.WARNING: "面试高压预警",
        CrisisState.CRISIS: "面试冲刺模式",
        CrisisState.RECOVERY: "恢复节奏中",
    },
    "fitness": {
        CrisisState.NORMAL: "正常模式",
        CrisisState.WARNING: "训练风险预警",
        CrisisState.CRISIS: "保护性恢复模式",
        CrisisState.RECOVERY: "恢复节奏中",
    },
    "startup": {
        CrisisState.NORMAL: "正常模式",
        CrisisState.WARNING: "创业高压预警",
        CrisisState.CRISIS: "MVP冲刺模式",
        CrisisState.RECOVERY: "恢复节奏中",
    },
    "general": {
        CrisisState.NORMAL: "正常模式",
        CrisisState.WARNING: "高压预警",
        CrisisState.CRISIS: "危机模式中",
        CrisisState.RECOVERY: "恢复节奏中",
    },
}


class CrisisModeFSM:
    """Deterministic crisis-mode state transitions."""

    CRISIS_POLICY_CONSTRAINTS: dict[str, Any] = {
        "max_task_duration_min": 15,
        "avoid_new_chapter": True,
        "retrieval_mode": "minimal_pass",
        "source_scope": "task_bound",
        "suppress_challenge_achievement_notifications": True,
        "aurora_l3_proactive_allowed": False,
    }

    GOAL_TYPE_CRISIS_CONSTRAINTS: dict[str, dict[str, Any]] = {
        "exam": {},  # uses CRISIS_POLICY_CONSTRAINTS as-is
        "project": {
            "max_task_duration_min": 20,
            "freeze_scope": True,
            "mvp_only": True,
            "avoid_new_chapter": True,
            "source_scope": "task_bound",
        },
        "job_search": {
            "max_task_duration_min": 20,
            "focus_top_companies": True,
            "avoid_new_applications": False,
            "source_scope": "task_bound",
        },
        "fitness": {
            "max_task_duration_min": 15,
            "reduce_intensity": True,
            "focus_recovery": True,
            "prevent_injury": True,
        },
        "startup": {
            "max_task_duration_min": 20,
            "freeze_scope": True,
            "mvp_only": True,
            "de_risk_only": True,
        },
        "general": {
            "max_task_duration_min": 15,
            "reduce_to_minimum": True,
        },
    }

    @classmethod
    def is_crisis_trigger(cls, signals: CrisisSignals) -> bool:
        """Goal-type-aware crisis trigger detection."""
        if signals.goal_type == "exam":
            return cls._exam_crisis_trigger(signals)
        if signals.goal_type == "project":
            return (
                signals.deadline_pressure == "critical" and signals.scope_bloat
            ) or (signals.deadline_passed and signals.stress == "high")
        if signals.goal_type == "job_search":
            return signals.interview_imminent and (
                signals.knowledge_gap in ("major", "moderate")
                or signals.stress == "high"
            )
        if signals.goal_type == "fitness":
            return signals.injury_risk or signals.skip_streak >= 5
        if signals.goal_type == "startup":
            return signals.deadline_pressure == "critical" and (
                signals.scope_bloat or signals.stress == "high"
            )
        # general: deadline pressure + stress/fatigue
        return signals.deadline_pressure == "critical" and (
            signals.fatigue in ("high", "critical") or signals.stress == "high"
        )

    @classmethod
    def _exam_crisis_trigger(cls, signals: CrisisSignals) -> bool:
        return signals.deadline_pressure == "critical" and (
            signals.knowledge_gap == "major"
            or signals.fatigue == "critical"
            or signals.stress == "high"
        )

    @classmethod
    def transition(
        cls,
        *,
        current_state: CrisisState | str = CrisisState.NORMAL,
        signals: CrisisSignals,
    ) -> CrisisModeSnapshot:
        previous_state = cls._coerce_state(current_state)
        trigger_matched = cls.is_crisis_trigger(signals)
        exit_reason: str | None = None

        if previous_state == CrisisState.CRISIS and (
            signals.deadline_passed or signals.user_declared_recovered
        ):
            next_state = CrisisState.RECOVERY
            exit_reason = "deadline_passed" if signals.deadline_passed else "user_recovered"
        elif previous_state == CrisisState.RECOVERY:
            next_state = CrisisState.CRISIS if trigger_matched else CrisisState.NORMAL
        elif trigger_matched:
            next_state = CrisisState.CRISIS
        elif signals.deadline_pressure == "critical":
            next_state = CrisisState.WARNING
        else:
            next_state = CrisisState.NORMAL

        goal_constraints = cls._goal_type_constraints(signals.goal_type)
        return CrisisModeSnapshot(
            state=next_state,
            previous_state=previous_state,
            trigger_matched=trigger_matched,
            exit_reason=exit_reason,
            status_band_label=cls._status_label(next_state, signals.goal_type),
            status_band_explanation=cls._status_explanation(next_state, signals, exit_reason),
            policy_constraints=goal_constraints if next_state == CrisisState.CRISIS else {},
        )

    @staticmethod
    def _coerce_state(state: CrisisState | str) -> CrisisState:
        if isinstance(state, CrisisState):
            return state
        try:
            return CrisisState(str(state))
        except ValueError:
            return CrisisState.NORMAL

    @classmethod
    def _goal_type_constraints(cls, goal_type: str) -> dict[str, Any]:
        base = dict(cls.CRISIS_POLICY_CONSTRAINTS)
        override = cls.GOAL_TYPE_CRISIS_CONSTRAINTS.get(goal_type, {})
        base.update(override)
        return base

    @staticmethod
    def _status_label(state: CrisisState, goal_type: str = "exam") -> str:
        return _GOAL_STATUS_LABELS.get(goal_type, _GOAL_STATUS_LABELS["exam"])[state]

    @staticmethod
    def _status_explanation(
        state: CrisisState,
        signals: CrisisSignals,
        exit_reason: str | None,
    ) -> str:
        gt = signals.goal_type
        if state == CrisisState.CRISIS:
            if gt == "project":
                return "项目截止压力已达极限，先砍到MVP只保留核心交付。"
            if gt == "job_search":
                return "面试马上开始，只练最高频题和核心回答框架。"
            if gt == "fitness":
                return "检测到伤病风险或连续跳过训练，降负荷专注恢复。"
            if gt == "startup":
                return "截止压力已达极限，冻结范围只做最小可行验证。"
            if gt == "general":
                return "压力已达极限，先降到最小可行任务。"
            return (
                "截止压力已到 critical，且出现知识缺口、疲劳或高压力信号；"
                "本轮只保留最低过线路径。"
            )
        if state == CrisisState.WARNING:
            if gt == "project":
                return "项目截止压力升高，系统会收窄范围但尚未进入危机模式。"
            if gt == "job_search":
                return "面试时间临近，系统会调整任务但尚未进入冲刺模式。"
            if gt == "fitness":
                return "检测到训练风险信号，系统会降低强度。"
            if gt == "startup":
                return "创业截止压力升高，系统会收窄范围。"
            if gt == "general":
                return "压力升高，系统会收窄任务范围。"
            return "截止压力已到 critical，系统会收窄任务但尚未进入危机模式。"
        if state == CrisisState.RECOVERY:
            if exit_reason == "deadline_passed":
                if gt == "project":
                    return "项目截止已过，先用恢复节奏整理后续行动。"
                if gt == "startup":
                    return "里程碑截止已过，先用恢复节奏整理后续行动。"
                return "考试截止已过，先用恢复节奏整理后续行动。"
            return "你已声明恢复，先用低压力节奏过渡。"
        return "未检测到危机触发条件。"

