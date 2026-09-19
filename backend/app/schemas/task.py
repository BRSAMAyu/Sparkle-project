"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Task Schemas - Task creation, update, query, etc.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum, StrEnum
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from app.core.action_plan import (
    ACTION_PLAN_SCHEMA_VERSION,
    ACTION_SOURCE_REF_SCHEMES,
    ActionPlanContract,
    CognitiveOwnership,
    CompletionEvidenceSpec,
    EvidenceKind,
    ExecutionMode,
    RiskClass,
    SmallestUsefulStep,
    UsefulStepReason,
    normalize_execution_mode,
)
from app.models.task import SubTaskStatus, TaskStatus, TaskType
from app.schemas.common import BaseSchema

# ========== Request Schemas ==========

# ── X-01 · ActionPlan V3 契约 DTO（结构化字段，非自然语言）──────────────────
# 语义真源：app/core/action_plan.py（封闭词表 + validate()）。DTO 在 parse 时完成
# 归一化与全量校验（API 边界 422），service 落列不再二次解释。


class SmallestUsefulStepIn(BaseModel):
    """最小有用步骤：描述 + 封闭判据（useful_because 非空，防「打开 IDE」式伪步骤）。"""

    description: str = Field(min_length=1, max_length=500, description="Step description")
    useful_because: list[UsefulStepReason] = Field(min_length=1, description="Why useful (closed vocabulary)")


class CompletionEvidenceIn(BaseModel):
    """单条完成证据规格：evidence_kind 必填（封闭枚举），ref 可选（封闭 scheme）。"""

    evidence_kind: EvidenceKind = Field(description="Evidence type (closed vocabulary)")
    ref: str | None = Field(default=None, max_length=255, description="Optional scheme://id reference")
    description: str | None = Field(default=None, max_length=500, description="Optional human note")

    @field_validator("ref")
    @classmethod
    def _ref_scheme_closed(cls, value: str | None) -> str | None:
        if value is None:
            return value
        scheme = value.split("://", 1)[0] if "://" in value else ""
        if scheme not in ACTION_SOURCE_REF_SCHEMES:
            raise ValueError(f"evidence ref scheme must be one of {sorted(ACTION_SOURCE_REF_SCHEMES)}")
        return value


class ActionPlanIn(BaseModel):
    """ActionPlan V3 写入块：三模式（human/agent/hybrid）在此结构化表达。"""

    desired_outcome: str = Field(min_length=1, max_length=1000, description="Desired outcome statement")
    smallest_useful_step: SmallestUsefulStepIn
    completion_evidence: list[CompletionEvidenceIn] = Field(min_length=1, description="Typed evidence specs")
    execution_mode: ExecutionMode = Field(description="human | agent | hybrid (ExecutionIntent vocabulary)")
    cognitive_ownership: CognitiveOwnership = Field(description="user_core | shared | delegated (D13)")
    source_refs: list[str] = Field(default_factory=list, description="scheme://id refs (closed schemes)")
    risk_class: RiskClass | None = Field(default=None, description="low | medium | high | critical")
    reversible: bool | None = Field(default=None, description="Reversibility of failure")

    @field_validator("execution_mode", mode="before")
    @classmethod
    def _normalize_execution_mode(cls, value):
        parsed = normalize_execution_mode(value)
        if parsed is None:
            raise ValueError("execution_mode must be one of human/agent/hybrid")
        return parsed

    @field_validator("source_refs")
    @classmethod
    def _source_refs_closed(cls, value: list[str]) -> list[str]:
        for ref in value:
            scheme = ref.split("://", 1)[0] if "://" in ref else ""
            if scheme not in ACTION_SOURCE_REF_SCHEMES:
                raise ValueError(f"source ref scheme must be one of {sorted(ACTION_SOURCE_REF_SCHEMES)}: {ref!r}")
        return value

    def to_contract(self) -> ActionPlanContract:
        """DTO → 契约（validate() 兜底跨字段规则；parse 时已过词表校验）。"""
        contract = ActionPlanContract(
            desired_outcome=self.desired_outcome,
            smallest_useful_step=SmallestUsefulStep(
                description=self.smallest_useful_step.description,
                useful_because=tuple(reason.value for reason in self.smallest_useful_step.useful_because),
            ),
            completion_evidence=tuple(
                CompletionEvidenceSpec(
                    evidence_kind=entry.evidence_kind.value,
                    ref=entry.ref,
                    description=entry.description,
                )
                for entry in self.completion_evidence
            ),
            execution_mode=self.execution_mode,
            cognitive_ownership=self.cognitive_ownership,
            source_refs=tuple(self.source_refs),
            risk_class=self.risk_class,
            reversible=self.reversible,
            schema_version=ACTION_PLAN_SCHEMA_VERSION,
        )
        violations = contract.validate()
        if violations:
            raise ValueError(f"invalid action_plan contract: {'; '.join(violations)}")
        return contract


