"""Persistent models for the safe adaptive experiment pipeline."""

from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class SafeExperiment(BaseModel):
    __tablename__ = "safe_experiments"

    experiment_key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    hypothesis = Column(Text, nullable=False)
    domain = Column(String(80), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    eligible_context = Column(JSON, nullable=False, default=dict)
    excluded_context = Column(JSON, nullable=False, default=list)
    policies = Column(JSON, nullable=False, default=list)
    assignment_mode = Column(String(32), nullable=False, default="shadow")
    reward_model = Column(JSON, nullable=False, default=dict)
    guardrails = Column(JSON, nullable=False, default=dict)
    min_episodes = Column(Integer, nullable=False, default=50)
    min_distinct_users = Column(Integer, nullable=False, default=15)
    evidence_grade_required = Column(Integer, nullable=False, default=3)
    current_episodes = Column(Integer, nullable=False, default=0)
    distinct_users = Column(JSON, nullable=False, default=list)
    outcome_history = Column(JSON, nullable=False, default=list)
    rollback_version = Column(String(80), nullable=True)
    previous_versions = Column(JSON, nullable=False, default=list)
    kill_switch_key = Column(String(120), nullable=False, index=True)
    incident_trace = Column(JSON, nullable=False, default=list)
    promotion_candidate = Column(JSON, nullable=True)
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    concluded_at = Column(DateTime, nullable=True)

    episodes = relationship(
        "SafeExperimentEpisode",
        back_populates="experiment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SafeExperimentEpisode(BaseModel):
    __tablename__ = "safe_experiment_episodes"

    experiment_id = Column(GUID(), ForeignKey("safe_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_key = Column(String(64), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    context_signature = Column(JSON, nullable=False, default=dict)
    candidate_actions = Column(JSON, nullable=False, default=list)
    selected_action = Column(String(160), nullable=False)
    selection_reason = Column(String(160), nullable=False, default="")
    assignment_mode = Column(String(32), nullable=False, default="shadow")
    risk_level = Column(String(32), nullable=False, default="low")
    reward = Column(Float, nullable=True)
    outcome_vector = Column(JSON, nullable=False, default=dict)
    guardrail_result = Column(JSON, nullable=False, default=dict)
    incident_trace = Column(JSON, nullable=True)

    experiment = relationship("SafeExperiment", back_populates="episodes")


Index("idx_safe_experiments_status_domain", SafeExperiment.status, SafeExperiment.domain)
Index("idx_safe_experiment_episodes_exp_created", SafeExperimentEpisode.experiment_id, SafeExperimentEpisode.created_at)
