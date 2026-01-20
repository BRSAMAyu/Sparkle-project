"""
Intervention Models
Phase 0: Contract, guardrails, audit, and feedback storage.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Integer, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class InterventionRequest(BaseModel):
    __tablename__ = "intervention_requests"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    dedupe_key = Column(String(200), nullable=True, index=True)
    topic = Column(String(120), nullable=True, index=True)

    requested_level = Column(String(40), nullable=False)
    final_level = Column(String(40), nullable=False)
    status = Column(String(40), nullable=False, index=True)

    reason = Column(JSON, nullable=True)
    content = Column(JSON, nullable=True)
    cooldown_policy = Column(JSON, nullable=True)
    delivery_method = Column(String(20), nullable=True)
    template_id = Column(String(100), nullable=True)
    template_variant_id = Column(String(100), nullable=True)
    scaffolding_level = Column(Integer, nullable=True)
    intent_type = Column(String(50), nullable=True)

    schema_version = Column(String(50), nullable=False)
    policy_version = Column(String(50), nullable=True)
    model_version = Column(String(80), nullable=True)

    expires_at = Column(DateTime, nullable=True)
    is_retractable = Column(Boolean, default=True, nullable=False)
    supersedes_id = Column(GUID(), nullable=True)

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

    request_id = Column(GUID(), ForeignKey("intervention_requests.id"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    action = Column(String(40), nullable=False)
    guardrail_result = Column(JSON, nullable=True)
    decision_trace = Column(JSON, nullable=True)
    evidence_refs = Column(JSON, nullable=True)

    requested_level = Column(String(40), nullable=False)
    final_level = Column(String(40), nullable=False)

    policy_version = Column(String(50), nullable=True)
    model_version = Column(String(80), nullable=True)
    schema_version = Column(String(50), nullable=True)

    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

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

    request_id = Column(GUID(), ForeignKey("intervention_requests.id"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    feedback_type = Column(String(40), nullable=False, index=True)
    extra_data = Column(JSON, nullable=True)
    idempotency_key = Column(String(200), nullable=False, index=True)

    request = relationship("InterventionRequest", back_populates="feedback")
    user = relationship("User", back_populates="intervention_feedback")


class UserInterventionSettings(BaseModel):
    __tablename__ = "user_intervention_settings"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    interrupt_threshold = Column(Float, default=0.5, nullable=False)
    daily_interrupt_budget = Column(Integer, default=3, nullable=False)
    cooldown_minutes = Column(Integer, default=120, nullable=False)
    quiet_hours = Column(JSON, nullable=True)
    topic_allowlist = Column(JSON, nullable=True)
    topic_blocklist = Column(JSON, nullable=True)
    do_not_disturb = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="intervention_settings")
