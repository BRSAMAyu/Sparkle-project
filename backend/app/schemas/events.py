from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.intervention import EvidenceRef


class EventIngestItem(BaseModel):
    event_id: str | None = None
    event_type: str = Field(..., min_length=1, max_length=120)
    schema_version: str = Field(..., min_length=1, max_length=50)
    source: str = Field(..., min_length=1, max_length=50)
    ts_ms: int | None = None
    entities: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    user_id: UUID | None = None


class EventIngestRequest(BaseModel):
    events: list[EventIngestItem] = Field(..., min_length=1, max_length=200)


class EventIngestResult(BaseModel):
    event_id: str
    status: str
    message: str | None = None


class EventIngestResponse(BaseModel):
    accepted: int
    deduped: int
    failed: int
    results: list[EventIngestResult]


class EventDetailResponse(BaseModel):
    event_id: str
    user_id: UUID
    event_type: str
    schema_version: str
    source: str
    ts_ms: int
    entities: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    deleted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceResolveRequest(BaseModel):
    items: list[EvidenceRef]


class UserStateSummary(BaseModel):
    user_id: UUID
    snapshot_at: datetime
    window_start: datetime
    window_end: datetime
    cognitive_load: float
    interruptibility: float
    strain_index: float
    focus_mode: bool
    sprint_mode: bool
    time_context: dict[str, Any] | None = None
    derived_event_ids: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceResolveItem(BaseModel):
    type: str
    id: str
    status: str
    event: EventDetailResponse | None = None
    chat_turn: dict[str, Any] | None = None
    state: UserStateSummary | None = None
    error: dict[str, Any] | None = None
    practice_outcome: dict[str, Any] | None = None
    concept: dict[str, Any] | None = None
    strategy: dict[str, Any] | None = None
    task: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    redaction_reason: str | None = None


class EvidenceResolveResponse(BaseModel):
    resolved: list[EvidenceResolveItem]


class EventDeleteResponse(BaseModel):
    event_id: str
    status: str
