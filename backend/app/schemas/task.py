"""Task Schemas - Task creation, update, query, etc."""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, date

from app.schemas.common import BaseSchema
from app.models.task import TaskType, TaskStatus

# ========== Request Schemas ==========

class TaskCreate(BaseModel):
    """Create task"""
    title: str = Field(min_length=1, max_length=255, description="Task title")
    type: TaskType = Field(description="Task type")
    plan_id: Optional[UUID] = Field(default=None, description="Related plan ID")
    tags: List[str] = Field(default_factory=list, description="Tags list")
    estimated_minutes: int = Field(ge=1, description="Estimated minutes")
    difficulty: int = Field(default=1, ge=1, le=5, description="Difficulty level")
    energy_cost: int = Field(default=1, ge=1, le=5, description="Energy cost")
    guide_content: Optional[str] = Field(default=None, description="Guide content")
    priority: int = Field(default=0, description="Priority")
    due_date: Optional[date] = Field(default=None, description="Due date")
    knowledge_node_id: Optional[UUID] = Field(default=None, description="Knowledge node ID")
    tool_result_id: Optional[str] = Field(default=None, description="Tool result ID from AI generator")

class TaskUpdate(BaseModel):
    """Update task"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Task title")
    tags: Optional[List[str]] = Field(default=None, description="Tags list")
    estimated_minutes: Optional[int] = Field(default=None, ge=1, description="Estimated minutes")
    difficulty: Optional[int] = Field(default=None, ge=1, le=5, description="Difficulty level")
    energy_cost: Optional[int] = Field(default=None, ge=1, le=5, description="Energy cost")
    guide_content: Optional[str] = Field(default=None, description="Guide content")
    priority: Optional[int] = Field(default=None, description="Priority")
    due_date: Optional[date] = Field(default=None, description="Due date")
    user_note: Optional[str] = Field(default=None, description="User note")

class TaskStart(BaseModel):
    """Start task"""
    task_id: UUID = Field(description="Task ID")

class TaskComplete(BaseModel):
    """Complete task (Legacy/Internal)"""
    task_id: UUID = Field(description="Task ID")
    actual_minutes: int = Field(ge=1, description="Actual minutes")
    user_note: Optional[str] = Field(default=None, description="Completion note")

class TaskCompleteRequest(BaseModel):
    """Complete task request body (v2.1)"""
    actual_minutes: int = Field(ge=1, description="Actual minutes")
    note: Optional[str] = Field(default=None, description="User note")
    completion_quality: Optional[int] = Field(default=None, ge=1, le=5, description="Self rating 1-5")

class TaskAbandon(BaseModel):
    """Abandon task"""
    task_id: UUID = Field(description="Task ID")
    reason: Optional[str] = Field(default=None, description="Abandon reason")

# ========== Response Schemas ==========

class TaskBase(BaseSchema):
    """Task basic information"""
    title: str = Field(description="Task title")
    type: TaskType = Field(description="Task type")
    status: TaskStatus = Field(description="Task status")
    tags: List[str] = Field(description="Tags list")
    estimated_minutes: int = Field(description="Estimated minutes")
    difficulty: int = Field(description="Difficulty level")
    energy_cost: int = Field(description="Energy cost")
    priority: int = Field(description="Priority")
    due_date: Optional[date] = Field(description="Due date")

class TaskDetail(TaskBase):
    """Task detailed information"""
    user_id: UUID = Field(description="User ID")
    plan_id: Optional[UUID] = Field(description="Related plan ID")
    guide_content: Optional[str] = Field(description="Guide content")
    started_at: Optional[datetime] = Field(description="Started time")
    confirmed_at: Optional[datetime] = Field(description="Confirmed time")
    completed_at: Optional[datetime] = Field(description="Completed time")
    actual_minutes: Optional[int] = Field(description="Actual minutes")
    user_note: Optional[str] = Field(description="User note")
    knowledge_node_id: Optional[UUID] = Field(description="Knowledge node ID")
    tool_result_id: Optional[str] = Field(description="Tool result ID")

class TaskSummary(BaseModel):
    """Task summary statistics"""
    total: int = Field(description="Total tasks")
    pending: int = Field(description="Pending tasks")
    in_progress: int = Field(description="In progress tasks")
    completed: int = Field(description="Completed tasks")
    abandoned: int = Field(description="Abandoned tasks")

class TaskListQuery(BaseModel):
    """Task list query parameters"""
    status: Optional[TaskStatus] = Field(default=None, description="Task status")
    type: Optional[TaskType] = Field(default=None, description="Task type")
    plan_id: Optional[UUID] = Field(default=None, description="Plan ID")
    tags: Optional[List[str]] = Field(default=None, description="Tags filter")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")

# ========== Suggestion Schemas ==========

class SuggestedNode(BaseModel):
    """Suggested knowledge node"""
    id: Optional[UUID] = Field(default=None, description="Node ID (if existing)")
    name: str = Field(description="Node name")
    reason: str = Field(description="Reason for suggestion")
    is_new: bool = Field(default=False, description="Whether this is a potential new node")

class TaskSuggestionRequest(BaseModel):
    """Request for task suggestions"""
    input_text: str = Field(min_length=1, description="User input title or description")

class TaskSuggestionResponse(BaseModel):
    """Response for task suggestions"""
    intent: str = Field(description="Recognized user intent")
    suggested_nodes: List[SuggestedNode] = Field(default_factory=list, description="Suggested knowledge nodes")
    suggested_tags: List[str] = Field(default_factory=list, description="Suggested tags")
    estimated_minutes: Optional[int] = Field(default=None, description="Suggested duration")
    difficulty: Optional[int] = Field(default=None, description="Suggested difficulty")
