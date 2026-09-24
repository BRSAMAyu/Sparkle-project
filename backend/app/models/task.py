"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

任务模型
Task Model - 学习任务卡片系统
"""

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
    inspect,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class TaskType(enum.StrEnum):
    LEARNING = "LEARNING"
    TRAINING = "TRAINING"
    ERROR_FIX = "ERROR_FIX"
    REFLECTION = "REFLECTION"
    SOCIAL = "SOCIAL"
    PLANNING = "PLANNING"
    OCR = "OCR"


class TaskStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    RESTORE = "RESTORE"
    STUCK = "STUCK"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class SubTaskStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class CognitiveOwnership(enum.StrEnum):
    """X-01 · D13 cognitive_ownership 首版定义（与 execution_mode 正交的认知归属轴）。

    - USER_CORE：该步骤本身即用户想获得的能力/判断/创作（学习、反思、关系沟通）；
    - SHARED：混合认知（agent 准备/校对，人做核心决定或创作）；
    - DELEGATED：机械性步骤（检索、整理、格式转换），可整体委托。
    语义真源：app/core/action_plan.py（契约）与 v3/02_core_systems/HUMAN_AGENT_HYBRID.md §2。
    """

    USER_CORE = "user_core"
    SHARED = "shared"
    DELEGATED = "delegated"


class RiskClass(enum.StrEnum):
    """X-01 · 风险分级（AGENT_RUNTIME §3 run contract 的 risk_class 同名对齐）。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _string_enum(enum_cls: type[enum.Enum]) -> Enum:
    """非原生枚举列（VARCHAR 存储，应用层校验）——沿用 execution_intent.py 模式。"""
    return Enum(
        enum_cls,
        values_callable=lambda members: [member.value for member in members],
        create_constraint=False,
        native_enum=False,
    )


