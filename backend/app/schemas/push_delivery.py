from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PushActionRequest(BaseModel):
    action: str = Field(pattern="^(seen|dismissed|acted|disable_category|retract)$")
    action_payload: dict[str, Any] = Field(default_factory=dict)


class PushDecisionResponse(BaseModel):
    policy_id: str
    evidence_token: str
    message_template_id: str
    scheduled_send_at: datetime
    title: str
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)

