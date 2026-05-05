from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DlqEntry(BaseModel):
    message_id: str
    payload: dict[str, Any]


class DlqReplayRequest(BaseModel):
    message_ids: list[str] = Field(..., min_length=1)
    approver_id: str
    reason_code: str
    delete_after: bool = True


class EventBusDlqEntry(BaseModel):
    message_id: str
    stream: str
    event_type: str
    user_id: UUID | None = None
    group_name: str
    consumer_name: str
    retry_count: int = 0
    failure_stage: str = "consume"
    error: str
    payload: dict[str, Any]
    failed_at: str | None = None


class EventBusDlqListResponse(BaseModel):
    entries: list[EventBusDlqEntry]
    total: int
    stream: str


class EventBusDlqReplayRequest(BaseModel):
    message_ids: list[str] = Field(..., min_length=1)
    approver_id: str
    reason_code: str
    delete_after: bool = True
