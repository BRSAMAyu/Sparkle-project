from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class PushDeliveryRecord(BaseModel):
    __tablename__ = "push_delivery_records"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    notification_id = Column(GUID(), ForeignKey("notifications.id"), nullable=True, index=True)
    policy_id = Column(String(64), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    message_template_id = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(String(1000), nullable=False)
    evidence_token = Column(String(255), nullable=False, index=True)
    delivery_channel = Column(String(32), nullable=False, default="websocket")
    status = Column(String(32), nullable=False, default="sent", index=True)
    scheduled_send_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    acted_at = Column(DateTime, nullable=True)
    retracted_at = Column(DateTime, nullable=True)
    retractable_until = Column(DateTime, nullable=True)
    category_disabled = Column(Boolean, nullable=False, default=False)
    metadata_payload = Column(JSONBCompat, nullable=False, default=dict)

    user = relationship("User", backref="push_delivery_records")
    notification = relationship("Notification", backref="push_delivery_records")


Index("idx_push_delivery_user_sent", PushDeliveryRecord.user_id, PushDeliveryRecord.sent_at)
Index("idx_push_delivery_user_category", PushDeliveryRecord.user_id, PushDeliveryRecord.category)

