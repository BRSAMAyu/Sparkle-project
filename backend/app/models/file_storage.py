"""
File storage models
文件存储模型
"""
from sqlalchemy import Column, String, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


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
    visibility = Column(String(32), default="private", nullable=False)
    error_message = Column(String(255), nullable=True)

    user = relationship("User")
    group_links = relationship("GroupFile", back_populates="file")
