from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InterventionLevel(str, Enum):
    SILENT_MARKER = "SILENT_MARKER"
    TOAST = "TOAST"
    CARD = "CARD"
    FULL_SCREEN_MODAL = "FULL_SCREEN_MODAL"


class InterventionStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    RETRACTED = "retracted"


class InterventionFeedbackType(str, Enum):
    ACCEPT = "accept"
    SNOOZE = "snooze"
    REJECT = "reject"
    MUTE_TOPIC = "mute_topic"
    OPEN_DETAIL = "open_detail"
    IGNORE = "ignore"


class EvidenceRef(BaseModel):
    type: str
    id: str
    schema_version: str | None = None
    user_deleted: bool = False


class InterventionReason(BaseModel):
    trigger_event_id: str | None = None
    explanation_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    decision_trace: list[str] = Field(default_factory=list)


class CoolDownPolicy(BaseModel):
    policy: str
    until_ms: int | None = None


class InterventionDecisionContext(BaseModel):
    interruptibility: float | None = Field(None, ge=0.0, le=1.0)
    focus_mode: bool | None = None
    sprint_mode: bool | None = None
    risk_level: str | None = None


class InterventionRequestCreate(BaseModel):
    user_id: UUID | None = None
    dedupe_key: str | None = None
    topic: str | None = None
    expires_at: datetime | None = None
    is_retractable: bool = True
    supersedes_id: UUID | None = None
    schema_version: str = "intervention.v1"
    policy_version: str | None = None
    model_version: str | None = None
    reason: InterventionReason
    level: InterventionLevel
    cooldown_policy: CoolDownPolicy | None = None
    content: dict[str, Any] | None = None
    context: InterventionDecisionContext | None = None
    delivery_method: str | None = None
    template_id: str | None = None
    template_variant_id: str | None = None
    scaffolding_level: int | None = None
    intent_type: str | None = None


class InterventionRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    dedupe_key: str | None = None
    topic: str | None = None
    requested_level: InterventionLevel
    final_level: InterventionLevel
    status: InterventionStatus
    reason: dict[str, Any] | None = None
    content: dict[str, Any] | None = None
    cooldown_policy: dict[str, Any] | None = None
    delivery_method: str | None = None
    template_id: str | None = None
    template_variant_id: str | None = None
    scaffolding_level: int | None = None
    intent_type: str | None = None
    schema_version: str
    policy_version: str | None = None
    model_version: str | None = None
    expires_at: datetime | None = None
    is_retractable: bool
    supersedes_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionSettingsUpdate(BaseModel):
    interrupt_threshold: float | None = Field(None, ge=0.0, le=1.0)
    daily_interrupt_budget: int | None = Field(None, ge=0, le=100)
    cooldown_minutes: int | None = Field(None, ge=0, le=1440)
    quiet_hours: dict[str, Any] | None = None
    topic_allowlist: list[str] | None = None
    topic_blocklist: list[str] | None = None
    do_not_disturb: bool | None = None


class InterventionSettingsResponse(BaseModel):
    user_id: UUID
    interrupt_threshold: float
    daily_interrupt_budget: int
    cooldown_minutes: int
    quiet_hours: dict[str, Any] | None = None
    topic_allowlist: list[str] | None = None
    topic_blocklist: list[str] | None = None
    do_not_disturb: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionFeedbackRequest(BaseModel):
    feedback_type: InterventionFeedbackType
    extra_data: dict[str, Any] | None = None
    idempotency_key: str | None = None


class InterventionFeedbackResponse(BaseModel):
    id: UUID
    request_id: UUID
    user_id: UUID
    feedback_type: InterventionFeedbackType
    extra_data: dict[str, Any] | None = None
    idempotency_key: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionAuditResponse(BaseModel):
    id: UUID
    request_id: UUID
    user_id: UUID
    action: str
    guardrail_result: dict[str, Any] | None = None
    decision_trace: dict[str, Any] | None = None
    evidence_refs: dict[str, Any] | None = None
    requested_level: InterventionLevel
    final_level: InterventionLevel
    policy_version: str | None = None
    model_version: str | None = None
    schema_version: str | None = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EdgeStatePayload(BaseModel):
    focus_score: float | None = None
    switching_rate: float | None = None
    is_foreground: bool | None = None
    session_seconds: int | None = None
    stress_score: float | None = None
    fatigue_score: float | None = None
    interrupt_score: float | None = None
    attention_score: float | None = None
    debug: dict[str, Any] | None = None


class InterventionTriggerRequest(BaseModel):
    type: str
    urgency: float = Field(..., ge=0.0, le=1.0)
    context: dict[str, Any] = Field(default_factory=dict)
    edge_state: EdgeStatePayload | None = None
    gate_decision: dict[str, Any] | None = None


class PassiveSignalRequest(BaseModel):
    signal_type: str
    intervention_id: UUID | None = None
    context: dict[str, Any] | None = None
    timestamp: datetime | None = None


class BehavioralOutcomeRequest(BaseModel):
    intervention_id: UUID
    outcome_type: str
    time_to_outcome: int = Field(..., ge=0)
    success: bool
    context: dict[str, Any] | None = None
