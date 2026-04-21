from __future__ import annotations

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
