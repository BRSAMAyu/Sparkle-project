"""
Cognitive Prism Schemas
认知棱镜相关 Schema
"""
from typing import List, Optional, Dict
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from app.models.cognitive import AnalysisStatus

# ========== Request Schemas ========== 

class CognitiveFragmentCreate(BaseModel):
    id: Optional[UUID] = None # Front-end can provide UUID to avoid duplicates
    content: str = Field(..., min_length=1)
    source_type: str = Field(..., description="capsule, interceptor, behavior")
    
    # Optional metadata
    resource_type: str = "text"
    resource_url: Optional[str] = None
    context_tags: Optional[Dict] = None
    error_tags: Optional[List[str]] = None
    severity: int = Field(1, ge=1, le=5)
    task_id: Optional[UUID] = None

# ========== Response Schemas ========== 

class CognitiveFragmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    content: str
    source_type: str
    resource_type: str
    resource_url: Optional[str]
    context_tags: Optional[Dict]
    error_tags: Optional[List[str]]
    severity: int
    sentiment: Optional[str]
    analysis_status: AnalysisStatus
    error_message: Optional[str]
    task_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================================
# Behavior Pattern Schemas
# ==========================================

class BehaviorPatternResponse(BaseModel):
    """行为定式响应"""
    id: UUID
    user_id: UUID
    pattern_name: str
    pattern_type: str
    description: Optional[str]
    solution_text: Optional[str]
    evidence_ids: Optional[List[UUID]]
    confidence_score: float
    frequency: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