class Task(BaseModel):
    __tablename__ = "tasks"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("plans.id"), nullable=True, index=True)

    # 任务基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    tags: Mapped[Any] = mapped_column(JSONBCompat, default=list, nullable=False)  # 标签列表 (使用 JSONB)

    # 时间和难度
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5
    energy_cost: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5

    # AI生成内容
    guide_content: Mapped[str] = mapped_column(Text, nullable=True)
    guide_json: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    ai_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    source_planning_session_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    phase_index: Mapped[int] = mapped_column(Integer, nullable=True)
    success_criteria: Mapped[str] = mapped_column(Text, nullable=True)

    # 状态信息
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 追溯信息
    tool_result_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=True, default=None)

    # 暂停信息
    paused_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    paused_reason: Mapped[str] = mapped_column(Text, nullable=True)

    # 完成信息
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    user_note: Mapped[str] = mapped_column(Text, nullable=True)

    # 优先级和截止日期
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=True)

    # Knowledge Galaxy Integration
    knowledge_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=True)
    auto_expand_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)

    # ── X-01 · ActionPlan V3 契约列（全部 nullable：NULL = legacy/V2.x 行）─────
    # 契约真源：app/core/action_plan.py；execution_mode 复用上方既有 String(20)
    # 镜像列（ExecutionIntent 唯一协议），不新增第二执行模式列。
    action_schema_version: Mapped[str] = mapped_column(String(16), nullable=True)  # "action_plan.v1" | NULL=legacy
    desired_outcome: Mapped[str] = mapped_column(Text, nullable=True)  # 期望结果陈述（outcome 语义）
    smallest_useful_step: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # {description, useful_because:[封闭枚举]}
    completion_evidence: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # [{evidence_kind, ref?, description?}]
    cognitive_ownership: Mapped[Any] = mapped_column(_string_enum(CognitiveOwnership), nullable=True)  # D13
    source_refs: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # ["scheme://id", ...] 封闭 scheme（C-01 对齐）
    risk_class: Mapped[Any] = mapped_column(_string_enum(RiskClass), nullable=True)  # 风险分级
    reversible: Mapped[bool] = mapped_column(Boolean, nullable=True)  # 可撤销性（risk/reversibility 成对）

    # Subtask counters
    subtasks_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subtasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系定义
    user = relationship("User", back_populates="tasks")
    plan = relationship("Plan", back_populates="tasks")
    knowledge_node = relationship("KnowledgeNode")
    chat_messages = relationship("ChatMessage", back_populates="task", cascade="all, delete-orphan", lazy="dynamic")

    curiosity_capsules = relationship(
        "CuriosityCapsule", back_populates="task", cascade="all, delete-orphan", lazy="dynamic"
    )

    # Subtasks relationship
    subtasks = relationship(
        "SubTask", back_populates="parent_task", cascade="all, delete-orphan", lazy="dynamic", order_by="SubTask.order"
    )

    # Task feedbacks relationship
    feedbacks = relationship("TaskFeedback", back_populates="task", cascade="all, delete-orphan", lazy="dynamic")

    resource_links = relationship(
        "TaskResourceLink",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    knowledge_links = relationship(
        "TaskKnowledgeLink",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    document_links = relationship(
        "TaskDocument",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Task(title={self.title}, status={self.status})>"

    @property
    def action_plan(self) -> dict | None:
        """ActionPlan V3 块的读侧投影（供 TaskDetail from_attributes 消费）。

        X-01 返修 F1/F2：**必须**走 app/core/action_plan.action_plan_projection 统一门
        （版本 + 全封闭词表 + execution_mode 归一，任一不过 → None + WARN）。禁止在此
        原样投影列值——曾使单行脏/未来枚举值打挂全部任务读端点。延迟 import 解除
        models↔core 循环依赖（调用时两模块均已初始化）。
        """
        from app.core.action_plan import action_plan_projection

        return action_plan_projection(self)


# 创建索引
Index("idx_tasks_user_id", Task.user_id)
Index("idx_tasks_plan_id", Task.plan_id)
Index("idx_tasks_status", Task.status)
Index("idx_tasks_created_at", Task.created_at)
Index("idx_tasks_due_date", Task.due_date)
Index("idx_tasks_user_order_index", Task.user_id, Task.order_index)


class SubTask(BaseModel):
    """子任务模型 - 用于任务的细分"""

    __tablename__ = "subtasks"

    parent_task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id", ondelete="SET NULL"), nullable=True, index=True)

    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 学习指导
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    guide_content: Mapped[str] = mapped_column(Text, nullable=True)

    # 排序和状态
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[SubTaskStatus] = mapped_column(Enum(SubTaskStatus), default=SubTaskStatus.PENDING, nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    parent_task = relationship("Task", back_populates="subtasks")

    def __repr__(self):
        return f"<SubTask(title={self.title}, status={self.status})>"


# SubTask 索引
Index("idx_subtasks_parent_task_id", SubTask.parent_task_id)
Index("idx_subtasks_status", SubTask.status)
Index("idx_subtasks_order", SubTask.order)


# SQLAlchemy 事件监听器 - 自动更新父任务的子任务计数
@event.listens_for(SubTask, "after_insert")
def update_total_on_subtask_insert(mapper, connection, target):
    """创建子任务时自动增加父任务的 subtasks_total"""
    connection.execute(
        update(Task).where(Task.id == target.parent_task_id).values(subtasks_total=Task.subtasks_total + 1)
    )


@event.listens_for(SubTask, "after_delete")
def update_total_on_subtask_delete(mapper, connection, target):
    """删除子任务时自动减少父任务的 subtasks_total"""
    connection.execute(
        update(Task)
        .where(Task.id == target.parent_task_id)
        .values(
            subtasks_total=Task.subtasks_total - 1,
            subtasks_completed=Task.subtasks_completed - (1 if target.status == SubTaskStatus.COMPLETED else 0),
        )
    )


@event.listens_for(SubTask, "after_update")
def update_completed_on_subtask_status_change(mapper, connection, target):
    """子任务状态变更时自动更新父任务的 subtasks_completed"""
    state = inspect(target)
    status_history = state.attrs.status.history
    if not status_history.has_changes():
        return

    old_status = status_history.deleted[0] if status_history.deleted else None
    new_status = status_history.added[0] if status_history.added else target.status
    if old_status == new_status:
        return

    delta = 0
    if new_status == SubTaskStatus.COMPLETED:
        delta = 1
    elif old_status == SubTaskStatus.COMPLETED:
        delta = -1

    if delta != 0:
        connection.execute(
            update(Task)
            .where(Task.id == target.parent_task_id)
            .values(subtasks_completed=Task.subtasks_completed + delta)
        )
