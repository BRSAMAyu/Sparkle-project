from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class AuroraJudgmentRecord(BaseModel):
    __tablename__ = "aurora_judgment_records"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_sufficiency_score: Mapped[float] = mapped_column(Float, nullable=False)
    task_missing_dimensions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    context_sufficiency_score: Mapped[float] = mapped_column(Float, nullable=False)
    context_missing_dimensions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    judge_version: Mapped[str] = mapped_column(String(16), nullable=False, default="v1")
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user = relationship("User", backref="aurora_judgment_records")


Index(
    "idx_aurora_judgment_records_user_computed",
    AuroraJudgmentRecord.user_id,
    AuroraJudgmentRecord.computed_at,
)


class ConflictResolutionRecord(BaseModel):
    __tablename__ = "conflict_resolution_records"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    loser_record_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    winner_record_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    loser_lane: Mapped[str] = mapped_column(String(40), nullable=True)
    winner_lane: Mapped[str] = mapped_column(String(40), nullable=True)
    resolution_action: Mapped[str] = mapped_column(String(32), nullable=False)
    resolution_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    conflict_key: Mapped[str] = mapped_column(String(64), nullable=True)
    evidence_tokens: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    metadata_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)

    user = relationship("User", backref="conflict_resolution_records")


Index(
    "idx_conflict_resolution_records_user_resolved",
    ConflictResolutionRecord.user_id,
    ConflictResolutionRecord.resolved_at,
)
Index(
    "idx_conflict_resolution_records_user_conflict_key",
    ConflictResolutionRecord.user_id,
    ConflictResolutionRecord.conflict_key,
)


class UnresolvedConflict(BaseModel):
    __tablename__ = "unresolved_conflicts"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    conflict_key: Mapped[str] = mapped_column(String(64), nullable=False)
    left_record_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    right_record_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    left_summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    right_summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    left_lane: Mapped[str] = mapped_column(String(40), nullable=False)
    right_lane: Mapped[str] = mapped_column(String(40), nullable=False)
    left_evidence_token: Mapped[str] = mapped_column(String(128), nullable=True)
    right_evidence_token: Mapped[str] = mapped_column(String(128), nullable=True)
    left_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    right_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_user")
    surfaced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolution_reason: Mapped[str] = mapped_column(String(128), nullable=True)
    selected_side: Mapped[str] = mapped_column(String(16), nullable=True)

    user = relationship("User", backref="unresolved_conflicts")


Index("idx_unresolved_conflicts_user_status", UnresolvedConflict.user_id, UnresolvedConflict.status)
Index("idx_unresolved_conflicts_user_conflict_key", UnresolvedConflict.user_id, UnresolvedConflict.conflict_key)


class RoutingDecisionLog(Base):
    __tablename__ = "routing_decision_log"

    decision_id: Mapped[Any] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    input_aggregator_snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sufficiency_judgment_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    source_state_v2: Mapped[Any] = mapped_column(JSONBCompat, nullable=True, default=dict)
    source_state_v2_key: Mapped[str] = mapped_column(String(255), nullable=True)
    skills_injected: Mapped[Any] = mapped_column(JSONBCompat, nullable=True, default=list)
    idiographic_associations_injected: Mapped[Any] = mapped_column(
        JSONBCompat, nullable=True, default=list
    )
    outcome_signal_id: Mapped[str] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=True)
    outcome_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    outcome_type: Mapped[str] = mapped_column(String(32), nullable=True)
    outcome_collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", backref="routing_decision_logs")


Index("idx_routing_decision_log_user_decided", RoutingDecisionLog.user_id, RoutingDecisionLog.decided_at)
Index("idx_routing_decision_log_user_outcome", RoutingDecisionLog.user_id, RoutingDecisionLog.outcome_collected_at)
Index("idx_routing_decision_log_user_outcome_v2", RoutingDecisionLog.user_id, RoutingDecisionLog.outcome_timestamp)
Index("idx_routing_decision_log_source_state_v2_key", RoutingDecisionLog.source_state_v2_key)
