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
    task_id: Optional[UUID] = Field(None, description="关联任务ID")

class CognitiveFragmentResponse(BaseModel):
    """碎片响应"""
    id: UUID
    user_id: UUID
    task_id: Optional[UUID]
    source_type: str
    content: str
    sentiment: Optional[str]
    tags: Optional[List[str]]
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
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
