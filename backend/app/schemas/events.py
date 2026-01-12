from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.intervention import EvidenceRef


class EventIngestItem(BaseModel):
    event_id: Optional[str] = None
    event_type: str = Field(..., min_length=1, max_length=120)
    schema_version: str = Field(..., min_length=1, max_length=50)
    source: str = Field(..., min_length=1, max_length=50)
    ts_ms: Optional[int] = None
    entities: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    user_id: Optional[UUID] = None


class EventIngestRequest(BaseModel):
    events: List[EventIngestItem] = Field(..., min_length=1, max_length=200)


class EventIngestResult(BaseModel):
    event_id: str
    status: str
    message: Optional[str] = None


class EventIngestResponse(BaseModel):
    accepted: int
    deduped: int
    failed: int
    results: List[EventIngestResult]


class EventDetailResponse(BaseModel):
    event_id: str
    user_id: UUID
    event_type: str
    schema_version: str
    source: str
    ts_ms: int
    entities: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    deleted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceResolveRequest(BaseModel):
    items: List[EvidenceRef]


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
    time_context: Optional[Dict[str, Any]] = None
    derived_event_ids: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceResolveItem(BaseModel):
    type: str
    id: str
    status: str
    event: Optional[EventDetailResponse] = None
    state: Optional[UserStateSummary] = None
    error: Optional[Dict[str, Any]] = None
    concept: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None
    redaction_reason: Optional[str] = None


class EvidenceResolveResponse(BaseModel):
    resolved: List[EvidenceResolveItem]


class EventDeleteResponse(BaseModel):
    event_id: str
    status: str
