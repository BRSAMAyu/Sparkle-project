"""Audit log for OpenClaw execution actions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, HardDeleteBaseModel


class ExecutionAuditLog(HardDeleteBaseModel):
    """Append-only audit trail for execution lifecycle actions."""

    __tablename__ = "execution_audit_log"

    intent_id = Column(GUID(), ForeignKey("execution_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    actor = Column(String(32), nullable=False, index=True)
    details = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    intent = relationship("ExecutionIntent", backref="audit_logs", foreign_keys=[intent_id])
    user = relationship("User", backref="execution_audit_logs", foreign_keys=[user_id])


Index("idx_execution_audit_intent_occurred", ExecutionAuditLog.intent_id, ExecutionAuditLog.occurred_at)
Index("idx_execution_audit_user_action", ExecutionAuditLog.user_id, ExecutionAuditLog.action)