class SmallestUsefulStepOut(BaseModel):
    description: str
    useful_because: list[UsefulStepReason]


class CompletionEvidenceOut(BaseModel):
    evidence_kind: EvidenceKind
    ref: str | None = None
    description: str | None = None


class ActionPlanOut(BaseModel):
    """ActionPlan V3 读回块（legacy 行 → TaskDetail.action_plan = None）。

    封闭枚举字段保持严格的前提：输入必须来自 Task.action_plan（统一门
    action_plan_projection 已过滤词表外/未来值/版本不符行，脏行降级为 None）。
    任何新读路径不得绕过该门直接把列值喂给本模型（X-01 返修 F1 教训）。
    """

    schema_version: str
    desired_outcome: str
    smallest_useful_step: SmallestUsefulStepOut
    completion_evidence: list[CompletionEvidenceOut]
    execution_mode: ExecutionMode
    cognitive_ownership: CognitiveOwnership
    source_refs: list[str] = Field(default_factory=list)
    risk_class: RiskClass | None = None
    reversible: bool | None = None


TASK_TYPE_ALIAS_MAP = {
    "learning": "LEARNING",
    "training": "TRAINING",
    "errorfix": "ERROR_FIX",
    "error_fix": "ERROR_FIX",
    "reflection": "REFLECTION",
    "social": "SOCIAL",
    "planning": "PLANNING",
    "study": "LEARNING",
    "review": "TRAINING",
    "practice": "TRAINING",
    "homework": "PLANNING",
    "exam": "REFLECTION",
    "worked_example_then_drill": "TRAINING",
    "other": "LEARNING",
}


def coerce_task_type(
    value: TaskType | str | Enum | None,
    *,
    default: TaskType | None = None,
) -> TaskType | None:
    if value is None:
        return default
    if isinstance(value, TaskType):
        return value

    raw_value = getattr(value, "value", value)
    if not isinstance(raw_value, str):
        return default

    normalized = raw_value.strip()
    if not normalized:
        return default

    mapped = TASK_TYPE_ALIAS_MAP.get(normalized.lower(), normalized.upper())
    try:
        return TaskType(mapped)
    except Exception:
        return default


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
    guide_json: dict | None = Field(default=None, description="Structured user-facing task guide")
    ai_prompt: str | None = Field(default=None, description="Copyable AI prompt scaffold")
    source_planning_session_id: str | None = Field(default=None, description="Origin planning session ID")
    phase_index: int | None = Field(default=None, ge=1, description="Phase index inside the planning strategy")
    success_criteria: str | None = Field(default=None, description="Task success criteria")
    action_plan: ActionPlanIn | None = Field(
        default=None, description="ActionPlan V3 contract block (omit for legacy tasks)"
    )

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_task_type(cls, value):
        parsed = coerce_task_type(value)
        return parsed if parsed is not None else value

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
    type: TaskType | None = Field(default=None, description="Task type")
    tags: list[str] | None = Field(default=None, description="Tags list")
    estimated_minutes: int | None = Field(default=None, ge=1, description="Estimated minutes")
    difficulty: int | None = Field(default=None, ge=1, le=5, description="Difficulty level")
    energy_cost: int | None = Field(default=None, ge=1, le=5, description="Energy cost")
    guide_content: str | None = Field(default=None, description="Guide content")
    priority: int | None = Field(default=None, description="Priority")
    order_index: int | None = Field(default=None, description="Display order")
    due_date: date | None = Field(default=None, description="Due date")
    user_note: str | None = Field(default=None, description="User note")
    knowledge_node_id: UUID | None = Field(default=None, description="Knowledge node ID")
    guide_json: dict | None = Field(default=None, description="Structured user-facing task guide")
    ai_prompt: str | None = Field(default=None, description="Copyable AI prompt scaffold")
    source_planning_session_id: str | None = Field(default=None, description="Origin planning session ID")
    phase_index: int | None = Field(default=None, ge=1, description="Phase index inside the planning strategy")
    success_criteria: str | None = Field(default=None, description="Task success criteria")
    action_plan: ActionPlanIn | None = Field(
        default=None,
        description="ActionPlan V3 contract block (explicit null = clear V3 semantics)",
    )

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_task_type(cls, value):
        # P2-J (daily-flow R2): TaskCreate accepts lowercase aliases
        # ("learning", "error_fix", "study", ...) via coerce_task_type, but
        # TaskUpdate did not — the same payload shape on a partial update
        # 422'd instead of mapping to the canonical enum.
        if value is None:
            return None
        parsed = coerce_task_type(value)
        return parsed if parsed is not None else value


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
    note: str | None = Field(default=None, validation_alias=AliasChoices("note", "user_note"), description="User note")
    completion_quality: int | None = Field(default=None, ge=1, le=5, description="Self rating 1-5")
    route_history_decision_id: str | None = Field(default=None, description="DualCore route decision id")
    routing_outcome_signal_id: str | None = Field(default=None, description="DualCore routing passive signal id")
    routing_trace_id: str | None = Field(default=None, description="DualCore routing trace id")


