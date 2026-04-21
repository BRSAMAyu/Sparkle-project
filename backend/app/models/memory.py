"""
Memory models for long-term memory storage.
"""
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")


class MemoryPreference(BaseModel):
    __tablename__ = "memory_preferences"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    pref_key = Column(String(80), nullable=False)
    pref_value = Column(JSONBCompat, nullable=False)
    version = Column(Integer, nullable=False)
    replaced_by_id = Column(GUID(), nullable=True)
    confidence = Column(Float, nullable=True)
    evidence_score = Column(Float, nullable=False, default=0.0)
    correction_count = Column(Integer, nullable=False, default=0)
    evidence_refs = Column(JSONBCompat, nullable=False, default=list)
    evidence_missing = Column(Boolean, default=False, nullable=False)
    evidence_checked_at = Column(DateTime, nullable=True)
    last_consumed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    retracted_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="memory_preferences")


Index("idx_memory_preferences_user_pref", MemoryPreference.user_id, MemoryPreference.pref_key)
Index("uq_memory_preferences_version", MemoryPreference.user_id, MemoryPreference.pref_key, MemoryPreference.version, unique=True)
Index("idx_memory_preferences_evidence_missing", MemoryPreference.evidence_missing)
Index("idx_memory_preferences_evidence_score", MemoryPreference.evidence_score)
Index("idx_memory_preferences_last_consumed_at", MemoryPreference.last_consumed_at)
Index("idx_memory_preferences_archived_at", MemoryPreference.archived_at)


class MemoryGoal(BaseModel):
    __tablename__ = "memory_goals"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False)
    target_date = Column(Date, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    linked_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)
    linked_plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=True)
    evidence_score = Column(Float, nullable=False, default=0.0)
    correction_count = Column(Integer, nullable=False, default=0)
    evidence_refs = Column(JSONBCompat, nullable=False, default=list)
    metadata_payload = Column("metadata", JSONBCompat, nullable=True)
    evidence_missing = Column(Boolean, default=False, nullable=False)
    evidence_checked_at = Column(DateTime, nullable=True)
    last_consumed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    retracted_at = Column(DateTime, nullable=True)

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

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    summary = Column(String(2000), nullable=False)
    source_type = Column(String(30), nullable=False)
    source_id = Column(String(100), nullable=True)
    source_lane = Column(String(40), nullable=False, default="direct_capture")
    subject_type = Column(String(32), nullable=False, default="self")
    occurred_at = Column(DateTime, nullable=False)
    due_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    importance_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    evidence_score = Column(Float, nullable=False, default=0.0)
    correction_count = Column(Integer, nullable=False, default=0)
    evidence_token = Column(String(128), nullable=True)
    decay_policy = Column(String(32), nullable=True)
    semantic_key = Column(String(64), nullable=True)
    mentioned_entity_hash = Column(String(64), nullable=True)
    mentioned_entity_owner_user_id = Column(GUID(), nullable=True)
    tags = Column(JSONBCompat, nullable=True)
    evidence_refs = Column(JSONBCompat, nullable=False, default=list)
    evidence_missing = Column(Boolean, default=False, nullable=False)
    evidence_checked_at = Column(DateTime, nullable=True)
    evidence_snapshot = Column(JSONBCompat, nullable=True)
    last_consumed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    retracted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    embedding = Column(VectorCompat, nullable=True)

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


class Scene(BaseModel):
    __tablename__ = "scenes"

    scene_id = Column(String(80), nullable=False, unique=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(String(200), nullable=False)
    member_memory_ids = Column(JSONBCompat, nullable=False, default=list)
    centroid_embedding = Column(VectorCompat, nullable=True)
    time_start = Column(DateTime, nullable=False)
    time_end = Column(DateTime, nullable=False)
    quality_score = Column(Float, nullable=False, default=0.0)
    version = Column(String(32), nullable=False, default="scene.v1")

    user = relationship("User", backref="scenes")


Index("idx_scenes_user_time_window", Scene.user_id, Scene.time_start, Scene.time_end)
Index("idx_scenes_user_quality", Scene.user_id, Scene.quality_score)
Index("idx_scenes_user_version", Scene.user_id, Scene.version)


class MemoryCorrection(BaseModel):
    __tablename__ = "memory_corrections"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    memory_type = Column(String(30), nullable=False)
    memory_id = Column(GUID(), nullable=False)
    action = Column(String(40), nullable=False)
    reason = Column(String(500), nullable=True)

    user = relationship("User", backref="memory_corrections")


Index(
    "idx_memory_corrections_user_type_created",
    MemoryCorrection.user_id,
    MemoryCorrection.memory_type,
    MemoryCorrection.created_at,
)
