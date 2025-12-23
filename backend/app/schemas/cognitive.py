"""
Cognitive Prism Schemas
认知棱镜相关 Schema
"""
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

# ==========================================
# Cognitive Fragment Schemas
# ==========================================

class CognitiveFragmentCreate(BaseModel):
    """创建碎片请求"""
    content: str = Field(..., description="内容", min_length=1)
    source_type: str = Field(..., description="来源类型: capsule, interceptor, behavior")
    resource_type: str = Field("text", description="资源类型: text, audio, image")
    resource_url: Optional[str] = Field(None, description="资源URL")
    task_id: Optional[UUID] = Field(None, description="关联任务ID")
    context_tags: Optional[dict] = Field(None, description="情境标签")
    error_tags: Optional[List[str]] = Field(None, description="错误标签")
    severity: int = Field(1, ge=1, le=5, description="严重程度")

class CognitiveFragmentResponse(BaseModel):
    """碎片响应"""
    id: UUID
    user_id: UUID
    task_id: Optional[UUID]
    source_type: str
    resource_type: str
    resource_url: Optional[str]
    content: str
    sentiment: Optional[str]
    tags: Optional[List[str]]
    error_tags: Optional[List[str]]
    context_tags: Optional[dict]
    severity: int
    created_at: datetime
    updated_at: datetime

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
