"""Durable L2 cache entries for continuous-learning distilled strategies."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, Base

try:
    from sqlalchemy import JSON

    JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
except ImportError:
    from sqlalchemy import JSON

    JSONBCompat = JSON()


class DistilledStrategyCacheEntry(Base):
    """Persisted L2 inference-cache record for a distilled strategy."""

    __tablename__ = "distilled_strategy_cache"

    id: Mapped[Any] = mapped_column(GUID(), primary_key=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    applicability_scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    shareability: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_trajectory_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


Index(
    "ix_distilled_strategy_cache_status_source",
    DistilledStrategyCacheEntry.status,
    DistilledStrategyCacheEntry.source_trajectory_type,
)
