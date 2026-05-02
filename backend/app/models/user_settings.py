from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class UserSettings(BaseModel):
    __tablename__ = "user_settings"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    transparency_level = Column(Integer, nullable=False, default=0)
    system_update_level = Column(Integer, nullable=False, default=1)
    ai_reasoning_mode = Column(String(16), nullable=False, default="balanced")
    current_goal_id = Column(String(64), nullable=True)

    # Task reminder settings
    task_reminders_enabled = Column(Boolean, nullable=False, default=True)
    task_reminder_times = Column(JSON, nullable=True)  # List of integers (minutes before due)
    community_intelligence_enabled = Column(Boolean, nullable=False, default=True)
    # FV-02 SafeExperimentRegistry opt-out (set by user; bandit and shadow
    # exploration must skip this user when true)
    safe_experiments_opt_out = Column(Boolean, nullable=False, default=False)

    user = relationship("User", backref="user_settings")


Index("idx_user_settings_user", UserSettings.user_id, unique=True)
