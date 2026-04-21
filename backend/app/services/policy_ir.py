from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


POLICY_IR_VERSION = "v1"
POLICY_IR_SCHEMA_VERSION = "policy_ir.v1"
POLICY_IR_FROZEN_AT = "2026-04-21T00:00:00Z"


class PolicyTriggerType(str, Enum):
    TIME_BEFORE_DUE = "time_before_due"
    STREAK_BREAK = "streak_break"
    OVERDUE_BY = "overdue_by"
    PEER_MISSED = "peer_missed"
    SUCCESS_STREAK = "success_streak"


class PolicyActionType(str, Enum):
    NOTIFY_USER = "notify_user"
    NOTIFY_PARTNER = "notify_partner"
    DOWNGRADE_PRIORITY = "downgrade_priority"
    LOWER_DIFFICULTY = "lower_difficulty"


class PolicyTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: PolicyTriggerType
    params: dict[str, Any] = Field(default_factory=dict)


class PolicyAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: PolicyActionType
    params: dict[str, Any] = Field(default_factory=dict)


class PolicyConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_budget: int | None = None
    cooldown_hours: int | None = None
    partner_consent_required: bool = False


class PolicyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commitment_summary: str
    commitment_due_at: datetime | None = None
    commitment_created_at: datetime | None = None
    evidence_token: str | None = None
    partnership_id: UUID | None = None
    partner_id: UUID | None = None
    partner_consent_granted: bool = False
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    commitment_id: UUID
    user_id: UUID
    trigger: PolicyTrigger
    action: PolicyAction
    constraints: PolicyConstraints = Field(default_factory=PolicyConstraints)
    context: PolicyContext
    version: str = POLICY_IR_VERSION


class PendingPoliciesSummaryValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = 0
    next_trigger_at: datetime | None = None
    policy_ids: tuple[str, ...] = ()


def policy_ir_json_schema() -> dict[str, Any]:
    return PolicyRule.model_json_schema()
