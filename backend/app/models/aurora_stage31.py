from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class DailyBehaviorVector(BaseModel):
    __tablename__ = "daily_behavior_vector"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vector_date = Column(Date, nullable=False)
    dims_payload = Column(JSONBCompat, nullable=False, default=dict)
    active_event_count = Column(Integer, nullable=False, default=0)
    stage30_dim_count = Column(Integer, nullable=False, default=0)
    silent_window_cut = Column(Boolean, nullable=False, default=False)

    user = relationship("User", backref="daily_behavior_vectors")


Index("idx_daily_behavior_vector_user_date", DailyBehaviorVector.user_id, DailyBehaviorVector.vector_date, unique=True)
Index("idx_daily_behavior_vector_user_active", DailyBehaviorVector.user_id, DailyBehaviorVector.active_event_count)


class IdiographicAssociation(BaseModel):
    __tablename__ = "idiographic_associations"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dim_a = Column(String(64), nullable=False)
    dim_b = Column(String(64), nullable=False)
    dim_pair = Column(String(128), nullable=False)
    direction = Column(String(24), nullable=False, default="positive_sync")
    correlation = Column(Float, nullable=False, default=0.0)
    p_value_raw = Column(Float, nullable=False, default=1.0)
    p_value_bh = Column(Float, nullable=False, default=1.0)
    sample_days = Column(Integer, nullable=False, default=0)
    active_days = Column(Integer, nullable=False, default=0)
    rank_pair_count = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False, default=0.0)
    density_insufficient = Column(Boolean, nullable=False, default=True)
    visible = Column(Boolean, nullable=False, default=False)
    path_mode = Column(String(16), nullable=False, default="B")
    window_start = Column(Date, nullable=True)
    window_end = Column(Date, nullable=True)
    disclaimer_text = Column(String(255), nullable=False, default="")
    rendered_text = Column(String(2000), nullable=False, default="")
    user_disconfirmed = Column(Boolean, nullable=False, default=False)
    user_disconfirmed_until = Column(DateTime, nullable=True)

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

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dim = Column(String(64), nullable=False)
    change_date = Column(Date, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    path_mode = Column(String(16), nullable=False, default="B")
    rendered_text = Column(String(1000), nullable=False, default="")
    window_start = Column(Date, nullable=True)
    window_end = Column(Date, nullable=True)

    user = relationship("User", backref="idiographic_changepoints")


Index(
    "idx_idiographic_changepoints_user_dim_date",
    IdiographicChangepoint.user_id,
    IdiographicChangepoint.dim,
    IdiographicChangepoint.change_date,
    unique=True,
)
