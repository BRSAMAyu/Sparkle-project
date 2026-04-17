"""
Error Record Schemas
"""
from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorRecordCreate(BaseModel):
    """创建错题记录"""
    # 🆕 v2.1: 改为标准学科 ID
    subject_id: int = Field(description="Standard Subject ID")
    topic: str = Field(min_length=1, description="Topic/Knowledge point")
    error_type: str = Field(description="Type of error")
    description: str = Field(description="Description of the error")
    ai_analysis: str | None = Field(None, description="AI Analysis")
    image_urls: list[str] | None = Field(default=[], description="Image URLs")

    # 兼容字段 (可选)
    # subject_name: Optional[str] = None

class ErrorRecordResponse(BaseModel):
    id: UUID
    user_id: UUID
    subject_id: int | None
    subject: str
    topic: str
    error_type: str
    description: str
    ai_analysis: str | None
    image_urls: list[str] | None
    frequency: int
    is_resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
