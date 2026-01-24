"""Adaptive intervention models (templates, scaffolding, signals)."""

from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Integer, Float

from app.models.base import BaseModel, GUID


class ScaffoldingState(BaseModel):
    __tablename__ = "scaffolding_states"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    capability_level = Column(Float, default=0.5, nullable=False)
    current_zone = Column(String(20), default="flow", nullable=False)
    support_level = Column(Integer, default=3, nullable=False)
    template_variant_id = Column(String(100), nullable=True)
    consecutive_successes = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    last_intervention_timestamp = Column(DateTime, nullable=True)
    history = Column(JSON, nullable=True)


class PassiveSignal(BaseModel):
    __tablename__ = "passive_signals"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)
    intervention_id = Column(GUID(), ForeignKey("intervention_requests.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    context = Column(JSON, nullable=True)


class BehavioralOutcome(BaseModel):
    __tablename__ = "behavioral_outcomes"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    intervention_id = Column(GUID(), ForeignKey("intervention_requests.id"), nullable=False, index=True)
    outcome_type = Column(String(50), nullable=False)
    time_to_outcome = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    context = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class InterventionTemplate(BaseModel):
    __tablename__ = "intervention_templates"

    template_id = Column(String(100), nullable=False, unique=True, index=True)
    intent_type = Column(String(50), nullable=False, index=True)
    support_level = Column(Integer, nullable=False)
    variants = Column(JSON, nullable=False)
    meta = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
