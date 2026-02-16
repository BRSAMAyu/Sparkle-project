"""
Seed Template Models
种子模板 2.0 数据模型
"""
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TemplatePackScenario(str, Enum):
    STUDY_PLAN = "study_plan"
    DEEP_ANALYSIS = "deep_analysis"
    WRITING = "writing"


class TemplateVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    OFFICIAL = "official"


class TemplatePackStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class TemplateVersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TemplatePromotionState(str, Enum):
    NONE = "none"
    PUBLIC_CANDIDATE = "public_candidate"
    PUBLIC_RECOMMENDED = "public_recommended"
    BLOCKED = "blocked"


class TemplateSignalType(str, Enum):
    LIKE = "like"
    SAVE = "save"
    REUSE = "reuse"
    REPORT = "report"
    DOWNVOTE = "downvote"
    ADOPT_SUCCESS = "adopt_success"


class SeedTemplatePack(BaseModel):
    __tablename__ = "seed_template_packs"

    scenario_type = Column(String(40), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    visibility = Column(String(20), nullable=False, default=TemplateVisibility.PRIVATE.value, index=True)
    status = Column(String(20), nullable=False, default=TemplatePackStatus.DRAFT.value, index=True)
    language = Column(String(10), nullable=False, default="zh")
    tags = Column(JSONBCompat, nullable=True)
    extra_metadata = Column(JSONBCompat, nullable=True)
    quality_score = Column(Float, nullable=True)
    adoption_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)

    templates = relationship("SeedTemplate", back_populates="pack", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_seed_template_pack_scene_visibility", "scenario_type", "visibility"),
    )


class SeedTemplate(BaseModel):
    __tablename__ = "seed_templates"

    pack_id = Column(GUID(), ForeignKey("seed_template_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(240), nullable=False, index=True)
    template_role = Column(String(64), nullable=False, default="default", index=True)
    current_version_id = Column(GUID(), nullable=True, index=True)
    forked_from_template_id = Column(GUID(), nullable=True, index=True)
    forked_from_version_id = Column(GUID(), nullable=True, index=True)
    owner_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_official = Column(Boolean, nullable=False, default=False, index=True)
    is_featured = Column(Boolean, nullable=False, default=False, index=True)

    pack = relationship("SeedTemplatePack", back_populates="templates")
    versions = relationship("SeedTemplateVersion", back_populates="template", cascade="all, delete-orphan")
    subscriptions = relationship("SeedTemplateSubscription", back_populates="template", cascade="all, delete-orphan")


class SeedTemplateVersion(BaseModel):
    __tablename__ = "seed_template_versions"

    template_id = Column(GUID(), ForeignKey("seed_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default=TemplateVersionStatus.DRAFT.value, index=True)
    body = Column(Text, nullable=False)
    schema_json = Column(JSONBCompat, nullable=True)
    variables_schema = Column(JSONBCompat, nullable=True)
    change_log = Column(Text, nullable=True)
    quality_gate_report = Column(JSONBCompat, nullable=True)
    moderation_report = Column(JSONBCompat, nullable=True)
    moderation_status = Column(String(20), nullable=False, default="pending", index=True)
    promotion_state = Column(String(30), nullable=False, default=TemplatePromotionState.NONE.value, index=True)
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    published_at = Column(DateTime, nullable=True)

    template = relationship("SeedTemplate", back_populates="versions")
    signals = relationship("SeedTemplateSignal", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_seed_template_version_template_version", "template_id", "version_no"),
    )


class SeedTemplateSignal(BaseModel):
    __tablename__ = "seed_template_signals"

    template_version_id = Column(
        GUID(),
        ForeignKey("seed_template_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_type = Column(String(32), nullable=False, index=True)
    score = Column(Float, nullable=False, default=1.0)
    meta = Column(JSONBCompat, nullable=True)

    version = relationship("SeedTemplateVersion", back_populates="signals")

    __table_args__ = (
        Index("idx_seed_template_signal_version_type", "template_version_id", "signal_type"),
    )


class SeedTemplateSubscription(BaseModel):
    __tablename__ = "seed_template_subscriptions"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(GUID(), ForeignKey("seed_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    priority = Column(Integer, nullable=False, default=0)

    template = relationship("SeedTemplate", back_populates="subscriptions")

    __table_args__ = (
        Index("idx_seed_template_subscription_user_template", "user_id", "template_id"),
    )


class SeedTemplateRewardLedger(BaseModel):
    __tablename__ = "seed_template_rewards_ledger"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(GUID(), ForeignKey("seed_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(40), nullable=False, index=True)
    points_delta = Column(Integer, nullable=False, default=0)
    source_signal = Column(String(40), nullable=True)
    extra_metadata = Column(JSONBCompat, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=_utcnow)

