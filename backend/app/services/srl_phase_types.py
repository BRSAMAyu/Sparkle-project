from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SRLPhase(str, Enum):
    FORETHOUGHT = "FORETHOUGHT"
    PERFORMANCE = "PERFORMANCE"
    SELF_REFLECTION = "SELF_REFLECTION"
    UNKNOWN = "UNKNOWN"


SRLPhaseSource = Literal["event_triggered", "trait_primed", "default"]


class SRLPhaseState(BaseModel):
    user_id: UUID
    current_phase: SRLPhase = SRLPhase.UNKNOWN
    phase_started_at: datetime = Field(default_factory=_utcnow)
    previous_phase: SRLPhase | None = None
    transition_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: SRLPhaseSource = "default"
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        normalized = float(value)
        if normalized < 0.0 or normalized > 1.0:
            raise ValueError("confidence must be within [0, 1]")
        return round(normalized, 4)


@dataclass(frozen=True)
class SRLPhaseHint:
    current_phase: str
    confidence: float
    source: str | None = None
    phase_started_at: str | None = None
    freshness_seconds: int | None = None

    PHASE_ALIASES = {
        "FORETHOUGHT": "forethought",
        "PERFORMANCE": "performance",
        "SELF_REFLECTION": "reflection",
        "REFLECTION": "reflection",
        "UNKNOWN": "unknown",
    }
    PHASE_LABELS = {
        "forethought": "前瞻准备",
        "performance": "执行监控",
        "reflection": "复盘反思",
        "unknown": "未知",
    }

    @classmethod
    def from_payload(cls, payload: dict[str, object] | None) -> "SRLPhaseHint | None":
        if not isinstance(payload, dict) or not payload:
            return None
        nested = payload.get("value")
        if isinstance(nested, dict) and nested:
            payload = nested

        raw_phase = str(payload.get("current_phase") or "").strip().upper()
        normalized_phase = cls.PHASE_ALIASES.get(raw_phase, "unknown")
        if normalized_phase == "unknown":
            return None

        try:
            confidence = round(float(payload.get("confidence") or 0.0), 4)
        except Exception:
            confidence = 0.0

        freshness_seconds = payload.get("freshness_seconds")
        if freshness_seconds is not None:
            try:
                freshness_seconds = int(freshness_seconds)
            except Exception:
                freshness_seconds = None

        phase_started_at = payload.get("phase_started_at")
        return cls(
            current_phase=normalized_phase,
            confidence=confidence,
            source=str(payload.get("source") or "").strip() or None,
            phase_started_at=str(phase_started_at).strip() or None if phase_started_at else None,
            freshness_seconds=freshness_seconds,
        )

    @property
    def phase_label(self) -> str:
        return self.PHASE_LABELS.get(self.current_phase, "未知")

    def to_payload(self) -> dict[str, object]:
        return {
            "current_phase": self.current_phase,
            "phase_label": self.phase_label,
            "confidence": self.confidence,
            "source": self.source,
            "phase_started_at": self.phase_started_at,
            "freshness_seconds": self.freshness_seconds,
        }

    def to_summary_lines(self) -> tuple[str, ...]:
        phase_guidance = {
            "forethought": "当前更适合先收紧目标、约束和启动标准，再展开具体方案。",
            "performance": "当前更适合维持执行节奏，给出能立刻开始的下一步，不把用户拉回大范围重规划。",
            "reflection": "当前更适合先复盘哪里有效、哪里失灵，再决定下一轮要怎么改。",
        }
        lines = [f"当前阶段：{self.phase_label}（{self.current_phase}）"]
        guidance = phase_guidance.get(self.current_phase)
        if guidance:
            lines.append(guidance)
        if self.confidence > 0:
            lines.append(f"阶段置信度：{self.confidence:.0%}")
        if self.freshness_seconds is not None:
            lines.append(f"新鲜度：{int(self.freshness_seconds)} 秒内")
        return tuple(lines)


class SRLTransitionRule(BaseModel):
    to_phase: SRLPhase
    allowed: bool = True
    description: str


INACTIVE_TIMEOUT_HOURS = 24
SRL_EVENT_TYPES: tuple[str, ...] = (
    "task.started",
    "plan.created",
    "task.feedback_submitted",
    "task.completed",
    "task.abandoned",
    "reflection.completed",
    "plan_stall_detected",
    "next_plan_draft",
    "user_start_new",
    "inactive_timeout",
)


