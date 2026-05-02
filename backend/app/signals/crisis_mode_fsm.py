"""
CrisisModeFSM — formal state machine for exam pressure control.

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
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "deadline_pressure": self.deadline_pressure,
            "knowledge_gap": self.knowledge_gap,
            "fatigue": self.fatigue,
            "stress": self.stress,
            "deadline_passed": self.deadline_passed,
            "user_declared_recovered": self.user_declared_recovered,
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

    @classmethod
    def is_crisis_trigger(cls, signals: CrisisSignals) -> bool:
        """
        Trigger condition:
        deadline_pressure=critical + (knowledge_gap=major OR fatigue=critical OR stress=high)
        """
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

        return CrisisModeSnapshot(
            state=next_state,
            previous_state=previous_state,
            trigger_matched=trigger_matched,
            exit_reason=exit_reason,
            status_band_label=cls._status_label(next_state),
            status_band_explanation=cls._status_explanation(next_state, signals, exit_reason),
            policy_constraints=(
                dict(cls.CRISIS_POLICY_CONSTRAINTS)
                if next_state == CrisisState.CRISIS
                else {}
            ),
        )

    @staticmethod
    def _coerce_state(state: CrisisState | str) -> CrisisState:
        if isinstance(state, CrisisState):
            return state
        try:
            return CrisisState(str(state))
        except ValueError:
            return CrisisState.NORMAL

    @staticmethod
    def _status_label(state: CrisisState) -> str:
        return {
            CrisisState.NORMAL: "正常模式",
            CrisisState.WARNING: "考试高压预警",
            CrisisState.CRISIS: "危机模式中",
            CrisisState.RECOVERY: "危机恢复中",
        }[state]

    @staticmethod
    def _status_explanation(
        state: CrisisState,
        signals: CrisisSignals,
        exit_reason: str | None,
    ) -> str:
        if state == CrisisState.CRISIS:
            return (
                "截止压力已到 critical，且出现知识缺口、疲劳或高压力信号；"
                "本轮只保留最低过线路径。"
            )
        if state == CrisisState.WARNING:
            return "截止压力已到 critical，系统会收窄任务但尚未进入危机模式。"
        if state == CrisisState.RECOVERY:
            if exit_reason == "deadline_passed":
                return "考试截止已过，先用恢复节奏整理后续行动。"
            return "你已声明恢复，先用低压力节奏过渡。"
        return "未检测到危机触发条件。"

