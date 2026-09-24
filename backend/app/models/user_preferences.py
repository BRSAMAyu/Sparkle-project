"""
用户偏好中心 - Single Source of Truth
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UserPreferencesCenter(BaseModel):
    """统一用户偏好中心"""

    __tablename__ = "user_preferences_center"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    explicit: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    inferred: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    traits_prior: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    trait_observation_state: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)

    last_explicit_update: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_inferred_update: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    traits_coldstart_completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def increment_version(self) -> int:
        self.version += 1
        return self.version
