from __future__ import annotations

from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class AuroraStateSnapshot(BaseModel):
    __tablename__ = "aurora_state_snapshots"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    surface = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(128), nullable=False, index=True)
    runtime_session_id = Column(String(128), nullable=True)
    snapshot_version = Column(Integer, nullable=False, default=1)
    snapshot_at = Column(DateTime, nullable=False, index=True)
    user_model_snapshot = Column(JSONBCompat, nullable=False, default=dict)
    informational_tensions = Column(JSONBCompat, nullable=False, default=list)
    current_intent = Column(JSONBCompat, nullable=True)
    latent_threads = Column(JSONBCompat, nullable=False, default=list)
    activity_profile = Column(JSONBCompat, nullable=False, default=dict)
    last_decision_at = Column(DateTime, nullable=True)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    user = relationship("User", backref="aurora_state_snapshots")

    __table_args__ = (
        Index(
            "idx_aurora_snapshot_scope",
            "user_id",
            "surface",
            "conversation_id",
            "snapshot_at",
        ),
    )


class AuroraScheduledWake(BaseModel):
    __tablename__ = "aurora_scheduled_wakes"

    wake_id = Column(String(128), nullable=False, index=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    surface = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(128), nullable=False, index=True)
    session_id = Column(GUID(), nullable=True, index=True)
    runtime_session_id = Column(String(128), nullable=True)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    executed_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    reason = Column(Text, nullable=False)
    planned_action = Column(String(64), nullable=False)
    urgency_score = Column(Float, nullable=False, default=0.5)
    payload = Column(JSONBCompat, nullable=False, default=dict)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)
    suppression_reason = Column(String(64), nullable=True)

    user = relationship("User", backref="aurora_scheduled_wakes")

    __table_args__ = (
        Index("idx_aurora_wake_due", "status", "scheduled_at"),
        Index("idx_aurora_wake_scope", "user_id", "surface", "conversation_id"),
        Index("idx_aurora_wake_id", "wake_id"),
    )


class AuroraDecisionTelemetry(BaseModel):
    __tablename__ = "aurora_decision_telemetry"

    decision_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    surface = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(128), nullable=False, index=True)
    request_id = Column(String(128), nullable=True, index=True)
    decided_at = Column(DateTime, nullable=False, index=True)
    wake_score = Column(Float, nullable=False, default=0.0)
    energy_level = Column(String(16), nullable=False, default="light", index=True)
    strategy_payload = Column(JSONBCompat, nullable=False, default=dict)
    expression_payload = Column(JSONBCompat, nullable=False, default=dict)
    context_mask = Column(JSONBCompat, nullable=False, default=list)
    action = Column(String(64), nullable=False, index=True)
    chat_directive_core = Column(JSONBCompat, nullable=False, default=dict)
    standard_layer_contract = Column(JSONBCompat, nullable=False, default=dict)
    strategy_confidence = Column(Float, nullable=False, default=0.7)
    outcome = Column(String(32), nullable=True, index=True)
    outcome_filled_at = Column(DateTime, nullable=True, index=True)
    outcome_reason = Column(Text, nullable=True)

    user = relationship("User", backref="aurora_decision_telemetry")

    __table_args__ = (
        Index("idx_aurora_decision_telemetry_scope_ts", "user_id", "conversation_id", "decided_at"),
        Index("idx_aurora_decision_telemetry_surface_ts", "surface", "decided_at"),
    )


class AuroraCoreSessionSnapshot(BaseModel):
    """Durable fallback for the L3 Aurora Core Session Redis FSM."""

    __tablename__ = "aurora_core_session_snapshots"

    session_id = Column(String(128), nullable=False, unique=True, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    conversation_id = Column(String(128), nullable=True, index=True)
    surface = Column(String(64), nullable=False, default="aurora_modeling", index=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    stage = Column(String(32), nullable=False, default="declare", index=True)
    resume_token_hash = Column(String(64), nullable=True, unique=True, index=True)
    last_activity_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    payload = Column(JSONBCompat, nullable=False, default=dict)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_aurora_core_session_user_status", "user_id", "status", "last_activity_at"),
        Index("idx_aurora_core_session_conversation", "user_id", "conversation_id", "last_activity_at"),
    )


class DurableSessionStateSnapshot(BaseModel):
    """Durable fallback for orchestration FSM state when Redis misses."""

    __tablename__ = "durable_session_state_snapshots"

    session_id = Column(String(128), nullable=False, unique=True, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    request_id = Column(String(128), nullable=True, index=True)
    fsm_state = Column(String(32), nullable=False, index=True)
    details = Column(Text, nullable=False, default="")
    payload = Column(JSONBCompat, nullable=False, default=dict)
    recoverable = Column(Boolean, nullable=False, default=True, index=True)
    last_seen_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_durable_session_state_recovery", "session_id", "recoverable", "expires_at"),
        Index("idx_durable_session_state_user_seen", "user_id", "last_seen_at"),
    )
