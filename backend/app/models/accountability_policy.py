from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class AccountabilityPolicy(BaseModel):
    __tablename__ = "accountability_policies"

    policy_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commitment_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("episodic_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    policy_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ir_payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    ir_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    next_trigger_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    cooldown_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_event_key: Mapped[str] = mapped_column(String(128), nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_shadow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_skip_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

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
