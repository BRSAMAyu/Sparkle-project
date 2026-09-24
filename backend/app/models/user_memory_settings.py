from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UserMemorySettings(BaseModel):
    __tablename__ = "user_memory_settings"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_preferences: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_goals: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_episodic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_inferred_episodic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capture_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    blocked_pref_keys: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    blocked_sources: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    # Memory V3 (M-01): per-user memory epoch. Bumped on destructive memory
    # changes (delete/revoke of records) so cache holders (M-07 context
    # compiler, semantic cache) and in-flight runs (C-07) can detect that
    # previously compiled memory context is stale. Monotonic; 1 = no bump yet.
    memory_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    memory_epoch_bumped_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    memory_epoch_reason: Mapped[str] = mapped_column(String(200), nullable=True)

    user = relationship("User", backref="memory_settings")


Index("idx_user_memory_settings_user", UserMemorySettings.user_id, unique=True)
