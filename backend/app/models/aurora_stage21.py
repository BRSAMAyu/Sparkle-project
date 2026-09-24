from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UserSkill(BaseModel):
    __tablename__ = "user_skills"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    forked_from_share_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)
    shared_catalog_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    pattern_template: Mapped[str] = mapped_column(String(4000), nullable=False)
    activation_conditions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    examples: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    privacy_level: Mapped[str] = mapped_column(String(16), nullable=False, default="private")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    forked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="skill.v1")

    user = relationship("User", backref="user_skills")


Index("idx_user_skills_user_active", UserSkill.user_id, UserSkill.active)
Index("idx_user_skills_user_updated", UserSkill.user_id, UserSkill.updated_at)


class SharedSkill(BaseModel):
    __tablename__ = "shared_skills"

    share_slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    pattern_template: Mapped[str] = mapped_column(String(4000), nullable=False)
    activation_conditions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    examples: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    author_label: Mapped[str] = mapped_column(String(32), nullable=False, default="anonymous")
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source_schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="skill.v1")


Index("idx_shared_skills_published", SharedSkill.published_at)


class SkillShareModerationQueue(BaseModel):
    __tablename__ = "skill_share_moderation_queue"

    owner_user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    user_skill_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    staged_name: Mapped[str] = mapped_column(String(40), nullable=False)
    staged_pattern_template: Mapped[str] = mapped_column(String(4000), nullable=False)
    staged_activation_conditions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    staged_examples: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    pii_scan_reasons: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    injection_scan_reasons: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    moderation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reviewer_label: Mapped[str] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    published_shared_skill_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(String(512), nullable=True)

    owner = relationship("User", backref="skill_share_queue")


Index(
    "idx_skill_share_queue_owner_created",
    SkillShareModerationQueue.owner_user_id,
    SkillShareModerationQueue.created_at,
)
