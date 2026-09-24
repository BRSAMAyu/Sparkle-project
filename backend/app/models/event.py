"""
Tracking Event Models
Phase 1 unified event schema.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class TrackingEvent(BaseModel):
    __tablename__ = "tracking_events"

    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    ts_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entities: Mapped[Any] = mapped_column(JSON, nullable=True)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", backref="tracking_events")
