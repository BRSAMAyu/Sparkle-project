from __future__ import annotations
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.intervention import EvidenceRef


class AnalysisTaskInput(BaseModel):
    task_id: str
    task_type: str
    user_id: UUID
    source_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    requested_tier: str | None = None


class AnalysisResult(BaseModel):
    task_id: str
    task_type: str
    model_used: str | None = None
    confidence: float = 0.0
    primary_output: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    latency_ms: int | None = None
    cost_micro_usd: int | None = None
    status: str = "ok"
