from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ReportSnapshot(BaseModel):
    __tablename__ = "report_snapshots"

    report_id = Column(String(128), nullable=False)
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_type = Column(String(64), nullable=False, default="learning_report", index=True)
    cache_version = Column(String(128), nullable=True, index=True)
    delivery_mode = Column(String(64), nullable=True, index=True)
    quality_mode = Column(String(64), nullable=True)
    trigger_source = Column(Text, nullable=True)
    payload = Column(JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_report_snapshots_report_id", "report_id", unique=True),
        Index("ix_report_snapshots_user_cache", "user_id", "cache_version"),
    )

    user = relationship("User")
