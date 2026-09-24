"""
Memory models for long-term memory storage.
"""

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")


class MemoryPreference(BaseModel):
    __tablename__ = "memory_preferences"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    pref_key: Mapped[str] = mapped_column(String(80), nullable=False)
    pref_value: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    replaced_by_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_refs: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    evidence_missing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_consumed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", backref="memory_preferences")


Index("idx_memory_preferences_user_pref", MemoryPreference.user_id, MemoryPreference.pref_key)
Index(
    "uq_memory_preferences_version",
    MemoryPreference.user_id,
    MemoryPreference.pref_key,
    MemoryPreference.version,
    unique=True,
)
Index("idx_memory_preferences_evidence_missing", MemoryPreference.evidence_missing)
Index("idx_memory_preferences_evidence_score", MemoryPreference.evidence_score)
Index("idx_memory_preferences_last_consumed_at", MemoryPreference.last_consumed_at)
Index("idx_memory_preferences_archived_at", MemoryPreference.archived_at)


class MemoryGoal(BaseModel):
    __tablename__ = "memory_goals"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    linked_task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)
    linked_plan_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("plans.id"), nullable=True)
    # M-08 R2 P2-2：goal 真实写入来源（与 episodic/preferences 域同构的溯源面）。
    # NULL = 既有行/用户公共创建路径（创建动作本身即用户陈述）；"event" 等系统
    # 捕获值由写入方（plan_review_service 等）传入，provenance 面据此分流
    # 「系统写入」桶标签并降置信档——推断/捕获永不报「已确认」（M-01 对外口径）。
    # 迁移：alembic/versions/m08_20260920_add_memory_goals_source_type.py
    source_type: Mapped[str] = mapped_column(String(30), nullable=True)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_refs: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    metadata_payload: Mapped[Any] = mapped_column("metadata", JSONBCompat, nullable=True)
    evidence_missing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_consumed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", backref="memory_goals")
    linked_task = relationship("Task")
    linked_plan = relationship("Plan")


Index("idx_memory_goals_user_status_target", MemoryGoal.user_id, MemoryGoal.status, MemoryGoal.target_date)
Index("idx_memory_goals_expires_at", MemoryGoal.expires_at)
Index("idx_memory_goals_evidence_missing", MemoryGoal.evidence_missing)
Index("idx_memory_goals_evidence_score", MemoryGoal.evidence_score)
Index("idx_memory_goals_last_consumed_at", MemoryGoal.last_consumed_at)
Index("idx_memory_goals_archived_at", MemoryGoal.archived_at)


class EpisodicMemory(BaseModel):
    __tablename__ = "episodic_memories"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=True)
    source_lane: Mapped[str] = mapped_column(String(40), nullable=False, default="direct_capture")
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, default="self")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_token: Mapped[str] = mapped_column(String(128), nullable=True)
    decay_policy: Mapped[str] = mapped_column(String(32), nullable=True)
    semantic_key: Mapped[str] = mapped_column(String(64), nullable=True)
    mentioned_entity_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    mentioned_entity_owner_user_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    tags: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    evidence_refs: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    evidence_missing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    evidence_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    last_consumed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # Memory V3 (M-01): epistemic class of the record. NULL = derive from
    # source_lane (explicit lanes -> FACT, everything else -> HYPOTHESIS);
    # OBSERVATION / EXPERIENCE are set explicitly by future writers
    # (outcome adapters / M-06 experience projection).
    epistemic_class: Mapped[str] = mapped_column(String(24), nullable=True)
    # Memory V3 (M-01): winner of a conflict resolution that replaced this
    # record —— episodic counterpart of memory_preferences.replaced_by_id.
    superseded_by_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    embedding: Mapped[Any] = mapped_column(VectorCompat, nullable=True)

    user = relationship("User", backref="episodic_memories")


Index("idx_episodic_memories_user_occurred", EpisodicMemory.user_id, EpisodicMemory.occurred_at)
Index("idx_episodic_memories_source_lane", EpisodicMemory.user_id, EpisodicMemory.source_lane)
Index("idx_episodic_memories_subject_type", EpisodicMemory.user_id, EpisodicMemory.subject_type)
Index("idx_episodic_memories_due_at", EpisodicMemory.user_id, EpisodicMemory.due_at)
Index("idx_episodic_memories_evidence_token", EpisodicMemory.user_id, EpisodicMemory.evidence_token)
Index("idx_episodic_memories_semantic_key", EpisodicMemory.user_id, EpisodicMemory.semantic_key)
Index("idx_episodic_memories_evidence_missing", EpisodicMemory.evidence_missing)
Index("idx_episodic_memories_evidence_score", EpisodicMemory.evidence_score)
Index("idx_episodic_memories_last_consumed_at", EpisodicMemory.last_consumed_at)
Index("idx_episodic_memories_archived_at", EpisodicMemory.archived_at)
Index("idx_episodic_memories_epistemic_class", EpisodicMemory.user_id, EpisodicMemory.epistemic_class)
Index("idx_episodic_memories_superseded_by_id", EpisodicMemory.superseded_by_id)


class Scene(BaseModel):
    __tablename__ = "scenes"

    scene_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(200), nullable=False)
    member_memory_ids: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    centroid_embedding: Mapped[Any] = mapped_column(VectorCompat, nullable=True)
    time_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    time_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="scene.v1")

    user = relationship("User", backref="scenes")


Index("idx_scenes_user_time_window", Scene.user_id, Scene.time_start, Scene.time_end)
Index("idx_scenes_user_quality", Scene.user_id, Scene.quality_score)
Index("idx_scenes_user_version", Scene.user_id, Scene.version)


class MemoryCorrection(BaseModel):
    __tablename__ = "memory_corrections"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(30), nullable=False)
    memory_id: Mapped[Any] = mapped_column(GUID(), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=True)

    user = relationship("User", backref="memory_corrections")


Index(
    "idx_memory_corrections_user_type_created",
    MemoryCorrection.user_id,
    MemoryCorrection.memory_type,
    MemoryCorrection.created_at,
)
