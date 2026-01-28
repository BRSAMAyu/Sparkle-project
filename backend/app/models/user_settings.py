from sqlalchemy import Column, Integer, ForeignKey, Index, Boolean, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class UserSettings(BaseModel):
    __tablename__ = "user_settings"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    transparency_level = Column(Integer, nullable=False, default=0)
    system_update_level = Column(Integer, nullable=False, default=1)

    # Task reminder settings
    task_reminders_enabled = Column(Boolean, nullable=False, default=True)
    task_reminder_times = Column(JSON, nullable=True)  # List of integers (minutes before due)

    user = relationship("User", backref="user_settings")


Index("idx_user_settings_user", UserSettings.user_id, unique=True)
