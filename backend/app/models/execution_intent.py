"""
ExecutionIntent - 面向外部执行器的结构化任务协议
"""

from __future__ import annotations

import enum

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class ExecutionMode(enum.StrEnum):
    """任务执行模式。"""

    HUMAN = "human"
    AGENT = "agent"
    HYBRID = "hybrid"


class ExecutorType(enum.StrEnum):
    """执行器类型。"""

    MANUAL = "manual"
    OPENCLAW = "openclaw"


class ExecutionTargetEnv(enum.StrEnum):
    """执行目标环境。"""

    BROWSER = "browser"
    SHELL = "shell"
    API = "api"
    DOCUMENT = "document"
    HUMAN = "human"


class ExecutionIntentStatus(enum.StrEnum):
    """执行意图生命周期状态。"""

    DRAFT = "draft"
    READY = "ready"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"
    HANDED_BACK = "handed_back"


class TrustLevel(enum.StrEnum):
    """执行结果信任等级。"""

    RAW = "raw"
    VALIDATED = "validated"
    TRUSTED = "trusted"


class ExecutionIntent(BaseModel):
    """面向执行层的标准任务协议。"""

    __tablename__ = "execution_intents"

    plan_id = Column(GUID(), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    execution_mode = Column(
        Enum(
            ExecutionMode,
            values_callable=_enum_values,
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
        default=ExecutionMode.HUMAN,
    )
    executor = Column(
        Enum(
            ExecutorType,
            values_callable=_enum_values,
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
        default=ExecutorType.MANUAL,
    )

    goal = Column(Text, nullable=False)
    instructions = Column(JSONBCompat, nullable=False, default=list)
    target_env = Column(
        Enum(
            ExecutionTargetEnv,
            values_callable=_enum_values,
            create_constraint=False,
            native_enum=False,
        ),
        nullable=True,
    )
    policy = Column(JSONBCompat, nullable=False, default=dict)
    success_criteria = Column(JSONBCompat, nullable=False, default=dict)
    result_contract = Column(JSONBCompat, nullable=False, default=dict)
    timeout_seconds = Column(Integer, nullable=False, default=300)

    status = Column(
        Enum(
            ExecutionIntentStatus,
            values_callable=_enum_values,
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
        default=ExecutionIntentStatus.DRAFT,
        index=True,
    )
    trust_level = Column(
        Enum(
            TrustLevel,
            values_callable=_enum_values,
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
        default=TrustLevel.RAW,
    )

    external_run_id = Column(String(255), nullable=True, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    error_category = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    dispatched_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("Task", backref="execution_intents", foreign_keys=[task_id])
    plan = relationship("Plan", backref="execution_intents", foreign_keys=[plan_id])
    user = relationship("User", backref="execution_intents", foreign_keys=[user_id])
    execution_record = relationship(
        "ExecutionRecord",
        back_populates="execution_intent",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_exec_intent_user_status", "user_id", "status"),
        Index("idx_exec_intent_task", "task_id"),
        Index("idx_exec_intent_created", "created_at"),
        Index("idx_exec_intent_external_run", "external_run_id"),
    )

    def __repr__(self):
        return f"<ExecutionIntent(task_id={self.task_id}, status={self.status}, executor={self.executor})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id) if self.plan_id else None,
            "task_id": str(self.task_id),
            "user_id": str(self.user_id),
            "execution_mode": self.execution_mode.value if self.execution_mode else None,
            "executor": self.executor.value if self.executor else None,
            "goal": self.goal,
            "instructions": self.instructions or [],
            "target_env": self.target_env.value if self.target_env else None,
            "policy": self.policy or {},
            "success_criteria": self.success_criteria or {},
            "result_contract": self.result_contract or {},
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value if self.status else None,
            "trust_level": self.trust_level.value if self.trust_level else None,
            "external_run_id": self.external_run_id,
            "idempotency_key": self.idempotency_key,
            "error_category": self.error_category,
            "error_message": self.error_message,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
