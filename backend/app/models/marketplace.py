"""Persisted marketplace assets and adoption audit records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class MarketplaceSkill(BaseModel):
    __tablename__ = "marketplace_skills"

    skill_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source_skill_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    goal_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    domain: Mapped[str] = mapped_column(String(96), nullable=False, index=True, default="")
    author_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="draft")

    trigger_condition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prerequisites: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    contraindications: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    context_signatures: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)

    evidence_grade: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    episode_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negative_feedback_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revoke_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    adoption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    privacy_report: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    governance: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    previous_versions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    rollback_of_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("marketplace_skills.id", ondelete="SET NULL"), nullable=True)
    auto_deprecation_reason: Mapped[str] = mapped_column(String(128), nullable=True)
    listed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    deprecated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_marketplace_skills_status_domain", "status", "domain"),
        Index("ix_marketplace_skills_quality", "status", "quality_score"),
    )


class MarketplacePack(BaseModel):
    __tablename__ = "marketplace_packs"

    pack_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    domain: Mapped[str] = mapped_column(String(96), nullable=False, index=True, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="draft")

    node_schema: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    task_templates: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    risk_rules: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    skill_ids: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    quality_evidence: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negative_feedback_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revoke_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    adoption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    privacy_report: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    governance: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    previous_versions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    rollback_of_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("marketplace_packs.id", ondelete="SET NULL"), nullable=True)
    auto_deprecation_reason: Mapped[str] = mapped_column(String(128), nullable=True)
    listed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    deprecated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_marketplace_packs_status_domain", "status", "domain"),
        Index("ix_marketplace_packs_quality", "status", "quality_score"),
    )


class UserSkillAdoption(BaseModel):
    __tablename__ = "user_skill_adoptions"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    asset_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True, default="active")
    explicit_confirm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    context_signature: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    preview_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "asset_type", "asset_id", name="uq_user_marketplace_asset_adoption"),
        Index("ix_user_skill_adoptions_user_asset", "user_id", "asset_type", "asset_id"),
    )


class PackAdoptionHistory(BaseModel):
    __tablename__ = "pack_adoption_history"

    adoption_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("user_skill_adoptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    impact_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_id: Mapped[str] = mapped_column(String(128), nullable=True)
    before_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    after_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    metadata_json: Mapped[Any] = mapped_column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_pack_adoption_history_asset_trace", "asset_type", "asset_id", "trace_id"),
        Index("ix_pack_adoption_history_user_created", "user_id", "created_at"),
    )
