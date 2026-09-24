"""Persistent models for the safe adaptive experiment pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class SafeExperiment(BaseModel):
    __tablename__ = "safe_experiments"

    experiment_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    eligible_context: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    excluded_context: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    policies: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    assignment_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="shadow")
    reward_model: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    guardrails: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    min_episodes: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    min_distinct_users: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    evidence_grade_required: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    current_episodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_users: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    outcome_history: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    rollback_version: Mapped[str] = mapped_column(String(80), nullable=True)
    previous_versions: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    kill_switch_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    incident_trace: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    promotion_candidate: Mapped[Any] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    concluded_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    episodes = relationship(
        "SafeExperimentEpisode",
        back_populates="experiment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SafeExperimentEpisode(BaseModel):
    __tablename__ = "safe_experiment_episodes"

    experiment_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("safe_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    context_signature: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    candidate_actions: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    selected_action: Mapped[str] = mapped_column(String(160), nullable=False)
    selection_reason: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    assignment_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="shadow")
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="low")
    reward: Mapped[float] = mapped_column(Float, nullable=True)
    outcome_vector: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    guardrail_result: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    incident_trace: Mapped[Any] = mapped_column(JSON, nullable=True)

    experiment = relationship("SafeExperiment", back_populates="episodes")


Index("idx_safe_experiments_status_domain", SafeExperiment.status, SafeExperiment.domain)
Index("idx_safe_experiment_episodes_exp_created", SafeExperimentEpisode.experiment_id, SafeExperimentEpisode.created_at)
