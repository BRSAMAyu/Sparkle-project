"""
File storage models
文件存储模型
"""
from sqlalchemy import BigInteger, Column, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


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
    # Rolling retrieval quality score in [-1.0, 1.0].
    # 0.0 is neutral, positive values promote retrieval, negative values demote it.
    document_quality_score = Column(Float, nullable=False, default=0.0)

    user = relationship("User")
    group_links = relationship("GroupFile", back_populates="file")
    source_file = relationship("StoredFile", remote_side="StoredFile.id")
