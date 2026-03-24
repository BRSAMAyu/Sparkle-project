from __future__ import annotations

import enum

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class CustomExpertSource(str, enum.Enum):
    OFFICIAL_DERIVED = "official_derived"
    USER_DEFINED = "user_defined"


class CustomExpertProfile(BaseModel):
    __tablename__ = "custom_expert_profiles"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    system_prompt = Column(Text, nullable=False)
    base_expert_id = Column(String(100), nullable=True, index=True)
    preferred_model_key = Column(String(100), nullable=True, index=True)
    preferred_model_tier = Column(String(40), nullable=True, index=True)
    reasoning_mode = Column(String(40), nullable=False, default="balanced")
    source = Column(String(40), nullable=False, default=CustomExpertSource.USER_DEFINED.value)
    metadata_json = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)

    user = relationship("User")

    __table_args__ = (
        Index("idx_custom_expert_profiles_user_enabled", "user_id", "is_enabled"),
    )


class CustomExpertTeam(BaseModel):
    __tablename__ = "custom_expert_teams"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    collaboration_mode = Column(String(40), nullable=False, default="auto")
    expert_ids = Column(JSON, nullable=False, default=list)
    answer_expert_ids = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)

    user = relationship("User")

    __table_args__ = (
        Index("idx_custom_expert_teams_user_enabled", "user_id", "is_enabled"),
    )
