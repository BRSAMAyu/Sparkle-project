from __future__ import annotations

from sqlalchemy import JSON, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel, GUID

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class EventBusDLQEntry(BaseModel):
    """Audit trail for failed EventBus deliveries."""

    __tablename__ = "event_bus_dlq"

    stream = Column(String(255), nullable=False, index=True)
    event_type = Column(String(255), nullable=False, index=True)
    user_id = Column(GUID(), nullable=True, index=True)
    group_name = Column(String(255), nullable=False, index=True)
    consumer_name = Column(String(255), nullable=False)
    message_id = Column(String(255), nullable=False, index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    failure_stage = Column(String(64), nullable=False, default="consume", index=True)
    error = Column(Text, nullable=False)
    payload = Column(JSONBCompat, nullable=False, default=dict)
