"""
Group file sharing models
群组文件共享模型
"""
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    # V3-FIX-149：DB 枚举 groupfiletrustlevel（gkb001）为小写值 {official, verified, member}，values_callable 对齐按值读写；
    # 缺它则 ORM 按枚举名（MEMBER 等）写库 → InvalidTextRepresentationError 500，读 'member' 默认行 → LookupError 500。
    trust_level: Mapped[GroupFileTrustLevel] = mapped_column(
        Enum(GroupFileTrustLevel, values_callable=lambda obj: [e.value for e in obj]),
        default=GroupFileTrustLevel.MEMBER,
        nullable=False,
        index=True,
    )
    is_knowledge_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    citation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    view_role: Mapped[GroupRole] = mapped_column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False)
    download_role: Mapped[GroupRole] = mapped_column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False)
    manage_role: Mapped[GroupRole] = mapped_column(Enum(GroupRole), default=GroupRole.ADMIN, nullable=False)

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
