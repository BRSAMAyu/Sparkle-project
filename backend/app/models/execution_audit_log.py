"""Audit log for OpenClaw execution actions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, HardDeleteBaseModel


class ExecutionAuditLog(HardDeleteBaseModel):
    """Append-only audit trail for execution lifecycle actions."""

    __tablename__ = "execution_audit_log"

    intent_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("execution_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    details: Mapped[Any] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    intent = relationship("ExecutionIntent", backref="audit_logs", foreign_keys=[intent_id])
    user = relationship("User", backref="execution_audit_logs", foreign_keys=[user_id])


Index("idx_execution_audit_intent_occurred", ExecutionAuditLog.intent_id, ExecutionAuditLog.occurred_at)
Index("idx_execution_audit_user_action", ExecutionAuditLog.user_id, ExecutionAuditLog.action)
