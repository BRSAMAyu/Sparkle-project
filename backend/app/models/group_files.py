"""
Group file sharing models
群组文件共享模型
"""
from enum import StrEnum

from sqlalchemy import Boolean, Float, Integer, JSON, Column, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel
from app.models.community import GroupRole


class GroupFileTrustLevel(StrEnum):
    """Trust tier applied to group documents."""

    OFFICIAL = "official"
    VERIFIED = "verified"
    MEMBER = "member"


class GroupFile(BaseModel):
    """
    Group file metadata
    """
    __tablename__ = "group_files"

    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    category = Column(String(64), nullable=True)
    description = Column(String(500), nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    trust_level = Column(Enum(GroupFileTrustLevel), default=GroupFileTrustLevel.MEMBER, nullable=False, index=True)
    is_knowledge_base = Column(Boolean, default=False, nullable=False, index=True)
    download_count = Column(Integer, default=0, nullable=False)
    citation_count = Column(Integer, default=0, nullable=False)
    rating_count = Column(Integer, default=0, nullable=False)
    rating_total = Column(Float, default=0.0, nullable=False)

    view_role = Column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False)
    download_role = Column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False)
    manage_role = Column(Enum(GroupRole), default=GroupRole.ADMIN, nullable=False)

    group = relationship("Group", back_populates="files")
    file = relationship("StoredFile", back_populates="group_links")
    shared_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("group_id", "file_id", name="uq_group_files_group_file"),
        Index("idx_group_files_group", "group_id"),
        Index("idx_group_files_file", "file_id"),
        Index("idx_group_files_shared_by", "shared_by_id"),
        Index("idx_group_files_category", "category"),
        Index("idx_group_files_knowledge_base", "group_id", "is_knowledge_base"),
    )
