"""Persisted intervention strategy learning outcomes for Phase 3."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionTriggerType,
    _string_enum,
)

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class InterventionStrategyOutcome(BaseModel):
    __tablename__ = "intervention_strategy_outcomes"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    intervention_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("intervention_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[Any] = mapped_column(
        _string_enum(InterventionTriggerType, "intervention_trigger_enum"),
        nullable=False,
        index=True,
    )
    delivery_tone: Mapped[Any] = mapped_column(
        _string_enum(DeliveryStrategy, "delivery_strategy_enum"),
        nullable=False,
        index=True,
    )
    delivery_channel: Mapped[Any] = mapped_column(
        _string_enum(DeliveryChannel, "delivery_channel_enum"),
        nullable=False,
    )
    acceptance_status: Mapped[Any] = mapped_column(
        _string_enum(InterventionAcceptanceStatus, "intervention_acceptance_enum"),
        nullable=False,
    )
    outcome: Mapped[Any] = mapped_column(
        _string_enum(InterventionOutcomeStatus, "intervention_outcome_enum"),
        nullable=False,
        index=True,
    )
    time_to_action_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, server_default="{}")

    __table_args__ = (
        UniqueConstraint("intervention_id", name="uq_strategy_outcome_intervention"),
        Index("ix_strategy_outcomes_user_trigger", "user_id", "trigger_type"),
        Index("ix_strategy_outcomes_user_trigger_tone", "user_id", "trigger_type", "delivery_tone"),
    )
