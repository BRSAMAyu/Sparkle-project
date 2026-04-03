"""Persistent schedules for delegated OpenClaw executions."""

from __future__ import annotations

import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class ExecutionScheduleTriggerType(str, enum.Enum):
    CRON = "cron"
    EVENT = "event"
    CONDITION = "condition"


class ExecutionSchedule(BaseModel):
    __tablename__ = "execution_schedules"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    intent_template = Column(JSONBCompat, nullable=False, default=dict)
    trigger_type = Column(
        Enum(
            ExecutionScheduleTriggerType,
            values_callable=_enum_values,
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
    )
    trigger_config = Column(JSONBCompat, nullable=False, default=dict)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    user = relationship("User", backref="execution_schedules", foreign_keys=[user_id])
    task = relationship("Task", backref="execution_schedules", foreign_keys=[task_id])

    __table_args__ = (
        Index("idx_execution_schedule_due", "is_active", "next_run_at"),
        Index("idx_execution_schedule_user_trigger", "user_id", "trigger_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_id": str(self.task_id),
            "intent_template": self.intent_template or {},
            "trigger_type": self.trigger_type.value if self.trigger_type else None,
            "trigger_config": self.trigger_config or {},
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
