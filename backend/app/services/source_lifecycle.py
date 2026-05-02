"""Lifecycle management for user source documents.

Source documents are stored as ``StoredFile`` records and indexed into the RAG
surfaces as document chunks. This service keeps the relational state, graph
attachments, sharing permissions, and Redis retrieval indexes in sync.
"""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument
from app.models.group_files import GroupFile
from app.models.task import Task
from app.models.task_document import TaskDocument
from app.services.document_upload_storage import document_upload_storage
from app.services.rag_indexing_service import (
    delete_document_chunk_keys,
    delete_group_document_chunk_keys,
    get_rag_redis,
    index_document_chunks,
)

ARCHIVE_REVIEW_DAYS = 90
RETRIEVAL_ENABLED_STATUSES = {SourceLifecycleStatus.ACTIVE.value}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class SourceLifecycleResult:
    source: StoredFile
    status: SourceLifecycleStatus
    invalidated_keys: int
    affected_group_links: int = 0
    affected_chunks: int = 0


class SourceLifecycleService:
    """Owns SourceAsset archive/restore/revoke/orphan/delete transitions."""

    async def get_owned_source(
        self,
        db: AsyncSession,
        *,
        source_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
    ) -> StoredFile | None:
        stmt = select(StoredFile).where(
            StoredFile.id == source_id,
            StoredFile.user_id == user_id,
        )
        if not include_deleted:
            stmt = stmt.where(StoredFile.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def archive(
        self,
        db: AsyncSession,
        *,
        source: StoredFile,
        reason: str = "user_archive",
    ) -> SourceLifecycleResult:
        self._set_lifecycle(source, SourceLifecycleStatus.ARCHIVED, reason=reason)
        now = _utcnow()
        source.archived_at = now
        source.archive_review_due_at = now + timedelta(days=ARCHIVE_REVIEW_DAYS)
        invalidated = await self.invalidate_source_retrieval(db, source)
        await db.flush()
        return SourceLifecycleResult(source=source, status=SourceLifecycleStatus.ARCHIVED, invalidated_keys=invalidated)

    async def restore(
        self,
        db: AsyncSession,
        *,
        source: StoredFile,
        reason: str = "user_restore",
    ) -> SourceLifecycleResult:
        if source.lifecycle_status == SourceLifecycleStatus.REVOKED.value:
            raise ValueError("revoked sources cannot be restored without re-granting permissions")
        self._set_lifecycle(source, SourceLifecycleStatus.ACTIVE, reason=reason)
        source.archived_at = None
        source.orphaned_at = None
        source.archive_review_due_at = None
        indexed = await self.reindex_source_retrieval(db, source)
        await db.flush()
        return SourceLifecycleResult(source=source, status=SourceLifecycleStatus.ACTIVE, invalidated_keys=0, affected_chunks=indexed)

    async def revoke_permissions(
        self,
        db: AsyncSession,
        *,
        source: StoredFile,
        reason: str = "permission_revoked",
    ) -> SourceLifecycleResult:
        self._set_lifecycle(source, SourceLifecycleStatus.REVOKED, reason=reason)
        source.revoked_at = _utcnow()
        source.visibility = "private"
        group_links = await self._active_group_links(db, source.id)
        for group_link in group_links:
            group_link.soft_delete()
        invalidated = await self.invalidate_source_retrieval(db, source, group_links=group_links)
        await db.flush()
        return SourceLifecycleResult(
            source=source,
            status=SourceLifecycleStatus.REVOKED,
            invalidated_keys=invalidated,
            affected_group_links=len(group_links),
        )

    async def goal_close_cleanup(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        goal_id: UUID,
        reason: str = "goal_closed",
    ) -> list[SourceLifecycleResult]:
        """Mark sources only connected through a closed goal/plan as orphaned."""
        stmt = (
            select(StoredFile)
            .join(TaskDocument, TaskDocument.file_id == StoredFile.id)
            .join(Task, Task.id == TaskDocument.task_id)
            .where(
                Task.user_id == user_id,
                Task.plan_id == goal_id,
                StoredFile.user_id == user_id,
                StoredFile.deleted_at.is_(None),
                StoredFile.lifecycle_status == SourceLifecycleStatus.ACTIVE.value,
            )
            .distinct()
        )
        result = await db.execute(stmt)
        sources = list(result.scalars().all())

        outcomes: list[SourceLifecycleResult] = []
        for source in sources:
            self._set_lifecycle(source, SourceLifecycleStatus.ORPHANED, reason=reason)
            source.orphaned_at = _utcnow()
            invalidated = await self.invalidate_source_retrieval(db, source)
            outcomes.append(
                SourceLifecycleResult(
                    source=source,
                    status=SourceLifecycleStatus.ORPHANED,
                    invalidated_keys=invalidated,
                )
            )
        await db.flush()
        return outcomes

    async def delete(
        self,
        db: AsyncSession,
        *,
        source: StoredFile,
        reason: str = "user_delete",
        erase_object: bool = True,
    ) -> SourceLifecycleResult:
        """Delete a source and erase retrieval/object material.

        Object deletion is the cryptographic erasure boundary for encrypted
        object storage: once the encrypted blob is removed, the DB retains only a
        receipt and non-sensitive metadata needed for audit/debugging.
        """
        invalidated = await self.invalidate_source_retrieval(db, source)
        await self._soft_delete_source_graph(db, source)
        await self._soft_delete_chunks(db, source)
        group_links = await self._active_group_links(db, source.id)
        for group_link in group_links:
            group_link.soft_delete()

        self._set_lifecycle(source, SourceLifecycleStatus.REVOKED, reason=reason)
        source.soft_delete()
        source.erased_at = _utcnow()
        source.lifecycle_updated_at = source.erased_at
        source.erasure_receipt = self._erasure_receipt(source)
        if erase_object and source.object_key:
            try:
                await asyncio.to_thread(document_upload_storage.delete_object, object_key=source.object_key)
            except Exception as exc:
                logger.warning(f"Source object erase failed for {source.id}: {exc}")
                source.erasure_receipt = f"{source.erasure_receipt}:object_delete_pending"

        await db.flush()
        return SourceLifecycleResult(
            source=source,
            status=SourceLifecycleStatus.REVOKED,
            invalidated_keys=invalidated,
            affected_group_links=len(group_links),
        )

    async def list_archive_review_due(
        self,
        db: AsyncSession,
        *,
        now: datetime | None = None,
        limit: int = 200,
    ) -> list[StoredFile]:
        due_at = now or _utcnow()
        result = await db.execute(
            select(StoredFile)
            .where(
                StoredFile.lifecycle_status == SourceLifecycleStatus.ARCHIVED.value,
                StoredFile.archive_review_due_at.is_not(None),
                StoredFile.archive_review_due_at <= due_at,
                StoredFile.deleted_at.is_(None),
            )
            .order_by(StoredFile.archive_review_due_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def invalidate_source_retrieval(
        self,
        db: AsyncSession,
        source: StoredFile,
        *,
        group_links: list[GroupFile] | None = None,
    ) -> int:
        redis = await get_rag_redis()
        deleted = 0
        if redis is not None:
            deleted += await delete_document_chunk_keys(redis, source.id)
            active_group_links = group_links if group_links is not None else await self._active_group_links(db, source.id)
            for group_link in active_group_links:
                deleted += await delete_group_document_chunk_keys(redis, group_link.group_id, source.id)

        await cache_service.delete_pattern(f"galaxy:node_source_documents:v1:{source.user_id}:*")
        await cache_service.delete_pattern(f"graphrag:*:{source.user_id}:*")
        return deleted

    async def reindex_source_retrieval(self, db: AsyncSession, source: StoredFile) -> int:
        if source.lifecycle_status not in RETRIEVAL_ENABLED_STATUSES or source.deleted_at is not None:
            return 0
        redis = await get_rag_redis()
        if redis is None:
            return 0
        chunks = (
            await db.execute(
                select(DocumentChunk)
                .where(
                    DocumentChunk.file_id == source.id,
                    DocumentChunk.user_id == source.user_id,
                    DocumentChunk.deleted_at.is_(None),
                )
                .order_by(DocumentChunk.chunk_index.asc())
            )
        ).scalars().all()
        if not chunks:
            return 0
        indexed = await index_document_chunks(redis, source, chunks)
        await cache_service.delete_pattern(f"galaxy:node_source_documents:v1:{source.user_id}:*")
        return indexed

    @staticmethod
    def should_include_in_retrieval(source: StoredFile | None) -> bool:
        return bool(
            source
            and source.deleted_at is None
            and (source.lifecycle_status or SourceLifecycleStatus.ACTIVE.value) in RETRIEVAL_ENABLED_STATUSES
        )

    def _set_lifecycle(self, source: StoredFile, status: SourceLifecycleStatus, *, reason: str) -> None:
        source.lifecycle_status = status.value
        source.lifecycle_reason = reason
        source.lifecycle_updated_at = _utcnow()

    async def _active_group_links(self, db: AsyncSession, source_id: UUID) -> list[GroupFile]:
        result = await db.execute(
            select(GroupFile).where(
                GroupFile.file_id == source_id,
                GroupFile.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def _soft_delete_chunks(self, db: AsyncSession, source: StoredFile) -> None:
        await db.execute(
            update(DocumentChunk)
            .where(DocumentChunk.file_id == source.id, DocumentChunk.deleted_at.is_(None))
            .values(deleted_at=_utcnow())
        )

    async def _soft_delete_source_graph(self, db: AsyncSession, source: StoredFile) -> None:
        await db.execute(
            update(KnowledgeNodeDocument)
            .where(KnowledgeNodeDocument.file_id == source.id, KnowledgeNodeDocument.deleted_at.is_(None))
            .values(deleted_at=_utcnow())
        )
        await db.execute(
            update(KnowledgeNode)
            .where(KnowledgeNode.source_file_id == source.id)
            .values(source_file_id=None)
        )

    def _erasure_receipt(self, source: StoredFile) -> str:
        digest = hashlib.sha256(f"{source.id}:{source.object_key}:{_utcnow().isoformat()}".encode()).hexdigest()[:24]
        return f"source-erased:{digest}"


source_lifecycle_service = SourceLifecycleService()


def source_lifecycle_payload(source: StoredFile, *, invalidated_keys: int = 0) -> dict[str, Any]:
    return {
        "id": str(source.id),
        "file_name": source.file_name,
        "status": source.status,
        "visibility": source.visibility,
        "lifecycle_status": source.lifecycle_status or SourceLifecycleStatus.ACTIVE.value,
        "lifecycle_reason": source.lifecycle_reason,
        "lifecycle_updated_at": source.lifecycle_updated_at.isoformat() if source.lifecycle_updated_at else None,
        "archived_at": source.archived_at.isoformat() if source.archived_at else None,
        "revoked_at": source.revoked_at.isoformat() if source.revoked_at else None,
        "orphaned_at": source.orphaned_at.isoformat() if source.orphaned_at else None,
        "archive_review_due_at": source.archive_review_due_at.isoformat() if source.archive_review_due_at else None,
        "erased_at": source.erased_at.isoformat() if source.erased_at else None,
        "erasure_receipt": source.erasure_receipt,
        "invalidated_rag_keys": invalidated_keys,
    }
