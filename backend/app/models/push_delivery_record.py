from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class PushDeliveryRecord(BaseModel):
    __tablename__ = "push_delivery_records"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    notification_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("notifications.id"), nullable=True, index=True)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    evidence_token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    delivery_channel: Mapped[str] = mapped_column(String(32), nullable=False, default="websocket")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="sent", index=True)
    scheduled_send_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retractable_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    category_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)

    user = relationship("User", backref="push_delivery_records")
    notification = relationship("Notification", backref="push_delivery_records")


Index("idx_push_delivery_user_sent", PushDeliveryRecord.user_id, PushDeliveryRecord.sent_at)
Index("idx_push_delivery_user_category", PushDeliveryRecord.user_id, PushDeliveryRecord.category)

