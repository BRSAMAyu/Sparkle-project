from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ReportSnapshot(BaseModel):
    __tablename__ = "report_snapshots"

    report_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_type: Mapped[str] = mapped_column(String(64), nullable=False, default="learning_report", index=True)
    cache_version: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    delivery_mode: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    quality_mode: Mapped[str] = mapped_column(String(64), nullable=True)
    trigger_source: Mapped[str] = mapped_column(Text, nullable=True)
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_report_snapshots_report_id", "report_id", unique=True),
        Index("ix_report_snapshots_user_cache", "user_id", "cache_version"),
    )

    user = relationship("User")
