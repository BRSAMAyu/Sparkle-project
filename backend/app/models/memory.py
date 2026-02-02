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
    retracted_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="memory_preferences")


Index("idx_memory_preferences_user_pref", MemoryPreference.user_id, MemoryPreference.pref_key)
Index("uq_memory_preferences_version", MemoryPreference.user_id, MemoryPreference.pref_key, MemoryPreference.version, unique=True)
Index("idx_memory_preferences_evidence_missing", MemoryPreference.evidence_missing)
Index("idx_memory_preferences_evidence_score", MemoryPreference.evidence_score)


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
    retracted_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="memory_goals")
    linked_task = relationship("Task")
    linked_plan = relationship("Plan")


Index("idx_memory_goals_user_status_target", MemoryGoal.user_id, MemoryGoal.status, MemoryGoal.target_date)
Index("idx_memory_goals_expires_at", MemoryGoal.expires_at)
Index("idx_memory_goals_evidence_missing", MemoryGoal.evidence_missing)
Index("idx_memory_goals_evidence_score", MemoryGoal.evidence_score)


class EpisodicMemory(BaseModel):
    __tablename__ = "episodic_memories"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    summary = Column(String(2000), nullable=False)
    source_type = Column(String(30), nullable=False)
    source_id = Column(String(100), nullable=True)
    occurred_at = Column(DateTime, nullable=False)
    importance_score = Column(Float, nullable=True)
    evidence_score = Column(Float, nullable=False, default=0.0)
    correction_count = Column(Integer, nullable=False, default=0)
    tags = Column(JSONBCompat, nullable=True)
    evidence_refs = Column(JSONBCompat, nullable=False, default=list)
    evidence_missing = Column(Boolean, default=False, nullable=False)
    evidence_checked_at = Column(DateTime, nullable=True)
    evidence_snapshot = Column(JSONBCompat, nullable=True)
    retracted_at = Column(DateTime, nullable=True)
    embedding = Column(VectorCompat, nullable=True)

    user = relationship("User", backref="episodic_memories")


Index("idx_episodic_memories_user_occurred", EpisodicMemory.user_id, EpisodicMemory.occurred_at)
Index("idx_episodic_memories_evidence_missing", EpisodicMemory.evidence_missing)
Index("idx_episodic_memories_evidence_score", EpisodicMemory.evidence_score)


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
