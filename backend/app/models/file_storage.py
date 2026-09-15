"""
File storage models
文件存储模型
"""
import enum

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

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

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(150), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    bucket = Column(String(128), nullable=False)
    object_key = Column(String(512), nullable=False, unique=True)
    status = Column(String(32), default="uploading", nullable=False)
    visibility = Column(String(32), default="private", nullable=False) # Maps to ArtifactScope
    retention_policy = Column(String(32), default="ephemeral", nullable=False) # ephemeral, keep
    source_file_id = Column(GUID(), ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True, index=True)
    error_message = Column(String(255), nullable=True)
    lifecycle_status = Column(String(32), default=SourceLifecycleStatus.ACTIVE.value, nullable=False, index=True)
    lifecycle_reason = Column(String(255), nullable=True)
    lifecycle_updated_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    orphaned_at = Column(DateTime, nullable=True, index=True)
    archive_review_due_at = Column(DateTime, nullable=True, index=True)
    erased_at = Column(DateTime, nullable=True)
    erasure_receipt = Column(String(255), nullable=True)
    # Rolling retrieval quality score in [-1.0, 1.0].
    # 0.0 is neutral, positive values promote retrieval, negative values demote it.
    document_quality_score = Column(Float, nullable=False, default=0.0)

    user = relationship("User")
    group_links = relationship("GroupFile", back_populates="file")
    source_file = relationship("StoredFile", remote_side="StoredFile.id")
