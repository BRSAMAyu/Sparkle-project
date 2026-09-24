"""
Intervention Models
Phase 0: Contract, guardrails, audit, and feedback storage.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class InterventionRequest(BaseModel):
    __tablename__ = "intervention_requests"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(120), nullable=True, index=True)

    requested_level: Mapped[str] = mapped_column(String(40), nullable=False)
    final_level: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    reason: Mapped[Any] = mapped_column(JSON, nullable=True)
    content: Mapped[Any] = mapped_column(JSON, nullable=True)
    cooldown_policy: Mapped[Any] = mapped_column(JSON, nullable=True)
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=True)
    template_id: Mapped[str] = mapped_column(String(100), nullable=True)
    template_variant_id: Mapped[str] = mapped_column(String(100), nullable=True)
    scaffolding_level: Mapped[int] = mapped_column(Integer, nullable=True)
    intent_type: Mapped[str] = mapped_column(String(50), nullable=True)

    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str] = mapped_column(String(80), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_retractable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supersedes_id: Mapped[Any] = mapped_column(GUID(), nullable=True)

    user = relationship("User", back_populates="intervention_requests")
    audits = relationship(
        "InterventionAuditLog",
        back_populates="request",
        cascade="all, delete-orphan"
    )
    feedback = relationship(
        "InterventionFeedback",
        back_populates="request",
        cascade="all, delete-orphan"
    )


class InterventionAuditLog(BaseModel):
    __tablename__ = "intervention_audit_logs"

    request_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("intervention_requests.id"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    action: Mapped[str] = mapped_column(String(40), nullable=False)
    guardrail_result: Mapped[Any] = mapped_column(JSON, nullable=True)
    decision_trace: Mapped[Any] = mapped_column(JSON, nullable=True)
    evidence_refs: Mapped[Any] = mapped_column(JSON, nullable=True)

    requested_level: Mapped[str] = mapped_column(String(40), nullable=False)
    final_level: Mapped[str] = mapped_column(String(40), nullable=False)

    policy_version: Mapped[str] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str] = mapped_column(String(80), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    request = relationship("InterventionRequest", back_populates="audits")


class InterventionFeedback(BaseModel):
    __tablename__ = "intervention_feedback"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "request_id",
            "feedback_type",
            "idempotency_key",
            name="uq_intervention_feedback_idempotency",
        ),
    )

    request_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("intervention_requests.id"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    extra_data: Mapped[Any] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    request = relationship("InterventionRequest", back_populates="feedback")
    user = relationship("User", back_populates="intervention_feedback")


class UserInterventionSettings(BaseModel):
    __tablename__ = "user_intervention_settings"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    interrupt_threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    daily_interrupt_budget: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    quiet_hours: Mapped[Any] = mapped_column(JSON, nullable=True)
    topic_allowlist: Mapped[Any] = mapped_column(JSON, nullable=True)
    topic_blocklist: Mapped[Any] = mapped_column(JSON, nullable=True)
    do_not_disturb: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="intervention_settings")
