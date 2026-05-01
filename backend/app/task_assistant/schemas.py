"""WS-D schemas: dormant injection set, outcome capture, sidecar store keys."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Injection items — the approved 5-item initial set
# ---------------------------------------------------------------------------

class DormantInjectionKind(StrEnum):
    """The five approved injection inputs for dormant-mode task assistant."""

    FOCUS_CONTRACT_SUMMARY = "focus_contract_summary"
    TASK_GUIDANCE_AI_OR_FALLBACK = "task_guidance_ai_or_fallback"
    LATEST_TDR_INTENT_PRESENCE = "latest_tdr_intent_presence"
    PROJECTION_ALLOWED_INSIGHT_CLAIM = "projection_allowed_insight_claim"
    RECENT_PROBE_OUTCOME = "recent_probe_outcome"


class DormantInjectionItem(BaseModel):
    """Single item in the dormant injection set."""

    model_config = ConfigDict(frozen=True)

    kind: DormantInjectionKind
    available: bool = Field(description="False means cold-start fallback applies")
    payload: dict | None = Field(
        default=None,
        description="Structured injection data; None when not yet available",
    )
    source_ref: str | None = Field(
        default=None,
        description="E.g. 'FocusContract:<uuid>' for traceability",
    )


class DormantInjection(BaseModel):
    """Full dormant injection set assembled for a task-assistant session start."""

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    user_id: UUID
    items: list[DormantInjectionItem]
    ux_intent: str = "routine"
    aurora_presence: str = "ambient"
    generated_by: str = "dormant_injector_v1"
    created_at: datetime


# ---------------------------------------------------------------------------
# Outcome capture — fed back to nearline for next-turn optimization
# ---------------------------------------------------------------------------

class AssistantOutcome(BaseModel):
    """Outcome record for a dormant-mode assistant turn, stored for nearline."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    task_id: UUID
    user_id: UUID
    conversation_id: UUID | None = None
    turn_number: int
    injection_was_used: bool = Field(
        default=False,
        description="True if the assistant response clearly leveraged injected context",
    )
    user_engaged: bool | None = Field(
        default=None,
        description="True if user continued, False if abandoned, None if unknown",
    )
    latency_ms: float | None = None
    created_at: datetime
