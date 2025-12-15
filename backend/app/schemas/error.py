"""
Error Record Schemas
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ErrorRecordCreate(BaseModel):
    """创建错题记录"""
    # 🆕 v2.1: 改为标准学科 ID
    subject_id: int = Field(description="Standard Subject ID")
    topic: str = Field(min_length=1, description="Topic/Knowledge point")
    error_type: str = Field(description="Type of error")
    description: str = Field(description="Description of the error")
    ai_analysis: Optional[str] = Field(None, description="AI Analysis")
    image_urls: Optional[List[str]] = Field(default=[], description="Image URLs")
    
    # 兼容字段 (可选)
    # subject_name: Optional[str] = None 

class ErrorRecordResponse(BaseModel):
    id: UUID
    user_id: UUID
    subject_id: Optional[int]
    subject: str
    topic: str
    error_type: str
    description: str
    ai_analysis: Optional[str]
    image_urls: Optional[List[str]]
    frequency: int
    is_resolved: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
