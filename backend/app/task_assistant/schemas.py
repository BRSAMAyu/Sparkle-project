"""Stage 4 sidecar schemas for task assistant dormant mode."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskAssistantDormantInjection(BaseModel):
    """One-shot context injected into a dormant task-assistant session."""

    focus_summary: str = ""
    guidance_content: str | None = None
    guidance_source: str = "human_fallback"
    latest_ux_intent: str = "routine"
    latest_aurora_presence: str = "ambient"
    active_claims: list[str] = Field(default_factory=list)
    recent_probe_outcomes: list[str] = Field(default_factory=list)


class TaskAssistantOutcome(BaseModel):
    """Outcome summary captured for nearline next-turn optimization."""

    turn_index: int = 0
    latest_user_message: str = ""
    latest_assistant_message: str = ""
    strong_signal: str | None = None
    refresh_reason: str | None = None
    used_cold_start_fallback: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskAssistantContextPayload(BaseModel):
    """Dormant-mode sidecar context carried through task-chat requests."""

    session_mode: str = "dormant_candidate_v1"
    cold_start: bool = False
    refresh_reason: str | None = None
    strong_signal: str | None = None
    injection: TaskAssistantDormantInjection = Field(default_factory=TaskAssistantDormantInjection)
    outcome: TaskAssistantOutcome | None = None

