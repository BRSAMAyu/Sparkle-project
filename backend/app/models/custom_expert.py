from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class CustomExpertSource(enum.StrEnum):
    OFFICIAL_DERIVED = "official_derived"
    USER_DEFINED = "user_defined"


class CustomExpertProfile(BaseModel):
    __tablename__ = "custom_expert_profiles"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    base_expert_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    preferred_model_key: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    preferred_model_tier: Mapped[str] = mapped_column(String(40), nullable=True, index=True)
    reasoning_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="balanced")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default=CustomExpertSource.USER_DEFINED.value)
    metadata_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user = relationship("User")

    __table_args__ = (
        Index("idx_custom_expert_profiles_user_enabled", "user_id", "is_enabled"),
    )


class CustomExpertTeam(BaseModel):
    __tablename__ = "custom_expert_teams"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    collaboration_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="auto")
    expert_ids: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    answer_expert_ids: Mapped[Any] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user = relationship("User")

    __table_args__ = (
        Index("idx_custom_expert_teams_user_enabled", "user_id", "is_enabled"),
    )
