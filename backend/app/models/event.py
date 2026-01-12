"""
Tracking Event Models
Phase 1 unified event schema.
"""
from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class TrackingEvent(BaseModel):
    __tablename__ = "tracking_events"

    event_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(120), nullable=False, index=True)
    schema_version = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    ts_ms = Column(BigInteger, nullable=False, index=True)
    entities = Column(JSON, nullable=True)
    payload = Column(JSON, nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", backref="tracking_events")
