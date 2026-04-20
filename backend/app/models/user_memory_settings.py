from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UserMemorySettings(BaseModel):
    __tablename__ = "user_memory_settings"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    allow_preferences = Column(Boolean, nullable=False, default=True)
    allow_goals = Column(Boolean, nullable=False, default=True)
    allow_episodic = Column(Boolean, nullable=False, default=True)
    allow_inferred_episodic = Column(Boolean, nullable=False, default=True)
    capture_level = Column(String(20), nullable=False, default="medium")
    blocked_pref_keys = Column(JSONBCompat, nullable=False, default=list)
    blocked_sources = Column(JSONBCompat, nullable=False, default=list)

    user = relationship("User", backref="memory_settings")


Index("idx_user_memory_settings_user", UserMemorySettings.user_id, unique=True)
