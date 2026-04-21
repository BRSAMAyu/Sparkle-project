from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SceneRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scene_id: str = Field(..., min_length=8, max_length=80)
    user_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=200)
    member_memory_ids: list[str] = Field(default_factory=list)
    time_start: datetime
    time_end: datetime
    quality_score: float = Field(..., ge=0.0, le=1.0)
    version: str = Field(..., min_length=1, max_length=32)
    created_at: datetime
    updated_at: datetime


class SceneSummary(BaseModel):
    scene_id: str
    title: str
    time_start: datetime
    time_end: datetime
    member_count: int = Field(..., ge=0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
