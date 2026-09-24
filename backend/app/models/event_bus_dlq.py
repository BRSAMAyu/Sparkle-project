from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class EventBusDLQEntry(BaseModel):
    """Audit trail for failed EventBus deliveries."""

    __tablename__ = "event_bus_dlq"

    stream: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    consumer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="consume", index=True)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
