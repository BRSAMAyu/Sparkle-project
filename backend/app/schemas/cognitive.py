"""
Cognitive Prism Schemas
认知棱镜相关 Schema
"""
from __future__ import annotations
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.cognitive import AnalysisStatus, PatternType

# ========== Request Schemas ==========

class CognitiveFragmentCreate(BaseModel):
    id: UUID | None = None # Front-end can provide UUID to avoid duplicates
    content: str = Field(..., min_length=1)
    source_type: str = Field(..., description="capsule, interceptor, behavior")

    # Optional metadata
    resource_type: str = "text"
    resource_url: str | None = None
    context_tags: dict | None = None
    error_tags: list[str] | None = None
    severity: int = Field(1, ge=1, le=5)
    task_id: UUID | None = None
    source_event_id: str | None = None
    persona_version: str | None = None

# ========== Response Schemas ==========

class CognitiveFragmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    content: str
    source_type: str
    resource_type: str
    resource_url: str | None
    context_tags: dict | None
    error_tags: list[str] | None
    severity: int
    sentiment: str | None
    analysis_status: AnalysisStatus
    error_message: str | None
    task_id: UUID | None
    source_event_id: str | None
    persona_version: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Behavior Pattern Schemas
# ==========================================

class BehaviorPatternResponse(BaseModel):
    """行为定式响应"""
    id: UUID
    user_id: UUID
    pattern_name: str
    pattern_type: PatternType
    description: str | None
    solution_text: str | None
    evidence_ids: list[UUID] | None
    confidence_score: float
    frequency: int
    is_archived: bool
    last_observed_at: datetime | None
    last_decay_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("pattern_type", mode="before")
    @classmethod
    def _normalize_pattern_type(cls, value):
        if isinstance(value, PatternType):
            return value

        normalized = str(value or "").strip().lower()
        if not normalized:
            return PatternType.EXECUTION

        valid_values = {item.value for item in PatternType}
        if normalized in valid_values:
            return PatternType(normalized)

        for token in re.split(r"[^a-z]+", normalized):
            if token in valid_values:
                return PatternType(token)

        return PatternType.EXECUTION

    model_config = ConfigDict(from_attributes=True)
