"""Persistent North Star product metric events."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class NorthStarMetricEvent(BaseModel):
    """One idempotent event feeding Sparkle's North Star metric dashboard."""

    __tablename__ = "north_star_metric_events"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="backend", index=True)

    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    numerator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    denominator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)

    user = relationship("User", backref="north_star_metric_events")
    plan = relationship("Plan", backref="north_star_metric_events")
    task = relationship("Task", backref="north_star_metric_events")

    __table_args__ = (
        UniqueConstraint("event_key", name="uq_north_star_metric_events_event_key"),
        Index("idx_north_star_metric_events_user_date", "user_id", "metric_date"),
        Index("idx_north_star_metric_events_type_date", "event_type", "metric_date"),
        Index("idx_north_star_metric_events_plan_type", "plan_id", "event_type"),
    )

