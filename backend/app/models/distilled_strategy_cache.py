"""Durable L2 cache entries for continuous-learning distilled strategies."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB

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

    id = Column(GUID(), primary_key=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    applicability_scope = Column(Text, nullable=False)
    status = Column(String(64), nullable=False, index=True)
    shareability = Column(String(64), nullable=False, index=True)
    source_trajectory_type = Column(String(128), nullable=False, index=True)
    payload = Column(JSONBCompat, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, index=True)


Index(
    "ix_distilled_strategy_cache_status_source",
    DistilledStrategyCacheEntry.status,
    DistilledStrategyCacheEntry.source_trajectory_type,
)
