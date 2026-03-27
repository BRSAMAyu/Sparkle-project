"""
ExecutionRecord - 外部执行器原始结果记录
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ExecutionRecord(BaseModel):
    """外部执行器原始结果记录。"""

    __tablename__ = "execution_records"

    execution_intent_id = Column(
        GUID(),
        ForeignKey("execution_intents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    executor_type = Column(String(50), nullable=False, default="openclaw")
    external_run_id = Column(String(255), nullable=True)

    raw_response = Column(JSONBCompat, nullable=False, default=dict)
    parsed_output = Column(JSONBCompat, nullable=True)
    artifacts = Column(JSONBCompat, nullable=False, default=list)

    trust_level = Column(String(20), nullable=False, default="raw")
    validation_passed = Column(Integer, nullable=True)
    validation_total = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)

    duration_ms = Column(Integer, nullable=True)
    token_usage = Column(JSONBCompat, nullable=True)
    tool_calls_count = Column(Integer, nullable=True, default=0)
    approval_requested = Column(Integer, nullable=True, default=0)

    error_category = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)

    execution_intent = relationship("ExecutionIntent", back_populates="execution_record", uselist=False)
    user = relationship("User", backref="execution_records")
    task = relationship("Task", backref="execution_records")

    __table_args__ = (
        Index("idx_exec_record_user", "user_id"),
        Index("idx_exec_record_intent", "execution_intent_id"),
        Index("idx_exec_record_trust", "trust_level"),
        Index("idx_exec_record_created", "created_at"),
    )

    def __repr__(self):
        return (
            f"<ExecutionRecord(intent_id={self.execution_intent_id}, "
            f"trust={self.trust_level}, score={self.quality_score})>"
        )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "execution_intent_id": str(self.execution_intent_id),
            "user_id": str(self.user_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "executor_type": self.executor_type,
            "external_run_id": self.external_run_id,
            "parsed_output": self.parsed_output,
            "artifacts": self.artifacts or [],
            "trust_level": self.trust_level,
            "validation_passed": self.validation_passed,
            "validation_total": self.validation_total,
            "quality_score": self.quality_score,
            "duration_ms": self.duration_ms,
            "approval_requested": self.approval_requested,
            "error_category": self.error_category,
            "error_message": self.error_message,
            "execution_started_at": self.execution_started_at.isoformat() if self.execution_started_at else None,
            "execution_completed_at": self.execution_completed_at.isoformat() if self.execution_completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
