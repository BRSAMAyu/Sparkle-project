# AI-OPAQUE: notification interaction rows drive delivery/product analytics and are not stable prompt-safe semantics.
"""
Notification Interaction and Preference Models
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import GUID


class NotificationInteraction(Base):
    """
    Notification Interaction Model

    Tracks user interactions with both system notifications and intervention requests.
    """
    __tablename__ = "notification_interactions"

    id: Mapped[Any] = mapped_column(GUID(), primary_key=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="system or intervention")
    notification_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False, comment="viewed, clicked, dismissed")
    action_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    time_to_action: Mapped[int] = mapped_column(Integer, nullable=True, comment="Seconds from creation to action")

    # Relationship
    user = relationship("User", backref="notification_interactions")

    def __repr__(self):
        return f"<NotificationInteraction(user_id={self.user_id}, type={self.notification_type}, action={self.action_type})>"


class NotificationPreferences(Base):
    """
    User Notification Preferences

    Stores user-specific notification settings.
    Uses user_id as primary key (one-to-one with users table).
    """
    __tablename__ = "notification_preferences"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), primary_key=True, nullable=False)
    enable_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_interventions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disabled_types: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    notification_level: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(5), nullable=True, comment="HH:MM format")
    quiet_hours_end: Mapped[str] = mapped_column(String(5), nullable=True, comment="HH:MM format")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreferences(user_id={self.user_id}, level={self.notification_level})>"