class TaskAbandon(BaseModel):
    """Abandon task"""

    task_id: UUID = Field(description="Task ID")
    reason: str | None = Field(default=None, description="Abandon reason")
    route_history_decision_id: str | None = Field(default=None, description="DualCore route decision id")
    routing_outcome_signal_id: str | None = Field(default=None, description="DualCore routing passive signal id")
    routing_trace_id: str | None = Field(default=None, description="DualCore routing trace id")


class TaskPause(BaseModel):
    """Pause task without counting it as success or failure."""

    reason: str | None = Field(default=None, max_length=500, description="Pause reason")


class TaskQuickActionRequest(BaseModel):
    """Lightweight task-card action request."""

    reason: str | None = Field(default=None, max_length=500, description="Optional user-facing reason")
    route_history_decision_id: str | None = Field(default=None, description="DualCore route decision id")
    routing_outcome_signal_id: str | None = Field(default=None, description="DualCore routing passive signal id")
    routing_trace_id: str | None = Field(default=None, description="DualCore routing trace id")


class TaskStuckRequest(BaseModel):
    """Current task execution context when the user asks for stuck help."""

    stuck_point: str | None = Field(default=None, max_length=500, description="Where the user feels blocked")
    recent_steps: list[str] = Field(default_factory=list, max_length=10, description="Recent execution steps")
    current_step_index: int | None = Field(default=None, ge=0, description="Current client-side step index")
    elapsed_seconds: int | None = Field(default=None, ge=0, description="Elapsed timer seconds")
    trigger: str | None = Field(default=None, max_length=100, description="Client trigger label")


class TaskSnoozeRequest(TaskQuickActionRequest):
    """Snooze a task without changing the plan structure."""

    days: int = Field(default=1, ge=1, le=30, description="Days to move the task forward")
    target_date: date | None = Field(default=None, description="Explicit target date")


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


class TaskBoundSourceInfo(BaseModel):
    """Lifecycle-aware source bound to a task."""

    id: UUID = Field(description="Source asset ID")
    title: str = Field(description="Source title")
    lifecycle_status: str = Field(default="active", description="Source lifecycle status")
    source_type: str = Field(default="file", description="Source type")
    linked_by: str | None = Field(default=None, description="Link origin")
    reason: str | None = Field(default=None, description="Why this source is bound")
    status: str | None = Field(default=None, description="Parsing or upload status")
    lifecycle_reason: str | None = Field(default=None, description="Lifecycle transition reason")
    updated_at: datetime | None = Field(default=None, description="Source updated time")


class TaskDetail(TaskBase):
    """Task detailed information"""

    user_id: UUID = Field(description="User ID")
    plan_id: UUID | None = Field(description="Related plan ID")
    guide_content: str | None = Field(description="Guide content")
    started_at: datetime | None = Field(description="Started time")
    confirmed_at: datetime | None = Field(description="Confirmed time")
    completed_at: datetime | None = Field(description="Completed time")
    paused_at: datetime | None = Field(description="Paused time")
    paused_reason: str | None = Field(description="Pause reason")
    actual_minutes: int | None = Field(description="Actual minutes")
    user_note: str | None = Field(description="User note")
    knowledge_node_id: UUID | None = Field(description="Knowledge node ID")
    tool_result_id: str | None = Field(description="Tool result ID")
    execution_mode: str | None = Field(default=None, description="Execution mode")
    order_index: int = Field(default=0, description="Display order")
    subtasks_total: int = Field(default=0, description="Total subtasks")
    subtasks_completed: int = Field(default=0, description="Completed subtasks")
    guide_json: dict | None = Field(default=None, description="Structured user-facing task guide")
    ai_prompt: str | None = Field(default=None, description="Copyable AI prompt scaffold")
    source_planning_session_id: str | None = Field(default=None, description="Origin planning session ID")
    phase_index: int | None = Field(default=None, description="Phase index inside the planning strategy")
    success_criteria: str | None = Field(default=None, description="Task success criteria")
    action_plan: ActionPlanOut | None = Field(
        default=None, description="ActionPlan V3 contract block (None for legacy tasks)"
    )
    bound_sources: list[TaskBoundSourceInfo] = Field(
        default_factory=list,
        description="Lifecycle-aware source assets currently bound to the task",
    )