SRL_TRANSITION_MATRIX: dict[SRLPhase, dict[str, SRLTransitionRule]] = {
    SRLPhase.FORETHOUGHT: {
        "task.started": SRLTransitionRule(
            to_phase=SRLPhase.PERFORMANCE,
            description="User starts executing a task.",
        ),
        "plan.created": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="Planning continues or is refined in-place.",
        ),
        "task.feedback_submitted": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            allowed=False,
            description="Direct forethought to reflection is rejected to avoid skip-level jumps.",
        ),
        "task.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            allowed=False,
            description="Completion without an execution phase is invalid.",
        ),
        "task.abandoned": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            allowed=False,
            description="Abandonment without an execution phase is invalid.",
        ),
        "reflection.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            allowed=False,
            description="Reflection cannot complete before execution begins.",
        ),
        "plan_stall_detected": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            allowed=False,
            description="Stall requires an active performance phase.",
        ),
        "next_plan_draft": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="A fresh plan draft keeps the learner in planning.",
        ),
        "user_start_new": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="A new attempt starts in planning.",
        ),
        "inactive_timeout": SRLTransitionRule(
            to_phase=SRLPhase.UNKNOWN,
            description="Long inactivity expires the known SRL phase.",
        ),
    },
    SRLPhase.PERFORMANCE: {
        "task.started": SRLTransitionRule(
            to_phase=SRLPhase.PERFORMANCE,
            description="A different task can keep the learner in execution.",
        ),
        "plan.created": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="Execution-time replanning returns to forethought.",
        ),
        "task.feedback_submitted": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Performance feedback starts reflection.",
        ),
        "task.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Task completion ends execution and starts reflection.",
        ),
        "task.abandoned": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Task abandonment ends execution and starts reflection.",
        ),
        "reflection.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Execution can jump into completed reflection when the reflection artifact lands.",
        ),
        "plan_stall_detected": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Repeated stalls push execution into reflection.",
        ),
        "next_plan_draft": SRLTransitionRule(
            to_phase=SRLPhase.PERFORMANCE,
            allowed=False,
            description="Execution must explicitly re-enter planning through plan.created.",
        ),
        "user_start_new": SRLTransitionRule(
            to_phase=SRLPhase.PERFORMANCE,
            allowed=False,
            description="Execution restart without replanning is rejected.",
        ),
        "inactive_timeout": SRLTransitionRule(
            to_phase=SRLPhase.UNKNOWN,
            description="Long inactivity expires the known SRL phase.",
        ),
    },
    SRLPhase.SELF_REFLECTION: {
        "task.started": SRLTransitionRule(
            to_phase=SRLPhase.PERFORMANCE,
            allowed=False,
            description="Reflection must re-enter forethought before execution.",
        ),
        "plan.created": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="A new or revised plan ends reflection and starts forethought.",
        ),
        "task.feedback_submitted": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="More feedback can deepen the current reflection loop.",
        ),
        "task.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Late completion evidence keeps reflection active.",
        ),
        "task.abandoned": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Abandonment evidence can keep reflection active.",
        ),
        "reflection.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Reflection can continue as a bounded self-loop.",
        ),
        "plan_stall_detected": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Further stall evidence keeps reflection active.",
        ),
        "next_plan_draft": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="A concrete next plan draft returns to forethought.",
        ),
        "user_start_new": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="Explicit restart returns to forethought.",
        ),
        "inactive_timeout": SRLTransitionRule(
            to_phase=SRLPhase.UNKNOWN,
            description="Long inactivity expires the known SRL phase.",
        ),
    },
    SRLPhase.UNKNOWN: {
        "task.started": SRLTransitionRule(
            to_phase=SRLPhase.PERFORMANCE,
            description="A concrete task start is sufficient to infer execution.",
        ),
        "plan.created": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="A concrete plan creation is sufficient to infer forethought.",
        ),
        "task.feedback_submitted": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Feedback without a known prior phase is treated as reflection.",
        ),
        "task.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Completion without prior state is treated as reflection.",
        ),
        "task.abandoned": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Abandonment without prior state is treated as reflection.",
        ),
        "reflection.completed": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="Completed reflection is directly inferable.",
        ),
        "plan_stall_detected": SRLTransitionRule(
            to_phase=SRLPhase.SELF_REFLECTION,
            description="A stall without prior state is treated as reflection.",
        ),
        "next_plan_draft": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="A next-plan draft restores forethought from unknown.",
        ),
        "user_start_new": SRLTransitionRule(
            to_phase=SRLPhase.FORETHOUGHT,
            description="Explicit restart restores forethought from unknown.",
        ),
        "inactive_timeout": SRLTransitionRule(
            to_phase=SRLPhase.UNKNOWN,
            description="Unknown can remain unknown during inactivity.",
        ),
    },
}


def get_transition_rule(current_phase: SRLPhase, trigger_event_type: str) -> SRLTransitionRule | None:
    normalized_trigger = str(trigger_event_type or "").strip()
    if not normalized_trigger:
        return None
    return SRL_TRANSITION_MATRIX.get(current_phase, {}).get(normalized_trigger)
