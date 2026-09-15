"""Persisted marketplace assets and adoption audit records."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class MarketplaceSkill(BaseModel):
    __tablename__ = "marketplace_skills"

    skill_id = Column(String(64), nullable=False, unique=True, index=True)
    source_skill_id = Column(String(128), nullable=True, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False, default="")
    goal_type = Column(String(64), nullable=False, default="")
    domain = Column(String(96), nullable=False, index=True, default="")
    author_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, index=True, default="draft")

    trigger_condition = Column(Text, nullable=False, default="")
    action_template = Column(Text, nullable=False, default="")
    expected_outcome = Column(Text, nullable=False, default="")
    prerequisites = Column(JSONBCompat, nullable=False, default=list)
    contraindications = Column(JSONBCompat, nullable=False, default=list)
    context_signatures = Column(JSONBCompat, nullable=False, default=list)

    evidence_grade = Column(Integer, nullable=False, default=0, index=True)
    evidence_summary = Column(Text, nullable=False, default="")
    episode_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=0.0)
    negative_feedback_rate = Column(Float, nullable=False, default=0.0)
    revoke_rate = Column(Float, nullable=False, default=0.0)
    adoption_count = Column(Integer, nullable=False, default=0)

    privacy_report = Column(JSONBCompat, nullable=False, default=dict)
    governance = Column(JSONBCompat, nullable=False, default=dict)
    previous_versions = Column(JSONBCompat, nullable=False, default=list)
    rollback_of_id = Column(GUID(), ForeignKey("marketplace_skills.id", ondelete="SET NULL"), nullable=True)
    auto_deprecation_reason = Column(String(128), nullable=True)
    listed_at = Column(DateTime, nullable=True)
    deprecated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_marketplace_skills_status_domain", "status", "domain"),
        Index("ix_marketplace_skills_quality", "status", "quality_score"),
    )


class MarketplacePack(BaseModel):
    __tablename__ = "marketplace_packs"

    pack_id = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False, default="")
    domain = Column(String(96), nullable=False, index=True, default="")
    version = Column(Integer, nullable=False, default=1)
    source = Column(String(128), nullable=False, default="system")
    status = Column(String(32), nullable=False, index=True, default="draft")

    node_schema = Column(JSONBCompat, nullable=False, default=dict)
    task_templates = Column(JSONBCompat, nullable=False, default=list)
    risk_rules = Column(JSONBCompat, nullable=False, default=list)
    skill_ids = Column(JSONBCompat, nullable=False, default=list)
    quality_evidence = Column(JSONBCompat, nullable=False, default=dict)
    quality_score = Column(Float, nullable=False, default=0.0)
    negative_feedback_rate = Column(Float, nullable=False, default=0.0)
    revoke_rate = Column(Float, nullable=False, default=0.0)
    adoption_count = Column(Integer, nullable=False, default=0)

    privacy_report = Column(JSONBCompat, nullable=False, default=dict)
    governance = Column(JSONBCompat, nullable=False, default=dict)
    previous_versions = Column(JSONBCompat, nullable=False, default=list)
    rollback_of_id = Column(GUID(), ForeignKey("marketplace_packs.id", ondelete="SET NULL"), nullable=True)
    auto_deprecation_reason = Column(String(128), nullable=True)
    listed_at = Column(DateTime, nullable=True)
    deprecated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_marketplace_packs_status_domain", "status", "domain"),
        Index("ix_marketplace_packs_quality", "status", "quality_score"),
    )


class UserSkillAdoption(BaseModel):
    __tablename__ = "user_skill_adoptions"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    asset_type = Column(String(24), nullable=False, index=True)
    asset_version = Column(Integer, nullable=False, default=1)
    status = Column(String(24), nullable=False, index=True, default="active")
    explicit_confirm = Column(Boolean, nullable=False, default=False)
    context_signature = Column(JSONBCompat, nullable=False, default=dict)
    preview_snapshot = Column(JSONBCompat, nullable=False, default=dict)
    trace_id = Column(String(128), nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(256), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "asset_type", "asset_id", name="uq_user_marketplace_asset_adoption"),
        Index("ix_user_skill_adoptions_user_asset", "user_id", "asset_type", "asset_id"),
    )


class PackAdoptionHistory(BaseModel):
    __tablename__ = "pack_adoption_history"

    adoption_id = Column(GUID(), ForeignKey("user_skill_adoptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    asset_type = Column(String(24), nullable=False, index=True)
    trace_id = Column(String(128), nullable=False, index=True)
    impact_type = Column(String(32), nullable=False, index=True)
    impact_summary = Column(Text, nullable=False, default="")
    target_id = Column(String(128), nullable=True)
    before_snapshot = Column(JSONBCompat, nullable=False, default=dict)
    after_snapshot = Column(JSONBCompat, nullable=False, default=dict)
    outcome = Column(String(32), nullable=False, index=True, default="pending")
    metadata_json = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_pack_adoption_history_asset_trace", "asset_type", "asset_id", "trace_id"),
        Index("ix_pack_adoption_history_user_created", "user_id", "created_at"),
    )
