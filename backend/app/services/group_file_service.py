"""
Group file service
群组文件服务
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.community import GroupMember, GroupRole
from app.models.file_storage import StoredFile
from app.models.group_files import GroupFile


class GroupFileService:
    """群文件服务"""

    @staticmethod
    def _allowed_roles(role: GroupRole) -> List[GroupRole]:
        if role == GroupRole.OWNER:
            return [GroupRole.MEMBER, GroupRole.ADMIN, GroupRole.OWNER]
        if role == GroupRole.ADMIN:
            return [GroupRole.MEMBER, GroupRole.ADMIN]
        return [GroupRole.MEMBER]

    @staticmethod
    def _can_access(role: GroupRole, required: GroupRole) -> bool:
        allowed = GroupFileService._allowed_roles(role)
        return required in allowed

    @staticmethod
    async def _require_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember:
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")
        return member

    @staticmethod
    async def share_file(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        file_id: UUID,
        category: Optional[str],
        tags: Optional[List[str]],
        view_role: GroupRole,
        download_role: GroupRole,
        manage_role: GroupRole,
    ) -> Tuple[GroupFile, StoredFile]:
        await GroupFileService._require_member(db, group_id, user_id)

        result = await db.execute(
            select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.user_id == user_id,
                StoredFile.not_deleted_filter(),
            )
        )
        stored_file = result.scalar_one_or_none()
        if not stored_file:
            raise ValueError("文件不存在或无权限分享")

        existing = await db.execute(
            select(GroupFile).where(
                GroupFile.group_id == group_id,
                GroupFile.file_id == file_id,
            )
        )
        group_file = existing.scalar_one_or_none()
        if group_file and not group_file.is_deleted:
            if category is not None:
                group_file.category = category
            if tags is not None:
                group_file.tags = tags
            group_file.view_role = view_role
            group_file.download_role = download_role
            group_file.manage_role = manage_role
            db.add(group_file)
            return group_file, stored_file

        if group_file and group_file.is_deleted:
            group_file.deleted_at = None
            group_file.category = category
            group_file.tags = tags or []
            group_file.view_role = view_role
            group_file.download_role = download_role
            group_file.manage_role = manage_role
            group_file.shared_by_id = user_id
            db.add(group_file)
        else:
            group_file = GroupFile(
                group_id=group_id,
                file_id=file_id,
                shared_by_id=user_id,
                category=category,
                tags=tags or [],
                view_role=view_role,
                download_role=download_role,
                manage_role=manage_role,
            )
            db.add(group_file)

        stored_file.visibility = "group"
        db.add(stored_file)
        await db.flush()
        return group_file, stored_file

    @staticmethod
    async def list_files(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        category: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[List[GroupFile], GroupRole]:
        member = await GroupFileService._require_member(db, group_id, user_id)
        allowed_roles = GroupFileService._allowed_roles(member.role)

        query = (
            select(GroupFile)
            .options(
                selectinload(GroupFile.file),
                selectinload(GroupFile.shared_by),
            )
            .where(
                GroupFile.group_id == group_id,
                GroupFile.not_deleted_filter(),
                GroupFile.view_role.in_(allowed_roles),
            )
            .order_by(GroupFile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if category:
            query = query.where(GroupFile.category == category)

        result = await db.execute(query)
        return result.scalars().all(), member.role

    @staticmethod
    async def update_permissions(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        file_id: UUID,
        view_role: GroupRole,
        download_role: GroupRole,
        manage_role: GroupRole,
    ) -> GroupFile:
        member = await GroupFileService._require_member(db, group_id, user_id)
        if member.role not in (GroupRole.ADMIN, GroupRole.OWNER):
            raise ValueError("无权限修改群文件权限")

        result = await db.execute(
            select(GroupFile).where(
                GroupFile.group_id == group_id,
                GroupFile.file_id == file_id,
                GroupFile.not_deleted_filter(),
            )
        )
        group_file = result.scalar_one_or_none()
        if not group_file:
            raise ValueError("文件未共享到群组")

        group_file.view_role = view_role
        group_file.download_role = download_role
        group_file.manage_role = manage_role
        db.add(group_file)
        await db.flush()
        return group_file

    @staticmethod
    async def category_stats(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> List[Tuple[Optional[str], int]]:
        member = await GroupFileService._require_member(db, group_id, user_id)
        allowed_roles = GroupFileService._allowed_roles(member.role)

        query = (
            select(GroupFile.category, func.count(GroupFile.id))
            .where(
                GroupFile.group_id == group_id,
                GroupFile.not_deleted_filter(),
                GroupFile.view_role.in_(allowed_roles),
            )
            .group_by(GroupFile.category)
            .order_by(func.count(GroupFile.id).desc())
        )
        result = await db.execute(query)
        return result.all()

    @staticmethod
    def can_download(member_role: GroupRole, required_role: GroupRole) -> bool:
        return GroupFileService._can_access(member_role, required_role)

    @staticmethod
    def can_manage(member_role: GroupRole, required_role: GroupRole) -> bool:
        return GroupFileService._can_access(member_role, required_role)
