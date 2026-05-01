"""
Group file service
群组文件服务
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.celery_tasks import process_stored_file
from app.core.event_bus import GroupFileSharedEvent, event_bus
from app.models.background_task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType
from app.models.community import GroupMember, GroupRole
from app.models.file_storage import StoredFile
from app.models.group_files import GroupFile, GroupFileTrustLevel
from app.services.document_upload_storage import document_upload_storage


@dataclass(slots=True)
class GroupFileListEntry:
    group_file: GroupFile
    is_in_my_library: bool


@dataclass(slots=True)
class FileCopyResult:
    stored_file: StoredFile
    job_id: str | None
    already_exists: bool
    notify_owner_id: UUID | None = None


class GroupFileService:
    """群文件服务"""

    PROCESSED_STATUSES = {"processed", "ready", "queued", "processing"}
    COPYABLE_VISIBILITIES = {"group", "public"}

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _allowed_roles(role: GroupRole) -> list[GroupRole]:
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
    def _root_source_file_id(stored_file: StoredFile) -> UUID:
        return stored_file.source_file_id or stored_file.id

    @staticmethod
    def _build_object_key(*, user_id: UUID, file_id: UUID, file_name: str) -> str:
        ext = os.path.splitext(file_name or "")[1] or ".bin"
        return f"{user_id}/{file_id}/original{ext}"

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
            raise PermissionError("不是群组成员")
        return member

    @staticmethod
    async def _get_owned_file(db: AsyncSession, *, user_id: UUID, file_id: UUID) -> StoredFile:
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
        return stored_file

    @staticmethod
    async def _get_group_file(
        db: AsyncSession,
        *,
        group_id: UUID,
        file_id: UUID,
    ) -> GroupFile:
        result = await db.execute(
            select(GroupFile)
            .options(
                selectinload(GroupFile.file),
                selectinload(GroupFile.shared_by),
            )
            .where(
                GroupFile.group_id == group_id,
                GroupFile.file_id == file_id,
                GroupFile.not_deleted_filter(),
            )
        )
        group_file = result.scalar_one_or_none()
        if not group_file:
            raise ValueError("文件未共享到群组")
        return group_file

    @staticmethod
    async def _get_existing_library_file(
        db: AsyncSession,
        *,
        user_id: UUID,
        origin_file_id: UUID,
    ) -> StoredFile | None:
        result = await db.execute(
            select(StoredFile)
            .where(
                StoredFile.user_id == user_id,
                StoredFile.not_deleted_filter(),
                or_(
                    StoredFile.id == origin_file_id,
                    StoredFile.source_file_id == origin_file_id,
                ),
            )
            .order_by(StoredFile.source_file_id.is_(None).desc(), StoredFile.created_at.asc())
        )
        return result.scalars().first()

    @staticmethod
    async def _enqueue_processing(
        db: AsyncSession,
        *,
        stored_file: StoredFile,
        effective_user_id: UUID,
    ) -> str:
        download_url = document_upload_storage.create_presigned_get_url(object_key=stored_file.object_key)
        thumbnail_upload_url = None
        if stored_file.mime_type == "application/pdf":
            thumbnail_upload_url = document_upload_storage.create_presigned_put_url(
                object_key=f"{stored_file.id}/thumbnail.jpg",
                mime_type="image/jpeg",
                file_size=0,
            )

        task = process_stored_file.delay(
            file_id=str(stored_file.id),
            user_id=str(effective_user_id),
            download_url=download_url,
            file_name=stored_file.file_name,
            mime_type=stored_file.mime_type,
            thumbnail_upload_url=thumbnail_upload_url,
        )

        stored_file.status = "queued"
        stored_file.error_message = None
        db.add(stored_file)
        db.add(
            BackgroundTask(
                user_id=effective_user_id,
                task_type=BackgroundTaskType.DATA_SYNC,
                name=f"文档分析: {stored_file.file_name}",
                status=BackgroundTaskStatus.PENDING,
                progress=0.0,
                progress_message="Queued for document analysis",
                related_entity_id=stored_file.id,
                related_entity_type="stored_file",
                external_task_id=task.id,
            )
        )
        await db.flush()
        return task.id

    @staticmethod
    async def ensure_processing_for_file(
        db: AsyncSession,
        *,
        stored_file: StoredFile,
        effective_user_id: UUID,
    ) -> str | None:
        if (stored_file.status or "").strip().lower() in GroupFileService.PROCESSED_STATUSES:
            return None
        if not document_upload_storage.object_exists(object_key=stored_file.object_key):
            return None
        return await GroupFileService._enqueue_processing(
            db,
            stored_file=stored_file,
            effective_user_id=effective_user_id,
        )

    @staticmethod
    async def list_accessible_group_ids(
        db: AsyncSession,
        user_id: UUID,
        requested_group_ids: list[UUID | str] | None = None,
    ) -> list[UUID]:
        stmt = select(GroupMember.group_id).where(
            GroupMember.user_id == user_id,
            GroupMember.not_deleted_filter(),
        )
        normalized_group_ids: list[UUID] = []
        for group_id in requested_group_ids or []:
            try:
                normalized_group_ids.append(UUID(str(group_id)))
            except (TypeError, ValueError):
                continue
        if normalized_group_ids:
            stmt = stmt.where(GroupMember.group_id.in_(normalized_group_ids))
        result = await db.execute(stmt)
        return list(dict.fromkeys(result.scalars().all()))

    @staticmethod
    async def list_accessible_files(
        db: AsyncSession,
        *,
        user_id: UUID,
        requested_file_ids: list[UUID] | None = None,
        include_group_documents: bool = False,
        group_ids: list[UUID | str] | None = None,
        limit: int | None = None,
    ) -> list[StoredFile]:
        stmt = select(StoredFile).where(StoredFile.not_deleted_filter())
        if requested_file_ids:
            stmt = stmt.where(StoredFile.id.in_(requested_file_ids))

        if include_group_documents:
            accessible_group_ids = await GroupFileService.list_accessible_group_ids(
                db,
                user_id,
                requested_group_ids=group_ids,
            )
            if accessible_group_ids:
                stmt = (
                    stmt.outerjoin(
                        GroupFile,
                        and_(
                            GroupFile.file_id == StoredFile.id,
                            GroupFile.not_deleted_filter(),
                            GroupFile.group_id.in_(accessible_group_ids),
                        ),
                    )
                    .outerjoin(
                        GroupMember,
                        and_(
                            GroupMember.group_id == GroupFile.group_id,
                            GroupMember.user_id == user_id,
                            GroupMember.not_deleted_filter(),
                        ),
                    )
                    .where(or_(StoredFile.user_id == user_id, GroupMember.id.isnot(None)))
                )
            else:
                stmt = stmt.where(StoredFile.user_id == user_id)
        else:
            stmt = stmt.where(StoredFile.user_id == user_id)

        stmt = stmt.order_by(StoredFile.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        files: list[StoredFile] = []
        seen: set[str] = set()
        for stored_file in result.scalars().all():
            key = str(stored_file.id)
            if key in seen:
                continue
            seen.add(key)
            files.append(stored_file)
        return files

    @staticmethod
    async def share_file(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        file_id: UUID,
        category: str | None,
        description: str | None,
        tags: list[str] | None,
        view_role: GroupRole,
        download_role: GroupRole,
        manage_role: GroupRole,
        trust_level: GroupFileTrustLevel | None = None,
        is_knowledge_base: bool | None = None,
    ) -> tuple[GroupFile, StoredFile, str | None]:
        await GroupFileService._require_member(db, group_id, user_id)
        stored_file = await GroupFileService._get_owned_file(db, user_id=user_id, file_id=file_id)

        if stored_file.visibility not in GroupFileService.COPYABLE_VISIBILITIES:
            raise PermissionError("文件可见性不允许分享至群组")

        existing = await db.execute(
            select(GroupFile).where(
                GroupFile.group_id == group_id,
                GroupFile.file_id == file_id,
            )
        )
        group_file = existing.scalar_one_or_none()
        should_publish_share_event = False
        if group_file and not group_file.is_deleted:
            if category is not None:
                group_file.category = category
            if description is not None:
                group_file.description = description
            if tags is not None:
                group_file.tags = tags
            if trust_level is not None:
                group_file.trust_level = trust_level
            if is_knowledge_base is not None:
                group_file.is_knowledge_base = is_knowledge_base
            group_file.view_role = view_role
            group_file.download_role = download_role
            group_file.manage_role = manage_role
            db.add(group_file)
        elif group_file and group_file.is_deleted:
            group_file.deleted_at = None
            group_file.category = category
            group_file.description = description
            group_file.tags = tags or []
            group_file.trust_level = trust_level or GroupFileTrustLevel.MEMBER
            group_file.is_knowledge_base = bool(is_knowledge_base)
            group_file.view_role = view_role
            group_file.download_role = download_role
            group_file.manage_role = manage_role
            group_file.shared_by_id = user_id
            db.add(group_file)
            should_publish_share_event = True
        else:
            group_file = GroupFile(
                group_id=group_id,
                file_id=file_id,
                shared_by_id=user_id,
                category=category,
                description=description,
                tags=tags or [],
                trust_level=trust_level or GroupFileTrustLevel.MEMBER,
                is_knowledge_base=bool(is_knowledge_base),
                view_role=view_role,
                download_role=download_role,
                manage_role=manage_role,
            )
            db.add(group_file)
            should_publish_share_event = True

        await db.flush()
        if should_publish_share_event:
            event = GroupFileSharedEvent(
                group_id=str(group_id),
                file_id=str(file_id),
                group_file_id=str(group_file.id),
                shared_by_user_id=str(user_id),
                triggered_at=GroupFileService._utcnow_iso(),
            )
            await event_bus.publish(event.event_type, event.to_dict())
        job_id = await GroupFileService.ensure_processing_for_file(
            db,
            stored_file=stored_file,
            effective_user_id=user_id,
        )
        return group_file, stored_file, job_id

    @staticmethod
    async def list_files(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        category: str | None,
        search_query: str | None,
        sort_by: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[GroupFileListEntry], GroupRole]:
        member = await GroupFileService._require_member(db, group_id, user_id)
        allowed_roles = GroupFileService._allowed_roles(member.role)

        query = (
            select(GroupFile)
            .join(StoredFile, StoredFile.id == GroupFile.file_id)
            .options(
                selectinload(GroupFile.file),
                selectinload(GroupFile.shared_by),
            )
            .where(
                GroupFile.group_id == group_id,
                GroupFile.not_deleted_filter(),
                GroupFile.view_role.in_(allowed_roles),
                StoredFile.deleted_at.is_(None),
            )
        )
        if category:
            query = query.where(GroupFile.category == category)
        if search_query:
            pattern = f"%{search_query.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(StoredFile.file_name).like(pattern),
                    func.lower(func.coalesce(GroupFile.description, "")).like(pattern),
                    func.lower(func.coalesce(GroupFile.category, "")).like(pattern),
                )
            )

        normalized_sort = (sort_by or "latest").strip().lower()
        if normalized_sort in {"downloads", "download_count", "most_downloaded"}:
            query = query.order_by(GroupFile.download_count.desc(), GroupFile.created_at.desc())
        elif normalized_sort in {"name", "file_name"}:
            query = query.order_by(StoredFile.file_name.asc(), GroupFile.created_at.desc())
        else:
            query = query.order_by(GroupFile.created_at.desc())

        offset = max(0, (page - 1) * page_size)
        result = await db.execute(query.limit(page_size).offset(offset))
        group_files = result.scalars().all()
        if not group_files:
            return [], member.role

        origin_ids = {GroupFileService._root_source_file_id(item.file) for item in group_files if item.file}
        owned_origin_ids: set[UUID] = set()
        if origin_ids:
            owned_result = await db.execute(
                select(StoredFile.source_file_id).where(
                    StoredFile.user_id == user_id,
                    StoredFile.not_deleted_filter(),
                    StoredFile.source_file_id.in_(origin_ids),
                )
            )
            owned_origin_ids = {item for item in owned_result.scalars().all() if item is not None}

        entries: list[GroupFileListEntry] = []
        for item in group_files:
            source_file = item.file
            is_in_my_library = False
            if source_file:
                origin_id = GroupFileService._root_source_file_id(source_file)
                is_in_my_library = source_file.user_id == user_id or origin_id in owned_origin_ids
            entries.append(GroupFileListEntry(group_file=item, is_in_my_library=is_in_my_library))
        return entries, member.role

    @staticmethod
    async def copy_to_library(
        db: AsyncSession,
        *,
        group_id: UUID,
        file_id: UUID,
        user_id: UUID,
    ) -> FileCopyResult:
        member = await GroupFileService._require_member(db, group_id, user_id)
        group_file = await GroupFileService._get_group_file(db, group_id=group_id, file_id=file_id)
        if not GroupFileService.can_download(member.role, group_file.download_role):
            raise PermissionError("无权限下载该群文件")

        source_file = group_file.file
        if source_file is None:
            raise ValueError("共享文件不存在")
        if source_file.visibility not in GroupFileService.COPYABLE_VISIBILITIES:
            raise PermissionError("文件可见性不允许复制到个人资料库")

        origin_file_id = GroupFileService._root_source_file_id(source_file)
        existing = await GroupFileService._get_existing_library_file(
            db,
            user_id=user_id,
            origin_file_id=origin_file_id,
        )
        if existing is not None:
            return FileCopyResult(stored_file=existing, job_id=None, already_exists=True)

        copied_file_id = uuid4()
        copied_object_key = GroupFileService._build_object_key(
            user_id=user_id,
            file_id=copied_file_id,
            file_name=source_file.file_name,
        )
        document_upload_storage.copy_object(
            source_object_key=source_file.object_key,
            destination_object_key=copied_object_key,
        )

        copied_file = StoredFile(
            id=copied_file_id,
            user_id=user_id,
            file_name=source_file.file_name,
            mime_type=source_file.mime_type,
            file_size=source_file.file_size,
            bucket=document_upload_storage.bucket,
            object_key=copied_object_key,
            status="uploaded",
            visibility="private",
            retention_policy=source_file.retention_policy,
            source_file_id=origin_file_id,
        )
        db.add(copied_file)
        await db.flush()

        group_file.download_count = int(group_file.download_count or 0) + 1
        db.add(group_file)
        job_id = await GroupFileService._enqueue_processing(
            db,
            stored_file=copied_file,
            effective_user_id=user_id,
        )
        notify_owner_id = source_file.user_id if source_file.user_id != user_id else None
        return FileCopyResult(
            stored_file=copied_file,
            job_id=job_id,
            already_exists=False,
            notify_owner_id=notify_owner_id,
        )

    @staticmethod
    async def share_file_to_user(
        db: AsyncSession,
        *,
        owner_id: UUID,
        target_user_id: UUID,
        file_id: UUID,
    ) -> FileCopyResult:
        if owner_id == target_user_id:
            raise ValueError("不能分享给自己")

        source_file = await GroupFileService._get_owned_file(db, user_id=owner_id, file_id=file_id)
        origin_file_id = GroupFileService._root_source_file_id(source_file)
        existing = await GroupFileService._get_existing_library_file(
            db,
            user_id=target_user_id,
            origin_file_id=origin_file_id,
        )
        if existing is not None:
            return FileCopyResult(stored_file=existing, job_id=None, already_exists=True)

        copied_file_id = uuid4()
        copied_object_key = GroupFileService._build_object_key(
            user_id=target_user_id,
            file_id=copied_file_id,
            file_name=source_file.file_name,
        )
        document_upload_storage.copy_object(
            source_object_key=source_file.object_key,
            destination_object_key=copied_object_key,
        )

        copied_file = StoredFile(
            id=copied_file_id,
            user_id=target_user_id,
            file_name=source_file.file_name,
            mime_type=source_file.mime_type,
            file_size=source_file.file_size,
            bucket=document_upload_storage.bucket,
            object_key=copied_object_key,
            status="uploaded",
            visibility="private",
            retention_policy=source_file.retention_policy,
            source_file_id=origin_file_id,
        )
        db.add(copied_file)
        await db.flush()

        job_id = await GroupFileService._enqueue_processing(
            db,
            stored_file=copied_file,
            effective_user_id=target_user_id,
        )
        return FileCopyResult(stored_file=copied_file, job_id=job_id, already_exists=False)

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
            raise PermissionError("无权限修改群文件权限")

        group_file = await GroupFileService._get_group_file(db, group_id=group_id, file_id=file_id)
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
    ) -> list[tuple[str | None, int]]:
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

    @staticmethod
    def average_rating(group_file: GroupFile) -> float | None:
        if not group_file.rating_count:
            return None
        return round(float(group_file.rating_total or 0.0) / float(group_file.rating_count), 2)

    @staticmethod
    def quality_score(group_file: GroupFile) -> float:
        rating = GroupFileService.average_rating(group_file) or 0.0
        trust_bonus = {
            GroupFileTrustLevel.OFFICIAL: 0.35,
            GroupFileTrustLevel.VERIFIED: 0.2,
            GroupFileTrustLevel.MEMBER: 0.0,
        }[group_file.trust_level]
        score = (
            trust_bonus
            + min(float(group_file.download_count or 0) / 25.0, 0.2)
            + min(float(group_file.citation_count or 0) / 20.0, 0.2)
            + (rating / 5.0) * 0.25
        )
        return round(min(score, 1.0), 3)

    @staticmethod
    def retrieval_boost(group_file: GroupFile) -> float:
        base = {
            GroupFileTrustLevel.OFFICIAL: 1.5,
            GroupFileTrustLevel.VERIFIED: 1.2,
            GroupFileTrustLevel.MEMBER: 1.0,
        }[group_file.trust_level]
        return round(base + GroupFileService.quality_score(group_file) * 0.25, 3)
