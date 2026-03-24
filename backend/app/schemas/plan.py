"""Plan Schemas - Plan creation, update, query, etc."""

from __future__ import annotations
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.plan import PlanPriority, PlanStage, PlanType
from app.schemas.common import BaseSchema
from app.schemas.task import TaskDetail

# ========== Request Schemas ==========


class PlanCreate(BaseModel):
    """Create plan"""

    name: str = Field(min_length=1, max_length=255, description="Plan name")
    type: PlanType = Field(description="Plan type")
    description: str | None = Field(default=None, description="Plan description")
    subject: str | None = Field(default=None, max_length=100, description="Subject/Course")
    target_date: date | None = Field(default=None, description="Target date (for sprint plans)")
    daily_available_minutes: int = Field(default=60, ge=1, description="Daily available minutes")
    total_estimated_hours: float | None = Field(default=None, ge=0, description="Total estimated hours")
    priority: PlanPriority | None = Field(default=PlanPriority.NORMAL, description="Plan priority")
    plan_stage: PlanStage | None = Field(default=None, description="Plan stage")


class PlanUpdate(BaseModel):
    """Update plan"""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Plan name")
    description: str | None = Field(default=None, description="Plan description")
    target_date: date | None = Field(default=None, description="Target date")
    daily_available_minutes: int | None = Field(default=None, ge=1, description="Daily available minutes")
    total_estimated_hours: float | None = Field(default=None, ge=0, description="Total estimated hours")
    is_active: bool | None = Field(default=None, description="Is active")
    priority: PlanPriority | None = Field(default=None, description="Plan priority")
    plan_stage: PlanStage | None = Field(default=None, description="Plan stage")


class PlanActivate(BaseModel):
    """Activate plan"""

    plan_id: UUID = Field(description="Plan ID")


class GenerateTasksRequest(BaseModel):
    """Generate tasks request"""

    plan_id: UUID = Field(description="Plan ID")
    ai_context: str | None = Field(default=None, description="AI context for task generation")


# ========== Response Schemas ==========


class PlanBase(BaseSchema):
    """Plan basic information"""

    name: str = Field(description="Plan name")
    type: PlanType = Field(description="Plan type")
    subject: str | None = Field(description="Subject/Course")
    target_date: date | None = Field(description="Target date")
    progress: float = Field(description="Progress percentage")
    is_active: bool = Field(description="Is active")
    priority: PlanPriority = Field(description="Plan priority")
    is_primary: bool = Field(description="Is primary plan")
    plan_stage: PlanStage = Field(description="Plan stage")


class PlanDetail(PlanBase):
    """Plan detailed information"""

    user_id: UUID = Field(description="User ID")
    description: str | None = Field(description="Plan description")
    daily_available_minutes: int = Field(description="Daily available minutes")
    total_estimated_hours: float | None = Field(description="Total estimated hours")
    mastery_level: float = Field(description="Mastery level")
    task_count: int = Field(default=0, description="Total tasks")
    completed_task_count: int = Field(default=0, description="Completed tasks")
    source: str | None = Field(default=None, description="Plan source (e.g., 'learning_path')")
    source_metadata: dict | None = Field(default=None, description="Source-specific metadata")
    tasks: list[TaskDetail] | None = Field(default=None, description="Related tasks for the plan")


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


# ========== Quota Related Schemas ==========


class PlanQuotaStatus(BaseModel):
    """Plan quota status"""

    used: int = Field(description="Number of active plans")
    limit: int = Field(description="Quota limit")
    remaining: int = Field(description="Remaining quota (-1 if unlimited)")
    is_unlimited: bool = Field(description="Is unlimited quota")
    primary_plan_id: UUID | None = Field(default=None, description="Current primary plan ID")

    class Config:
        from_attributes = True


class SetPrimaryPlanRequest(BaseModel):
    """Set primary plan request"""

    plan_id: UUID = Field(description="Plan ID to set as primary")


class PlanPriorityUpdate(BaseModel):
    """Update plan priority request"""

    priority: PlanPriority = Field(description="New priority")