class TaskReorderRequest(BaseModel):
    """Persist task ordering for the current user."""

    task_ids: list[UUID] = Field(min_length=1, description="Ordered task IDs")


class TaskResourceLinkCreate(BaseModel):
    """Attach a resource to a task."""

    resource_type: str = Field(
        ...,
        pattern="^(seed_library|seed_item|knowledge_node|external_url|file|note)$",
        description="Resource type",
    )
    resource_id: UUID | None = Field(default=None, description="Referenced resource ID")
    title: str | None = Field(default=None, max_length=255, description="Display title")
    url: str | None = Field(default=None, max_length=500, description="External URL")
    summary: str | None = Field(default=None, description="Short summary")
    resource_metadata: dict | None = Field(default=None, description="Extra metadata")
    order_index: int | None = Field(default=None, ge=0, description="Display order")
    is_primary: bool = Field(default=False, description="Primary resource flag")


class TaskResourceLinkInfo(BaseSchema):
    """Attached task resource."""

    task_id: UUID = Field(description="Task ID")
    resource_type: str = Field(description="Resource type")
    resource_id: UUID | None = Field(default=None, description="Referenced resource ID")
    title: str | None = Field(default=None, description="Display title")
    url: str | None = Field(default=None, description="External URL")
    summary: str | None = Field(default=None, description="Short summary")
    resource_metadata: dict | None = Field(default=None, description="Extra metadata")
    order_index: int = Field(default=0, description="Display order")
    is_primary: bool = Field(default=False, description="Primary resource flag")


class TaskDocumentLinkCreate(BaseModel):
    """Attach a document to a task."""

    file_id: UUID = Field(description="Stored file ID")
    linked_by: Literal["user", "ai"] = Field(default="user", description="Who created the link")


class TaskDocumentUnlinkRequest(BaseModel):
    """Remove a linked document from a task."""

    file_id: UUID = Field(description="Stored file ID")


class TaskDocumentInfo(BaseSchema):
    """Task-linked document."""

    task_id: UUID = Field(description="Task ID")
    file_id: UUID = Field(description="Stored file ID")
    file_name: str = Field(description="Original file name")
    mime_type: str = Field(description="Mime type")
    file_size: int = Field(description="File size in bytes")
    status: str = Field(description="Processing status")
    linked_by: str = Field(description="Link origin")
    document_quality_score: float = Field(description="Rolling document quality score")


class TaskDocumentSuggestion(BaseModel):
    """Suggested task-document link."""

    file_id: UUID = Field(description="Stored file ID")
    file_name: str = Field(description="Original file name")
    reason: str = Field(description="Why this document is relevant")
    source: str = Field(description="Suggestion source")
    node_id: UUID | None = Field(default=None, description="Related knowledge node ID")
    node_name: str | None = Field(default=None, description="Related knowledge node name")
    linked_by: str = Field(default="ai", description="Suggested link origin")
    status: str | None = Field(default=None, description="Current file processing status")


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
        parsed = coerce_task_type(value)
        return parsed if parsed is not None else value


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


class NextActionType(StrEnum):
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
    knowledge_node_id: UUID | None = Field(default=None, description="Linked knowledge node ID")
    estimated_minutes: int | None = Field(default=25, description="Estimated study time in minutes")
    guide_content: str | None = Field(default=None, description="Learning guide content")


class SubTaskUpdate(BaseModel):
    """Update subtask"""

    title: str | None = Field(default=None, min_length=1, max_length=255, description="Subtask title")
    description: str | None = Field(default=None, description="Subtask description")
    status: SubTaskStatus | None = Field(default=None, description="Subtask status")
    order: int | None = Field(default=None, description="Display order")
    knowledge_node_id: UUID | None = Field(default=None, description="Linked knowledge node ID")
    estimated_minutes: int | None = Field(default=None, description="Estimated study time in minutes")
    guide_content: str | None = Field(default=None, description="Learning guide content")


class SubTaskDetail(BaseSchema):
    """Subtask detailed information"""

    parent_task_id: UUID = Field(description="Parent task ID")
    title: str = Field(description="Subtask title")
    description: str | None = Field(default=None, description="Subtask description")
    order: int = Field(description="Display order")
    status: SubTaskStatus = Field(description="Subtask status")
    completed_at: datetime | None = Field(default=None, description="Completion time")
    knowledge_node_id: UUID | None = Field(default=None, description="Linked knowledge node ID")
    estimated_minutes: int = Field(description="Estimated study time in minutes")
    guide_content: str | None = Field(default=None, description="Learning guide content")


class SubTaskReorderRequest(BaseModel):
    """Reorder subtasks"""

    subtask_orders: list[dict] = Field(
        description="List of {subtask_id, order} pairs",
        examples=[[{"subtask_id": "uuid", "order": 0}, {"subtask_id": "uuid", "order": 1}]],
    )
