from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class DailyBehaviorVector(BaseModel):
    __tablename__ = "daily_behavior_vector"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vector_date: Mapped[date] = mapped_column(Date, nullable=False)
    dims_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    active_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage30_dim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    silent_window_cut: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user = relationship("User", backref="daily_behavior_vectors")


Index("idx_daily_behavior_vector_user_date", DailyBehaviorVector.user_id, DailyBehaviorVector.vector_date, unique=True)
Index("idx_daily_behavior_vector_user_active", DailyBehaviorVector.user_id, DailyBehaviorVector.active_event_count)


class IdiographicAssociation(BaseModel):
    __tablename__ = "idiographic_associations"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dim_a: Mapped[str] = mapped_column(String(64), nullable=False)
    dim_b: Mapped[str] = mapped_column(String(64), nullable=False)
    dim_pair: Mapped[str] = mapped_column(String(128), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), nullable=False, default="positive_sync")
    correlation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p_value_raw: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    p_value_bh: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    sample_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank_pair_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    density_insufficient: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    path_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="B")
    window_start: Mapped[date] = mapped_column(Date, nullable=True)
    window_end: Mapped[date] = mapped_column(Date, nullable=True)
    disclaimer_text: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    rendered_text: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    user_disconfirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_disconfirmed_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", backref="idiographic_associations")


Index(
    "idx_idiographic_associations_user_pair",
    IdiographicAssociation.user_id,
    IdiographicAssociation.dim_pair,
    unique=True,
)
Index(
    "idx_idiographic_associations_user_visible",
    IdiographicAssociation.user_id,
    IdiographicAssociation.visible,
)


class IdiographicChangepoint(BaseModel):
    __tablename__ = "idiographic_changepoints"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dim: Mapped[str] = mapped_column(String(64), nullable=False)
    change_date: Mapped[date] = mapped_column(Date, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    path_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="B")
    rendered_text: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    window_start: Mapped[date] = mapped_column(Date, nullable=True)
    window_end: Mapped[date] = mapped_column(Date, nullable=True)

    user = relationship("User", backref="idiographic_changepoints")


Index(
    "idx_idiographic_changepoints_user_dim_date",
    IdiographicChangepoint.user_id,
    IdiographicChangepoint.dim,
    IdiographicChangepoint.change_date,
    unique=True,
)
