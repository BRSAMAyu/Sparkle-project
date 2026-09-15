from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class AccountabilityPolicy(BaseModel):
    __tablename__ = "accountability_policies"

    policy_id = Column(String(128), nullable=False, unique=True, index=True)
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commitment_id = Column(
        GUID(),
        ForeignKey("episodic_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_version = Column(String(32), nullable=False, default="v1")
    policy_type = Column(String(64), nullable=False, index=True)
    trigger_type = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)
    ir_payload = Column(JSONBCompat, nullable=False, default=dict)
    ir_hash = Column(String(64), nullable=False)
    next_trigger_at = Column(DateTime, nullable=True, index=True)
    last_triggered_at = Column(DateTime, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)
    last_event_key = Column(String(128), nullable=True)
    execution_count = Column(Integer, nullable=False, default=0)
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_shadow = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime, nullable=True)
    last_skip_reason = Column(String(64), nullable=True)

    user = relationship("User", lazy="selectin")
    commitment = relationship("EpisodicMemory", lazy="selectin")

    __table_args__ = (
        Index(
            "idx_accountability_policies_user_next_trigger",
            "user_id",
            "next_trigger_at",
        ),
        Index(
            "idx_accountability_policies_commitment_enabled",
            "commitment_id",
            "is_enabled",
        ),
    )
