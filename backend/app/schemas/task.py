"""Task Schemas - Task creation, update, query, etc."""
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.models.task import SubTaskStatus, TaskStatus, TaskType
from app.schemas.common import BaseSchema

# ========== Request Schemas ==========

class TaskCreate(BaseModel):
    """Create task"""
    title: str = Field(min_length=1, max_length=255, description="Task title")
    type: TaskType = Field(validation_alias=AliasChoices("type", "task_type"), description="Task type")
    plan_id: UUID | None = Field(default=None, description="Related plan ID")
    tags: list[str] = Field(default_factory=list, description="Tags list")
    estimated_minutes: int | None = Field(default=None, ge=1, description="Estimated minutes")
    difficulty: int | None = Field(default=None, ge=1, le=5, description="Difficulty level")
    energy_cost: int = Field(default=1, ge=1, le=5, description="Energy cost")
    guide_content: str | None = Field(default=None, description="Guide content")
    priority: int = Field(default=0, description="Priority")
    due_date: date | None = Field(default=None, description="Due date")
    knowledge_node_id: UUID | None = Field(default=None, description="Knowledge node ID")
    tool_result_id: str | None = Field(default=None, description="Tool result ID from AI generator")

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_task_type(cls, value):
        if isinstance(value, TaskType):
            return value
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return value
            lowered = normalized.lower()
            alias_map = {
                "learning": "LEARNING",
                "training": "TRAINING",
                "errorfix": "ERROR_FIX",
                "error_fix": "ERROR_FIX",
                "reflection": "REFLECTION",
                "social": "SOCIAL",
                "planning": "PLANNING",
                "study": "LEARNING",
                "review": "TRAINING",
                "homework": "PLANNING",
                "exam": "REFLECTION",
                "other": "LEARNING",
            }
            mapped = alias_map.get(lowered, normalized.upper())
            try:
                return TaskType(mapped)
            except Exception:
                return value
        return value

    @field_validator("due_date", mode="before")
    @classmethod
    def _normalize_due_date(cls, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            try:
                if normalized.endswith("Z"):
                    normalized = normalized[:-1] + "+00:00"
                parsed = datetime.fromisoformat(normalized)
                return parsed.date()
            except ValueError:
                try:
                    return date.fromisoformat(normalized)
                except ValueError:
                    return value
        return value

class TaskUpdate(BaseModel):
    """Update task"""
    title: str | None = Field(default=None, min_length=1, max_length=255, description="Task title")
    tags: list[str] | None = Field(default=None, description="Tags list")
    estimated_minutes: int | None = Field(default=None, ge=1, description="Estimated minutes")
    difficulty: int | None = Field(default=None, ge=1, le=5, description="Difficulty level")
    energy_cost: int | None = Field(default=None, ge=1, le=5, description="Energy cost")
    guide_content: str | None = Field(default=None, description="Guide content")
    priority: int | None = Field(default=None, description="Priority")
    due_date: date | None = Field(default=None, description="Due date")
    user_note: str | None = Field(default=None, description="User note")

class TaskStart(BaseModel):
    """Start task"""
    task_id: UUID = Field(description="Task ID")

class TaskComplete(BaseModel):
    """Complete task (Legacy/Internal)"""
    task_id: UUID = Field(description="Task ID")
    actual_minutes: int = Field(ge=1, description="Actual minutes")
    user_note: str | None = Field(default=None, description="Completion note")

class TaskCompleteRequest(BaseModel):
    """Complete task request body (v2.1)"""
    actual_minutes: int = Field(ge=1, description="Actual minutes")
    note: str | None = Field(default=None, description="User note")
    completion_quality: int | None = Field(default=None, ge=1, le=5, description="Self rating 1-5")

class TaskAbandon(BaseModel):
    """Abandon task"""
    task_id: UUID = Field(description="Task ID")
    reason: str | None = Field(default=None, description="Abandon reason")

# ========== Response Schemas ==========

class TaskBase(BaseSchema):
    """Task basic information"""
    title: str = Field(description="Task title")
    type: TaskType = Field(description="Task type")
    status: TaskStatus = Field(description="Task status")
    tags: list[str] = Field(description="Tags list")
    estimated_minutes: int = Field(description="Estimated minutes")
    difficulty: int = Field(description="Difficulty level")
    energy_cost: int = Field(description="Energy cost")
    priority: int = Field(description="Priority")
    due_date: date | None = Field(description="Due date")

class TaskDetail(TaskBase):
    """Task detailed information"""
    user_id: UUID = Field(description="User ID")
    plan_id: UUID | None = Field(description="Related plan ID")
    guide_content: str | None = Field(description="Guide content")
    started_at: datetime | None = Field(description="Started time")
    confirmed_at: datetime | None = Field(description="Confirmed time")
    completed_at: datetime | None = Field(description="Completed time")
    actual_minutes: int | None = Field(description="Actual minutes")
    user_note: str | None = Field(description="User note")
    knowledge_node_id: UUID | None = Field(description="Knowledge node ID")
    tool_result_id: str | None = Field(description="Tool result ID")

class TaskSummary(BaseModel):
    """Task summary statistics"""
    total: int = Field(description="Total tasks")
    pending: int = Field(description="Pending tasks")
    in_progress: int = Field(description="In progress tasks")
    completed: int = Field(description="Completed tasks")
    abandoned: int = Field(description="Abandoned tasks")

class TaskRecommendationResponse(BaseModel):
    """Task recommendation response"""
    knowledge_node_id: UUID = Field(description="Knowledge node ID")
    title: str = Field(description="Task title")
    estimated_minutes: int = Field(description="Estimated minutes")
    task_type: str = Field(description="Task type")
    difficulty: int = Field(description="Difficulty level")
    priority: float = Field(description="Priority score")
    reason: str = Field(description="Recommendation reason")

class TaskListQuery(BaseModel):
    """Task list query parameters"""
    status: TaskStatus | None = Field(default=None, description="Task status")
    type: TaskType | None = Field(default=None, description="Task type")
    plan_id: UUID | None = Field(default=None, description="Plan ID")
    tags: list[str] | None = Field(default=None, description="Tags filter")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_query_task_type(cls, value):
        if value is None:
            return value
        if isinstance(value, TaskType):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            alias_map = {
                "learning": "LEARNING",
                "training": "TRAINING",
                "errorfix": "ERROR_FIX",
                "error_fix": "ERROR_FIX",
                "reflection": "REFLECTION",
                "social": "SOCIAL",
                "planning": "PLANNING",
                "study": "LEARNING",
                "review": "TRAINING",
                "homework": "PLANNING",
                "exam": "REFLECTION",
                "other": "LEARNING",
            }
            mapped = alias_map.get(lowered, value.upper())
            try:
                return TaskType(mapped)
            except Exception:
                return value
        return value

# ========== Suggestion Schemas ==========

class SuggestedNode(BaseModel):
    """Suggested knowledge node"""
    id: UUID | None = Field(default=None, description="Node ID (if existing)")
    name: str = Field(description="Node name")
    reason: str = Field(description="Reason for suggestion")
    is_new: bool = Field(default=False, description="Whether this is a potential new node")

class TaskSuggestionRequest(BaseModel):
    """Request for task suggestions"""
    input_text: str = Field(min_length=1, description="User input title or description")

class TaskSuggestionResponse(BaseModel):
    """Response for task suggestions"""
    intent: str = Field(description="Recognized user intent")
    suggested_nodes: list[SuggestedNode] = Field(default_factory=list, description="Suggested knowledge nodes")
    suggested_tags: list[str] = Field(default_factory=list, description="Suggested tags")
    estimated_minutes: int | None = Field(default=None, description="Suggested duration")
    difficulty: int | None = Field(default=None, description="Suggested difficulty")

# ========== Next Step Recommendation Schemas ==========

class NextActionType(str, Enum):
    """下一步行动类型"""
    QUICK_REVIEW = "quick_review"
    LIGHT_EXPAND = "light_expand"
    PRACTICE_APPLY = "practice_apply"
    REST_BREAK = "rest_break"
    CONTINUE_PLAN = "continue_plan"


class NextActionSuggestion(BaseModel):
    """Next action suggestion after task completion"""
    type: NextActionType = Field(description="Action type")
    title: str = Field(description="Action title")
    description: str = Field(description="Action description")
    estimated_minutes: int = Field(le=15, description="Estimated minutes (micro-task)")
    energy_cost: int = Field(le=2, description="Energy cost (low)")
    difficulty: int = Field(description="Difficulty level")
    reason: str = Field(description="Reason for recommendation")
    quick_create_params: dict | None = Field(default=None, description="Params to quick create task")
    existing_task_id: UUID | None = Field(default=None, description="ID if linking to existing task")
    can_quick_create: bool = Field(default=True, description="Whether can be quick created")


# ========== Subtask Schemas ==========

class SubTaskCreate(BaseModel):
    """Create subtask"""
    title: str = Field(min_length=1, max_length=255, description="Subtask title")
    description: str | None = Field(default=None, description="Subtask description")
    order: int | None = Field(default=0, description="Display order")

class SubTaskUpdate(BaseModel):
    """Update subtask"""
    title: str | None = Field(default=None, min_length=1, max_length=255, description="Subtask title")
    description: str | None = Field(default=None, description="Subtask description")
    status: SubTaskStatus | None = Field(default=None, description="Subtask status")
    order: int | None = Field(default=None, description="Display order")

class SubTaskDetail(BaseSchema):
    """Subtask detailed information"""
    parent_task_id: UUID = Field(description="Parent task ID")
    title: str = Field(description="Subtask title")
    description: str | None = Field(default=None, description="Subtask description")
    order: int = Field(description="Display order")
    status: SubTaskStatus = Field(description="Subtask status")
    completed_at: datetime | None = Field(default=None, description="Completion time")

class SubTaskReorderRequest(BaseModel):
    """Reorder subtasks"""
    subtask_orders: list[dict] = Field(
        description="List of {subtask_id, order} pairs",
        examples=[[{"subtask_id": "uuid", "order": 0}, {"subtask_id": "uuid", "order": 1}]]
    )
