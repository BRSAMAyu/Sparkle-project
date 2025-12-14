"""Plan Schemas - Plan creation, update, query, etc."""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date

from app.schemas.common import BaseSchema
from app.models.plan import PlanType

# ========== Request Schemas ==========

class PlanCreate(BaseModel):
    """Create plan"""
    name: str = Field(min_length=1, max_length=255, description="Plan name")
    type: PlanType = Field(description="Plan type")
    description: Optional[str] = Field(default=None, description="Plan description")
    subject: Optional[str] = Field(default=None, max_length=100, description="Subject/Course")
    target_date: Optional[date] = Field(default=None, description="Target date (for sprint plans)")
    daily_available_minutes: int = Field(default=60, ge=1, description="Daily available minutes")
    total_estimated_hours: Optional[float] = Field(default=None, ge=0, description="Total estimated hours")

class PlanUpdate(BaseModel):
    """Update plan"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Plan name")
    description: Optional[str] = Field(default=None, description="Plan description")
    target_date: Optional[date] = Field(default=None, description="Target date")
    daily_available_minutes: Optional[int] = Field(default=None, ge=1, description="Daily available minutes")
    total_estimated_hours: Optional[float] = Field(default=None, ge=0, description="Total estimated hours")
    is_active: Optional[bool] = Field(default=None, description="Is active")

class PlanActivate(BaseModel):
    """Activate plan"""
    plan_id: UUID = Field(description="Plan ID")

class GenerateTasksRequest(BaseModel):
    """Generate tasks request"""
    plan_id: UUID = Field(description="Plan ID")
    ai_context: Optional[str] = Field(default=None, description="AI context for task generation")

# ========== Response Schemas ==========

class PlanBase(BaseSchema):
    """Plan basic information"""
    name: str = Field(description="Plan name")
    type: PlanType = Field(description="Plan type")
    subject: Optional[str] = Field(description="Subject/Course")
    target_date: Optional[date] = Field(description="Target date")
    progress: float = Field(description="Progress percentage")
    is_active: bool = Field(description="Is active")

class PlanDetail(PlanBase):
    """Plan detailed information"""
    user_id: UUID = Field(description="User ID")
    description: Optional[str] = Field(description="Plan description")
    daily_available_minutes: int = Field(description="Daily available minutes")
    total_estimated_hours: Optional[float] = Field(description="Total estimated hours")
    mastery_level: float = Field(description="Mastery level")
    task_count: int = Field(default=0, description="Total tasks")
    completed_task_count: int = Field(default=0, description="Completed tasks")

class PlanProgress(BaseModel):
    """Plan progress information"""
    plan_id: UUID = Field(description="Plan ID")
    progress: float = Field(description="Progress percentage")
    mastery_level: float = Field(description="Mastery level")
    total_tasks: int = Field(description="Total tasks")
    completed_tasks: int = Field(description="Completed tasks")
    total_minutes_spent: int = Field(description="Total minutes spent")
    estimated_remaining_hours: float = Field(description="Estimated remaining hours")

    class Config:
        from_attributes = True

class PlanSummary(BaseModel):
    """Plan summary statistics"""
    total: int = Field(description="Total plans")
    active: int = Field(description="Active plans")
    sprint_plans: int = Field(description="Sprint plans")
    growth_plans: int = Field(description="Growth plans")
