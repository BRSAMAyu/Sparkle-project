from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.intervention import EvidenceRef


class AnalysisTaskInput(BaseModel):
    task_id: str
    task_type: str
    user_id: UUID
    source_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    requested_tier: Optional[str] = None


class AnalysisResult(BaseModel):
    task_id: str
    task_type: str
    model_used: Optional[str] = None
    confidence: float = 0.0
    primary_output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    latency_ms: Optional[int] = None
    cost_micro_usd: Optional[int] = None
    status: str = "ok"
