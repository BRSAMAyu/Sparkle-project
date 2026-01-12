from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


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
    schema_version: Optional[str] = None
    user_deleted: bool = False


class InterventionReason(BaseModel):
    trigger_event_id: Optional[str] = None
    explanation_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    decision_trace: List[str] = Field(default_factory=list)


class CoolDownPolicy(BaseModel):
    policy: str
    until_ms: Optional[int] = None


class InterventionDecisionContext(BaseModel):
    interruptibility: Optional[float] = Field(None, ge=0.0, le=1.0)
    focus_mode: Optional[bool] = None
    sprint_mode: Optional[bool] = None
    risk_level: Optional[str] = None


class InterventionRequestCreate(BaseModel):
    user_id: Optional[UUID] = None
    dedupe_key: Optional[str] = None
    topic: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_retractable: bool = True
    supersedes_id: Optional[UUID] = None
    schema_version: str = "intervention.v1"
    policy_version: Optional[str] = None
    model_version: Optional[str] = None
    reason: InterventionReason
    level: InterventionLevel
    cooldown_policy: Optional[CoolDownPolicy] = None
    content: Optional[Dict[str, Any]] = None
    context: Optional[InterventionDecisionContext] = None


class InterventionRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    dedupe_key: Optional[str] = None
    topic: Optional[str] = None
    requested_level: InterventionLevel
    final_level: InterventionLevel
    status: InterventionStatus
    reason: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    cooldown_policy: Optional[Dict[str, Any]] = None
    schema_version: str
    policy_version: Optional[str] = None
    model_version: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_retractable: bool
    supersedes_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionSettingsUpdate(BaseModel):
    interrupt_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    daily_interrupt_budget: Optional[int] = Field(None, ge=0, le=100)
    cooldown_minutes: Optional[int] = Field(None, ge=0, le=1440)
    quiet_hours: Optional[Dict[str, Any]] = None
    topic_allowlist: Optional[List[str]] = None
    topic_blocklist: Optional[List[str]] = None
    do_not_disturb: Optional[bool] = None


class InterventionSettingsResponse(BaseModel):
    user_id: UUID
    interrupt_threshold: float
    daily_interrupt_budget: int
    cooldown_minutes: int
    quiet_hours: Optional[Dict[str, Any]] = None
    topic_allowlist: Optional[List[str]] = None
    topic_blocklist: Optional[List[str]] = None
    do_not_disturb: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionFeedbackRequest(BaseModel):
    feedback_type: InterventionFeedbackType
    extra_data: Optional[Dict[str, Any]] = None


class InterventionFeedbackResponse(BaseModel):
    id: UUID
    request_id: UUID
    user_id: UUID
    feedback_type: InterventionFeedbackType
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionAuditResponse(BaseModel):
    id: UUID
    request_id: UUID
    user_id: UUID
    action: str
    guardrail_result: Optional[Dict[str, Any]] = None
    decision_trace: Optional[Dict[str, Any]] = None
    evidence_refs: Optional[Dict[str, Any]] = None
    requested_level: InterventionLevel
    final_level: InterventionLevel
    policy_version: Optional[str] = None
    model_version: Optional[str] = None
    schema_version: Optional[str] = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)
