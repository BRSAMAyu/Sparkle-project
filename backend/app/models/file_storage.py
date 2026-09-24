"""
File storage models
文件存储模型
"""
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class SourceLifecycleStatus(enum.StrEnum):
    """Lifecycle state controlling whether a stored source may participate in retrieval."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    REVOKED = "revoked"
    ORPHANED = "orphaned"


class StoredFile(BaseModel):
    """
    Stored file metadata
    """
    __tablename__ = "stored_files"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="uploading", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False) # Maps to ArtifactScope
    retention_policy: Mapped[str] = mapped_column(String(32), default="ephemeral", nullable=False) # ephemeral, keep
    source_file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True, index=True)
    error_message: Mapped[str] = mapped_column(String(255), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default=SourceLifecycleStatus.ACTIVE.value, nullable=False, index=True)
    lifecycle_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    lifecycle_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    orphaned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    archive_review_due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    erased_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    erasure_receipt: Mapped[str] = mapped_column(String(255), nullable=True)
    # Rolling retrieval quality score in [-1.0, 1.0].
    # 0.0 is neutral, positive values promote retrieval, negative values demote it.
    document_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    user = relationship("User")
    group_links = relationship("GroupFile", back_populates="file")
    source_file = relationship("StoredFile", remote_side="StoredFile.id")
