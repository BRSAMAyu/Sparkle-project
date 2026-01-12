"""
Group file sharing models
群组文件共享模型
"""
from sqlalchemy import Column, ForeignKey, Enum, String, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID
from app.models.community import GroupRole


class GroupFile(BaseModel):
    """
    Group file metadata
    """
    __tablename__ = "group_files"

    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    category = Column(String(64), nullable=True)
    tags = Column(JSON, default=list, nullable=False)

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
    )
