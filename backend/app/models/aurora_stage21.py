from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UserSkill(BaseModel):
    __tablename__ = "user_skills"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    forked_from_share_id = Column(GUID(), nullable=True, index=True)
    shared_catalog_id = Column(GUID(), nullable=True, index=True)
    name = Column(String(40), nullable=False)
    pattern_template = Column(String(4000), nullable=False)
    activation_conditions = Column(JSONBCompat, nullable=False, default=list)
    examples = Column(JSONBCompat, nullable=False, default=list)
    privacy_level = Column(String(16), nullable=False, default="private")
    usage_count = Column(Integer, nullable=False, default=0)
    last_activated_at = Column(DateTime, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    forked_at = Column(DateTime, nullable=True)
    schema_version = Column(String(16), nullable=False, default="skill.v1")

    user = relationship("User", backref="user_skills")


Index("idx_user_skills_user_active", UserSkill.user_id, UserSkill.active)
Index("idx_user_skills_user_updated", UserSkill.user_id, UserSkill.updated_at)


class SharedSkill(BaseModel):
    __tablename__ = "shared_skills"

    share_slug = Column(String(80), nullable=False, unique=True, index=True)
    name = Column(String(40), nullable=False)
    pattern_template = Column(String(4000), nullable=False)
    activation_conditions = Column(JSONBCompat, nullable=False, default=list)
    examples = Column(JSONBCompat, nullable=False, default=list)
    author_label = Column(String(32), nullable=False, default="anonymous")
    published_at = Column(DateTime, nullable=False)
    source_schema_version = Column(String(16), nullable=False, default="skill.v1")


Index("idx_shared_skills_published", SharedSkill.published_at)


class SkillShareModerationQueue(BaseModel):
    __tablename__ = "skill_share_moderation_queue"

    owner_user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    user_skill_id = Column(GUID(), nullable=False, index=True)
    staged_name = Column(String(40), nullable=False)
    staged_pattern_template = Column(String(4000), nullable=False)
    staged_activation_conditions = Column(JSONBCompat, nullable=False, default=list)
    staged_examples = Column(JSONBCompat, nullable=False, default=list)
    pii_scan_reasons = Column(JSONBCompat, nullable=False, default=list)
    injection_scan_reasons = Column(JSONBCompat, nullable=False, default=list)
    moderation_status = Column(String(32), nullable=False, default="pending")
    reviewer_label = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    published_shared_skill_id = Column(GUID(), nullable=True)
    rejection_reason = Column(String(512), nullable=True)

    owner = relationship("User", backref="skill_share_queue")


Index(
    "idx_skill_share_queue_owner_created",
    SkillShareModerationQueue.owner_user_id,
    SkillShareModerationQueue.created_at,
)
