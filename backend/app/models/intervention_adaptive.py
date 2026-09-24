"""Adaptive intervention models (templates, scaffolding, signals)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel


class ScaffoldingState(BaseModel):
    __tablename__ = "scaffolding_states"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    capability_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    current_zone: Mapped[str] = mapped_column(String(20), default="flow", nullable=False)
    support_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    template_variant_id: Mapped[str] = mapped_column(String(100), nullable=True)
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_intervention_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    history: Mapped[Any] = mapped_column(JSON, nullable=True)


class PassiveSignal(BaseModel):
    __tablename__ = "passive_signals"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    intervention_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("intervention_requests.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    context: Mapped[Any] = mapped_column(JSON, nullable=True)


class BehavioralOutcome(BaseModel):
    __tablename__ = "behavioral_outcomes"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    intervention_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("intervention_requests.id"), nullable=False, index=True)
    outcome_type: Mapped[str] = mapped_column(String(50), nullable=False)
    time_to_outcome: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context: Mapped[Any] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InterventionTemplate(BaseModel):
    __tablename__ = "intervention_templates"

    template_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    intent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    support_level: Mapped[int] = mapped_column(Integer, nullable=False)
    variants: Mapped[Any] = mapped_column(JSON, nullable=False)
    meta: Mapped[Any] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
