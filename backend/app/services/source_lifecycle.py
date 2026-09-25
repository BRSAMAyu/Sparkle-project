"""Lifecycle management for user source documents.

Source documents are stored as ``StoredFile`` records and indexed into the RAG
surfaces as document chunks. This service keeps the relational state, graph
attachments, sharing permissions, and Redis retrieval indexes in sync.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict
from uuid import UUID

from loguru import logger
from sqlalchemy import event, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument
from app.models.group_files import GroupFile
from app.models.task import Task
from app.models.task_document import TaskDocument
from app.services.document_upload_storage import document_upload_storage
from app.services.galaxy.retrieval_service import KNOWLEDGE_VERSION_CACHE_KEY
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
class _RetrievalInvalidationPlan:
    """一次检索失效的不可变执行计划（FIX-16 ② N1）。

    在事务内捕获（source/group 身份在软删前解析），在事务提交后执行——
    这样失效的 Redis DEL 严格晚于 commit，消灭「DEL→commit 窗口内并发
    检索以 READ COMMITTED 旧快照重播删除前 knowledge_version 并再缓存
    30s」的陈旧窗口。
    """

    source_id: UUID
    user_id: UUID
    group_ids: tuple[UUID, ...] = ()


# 已排期、尚在执行的 post-commit 失效任务集合（测试可 drain；优雅关停可 await）。
_PENDING_INVALIDATION_TASKS: set[asyncio.Task] = set()

class _InvalidationReg(TypedDict):
    """per-session 登记表值结构：plans 待执行计划 + tasks 在飞任务。"""

    plans: list[_RetrievalInvalidationPlan]
    tasks: list[asyncio.Task[Any]]


# per-session 失效计划登记表（session 请求级生命周期，弱引用不阻止 GC）。
_POST_COMMIT_INVALIDATION_REGS: weakref.WeakKeyDictionary[Any, _InvalidationReg] = (
    weakref.WeakKeyDictionary()
)


def _on_invalidation_task_done(task: asyncio.Task) -> None:
    _PENDING_INVALIDATION_TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.warning(f"Post-commit retrieval invalidation task failed: {exc}")


async def wait_for_pending_post_commit_invalidation() -> None:
    """等待所有已排期的 post-commit 检索失效完成（测试 drain / 优雅关停用）。"""
    tasks = [t for t in list(_PENDING_INVALIDATION_TASKS) if not t.done()]
    if tasks:
        await asyncio.gather(*tasks)


async def drain_session_retrieval_invalidations(db: AsyncSession) -> None:
    """显式 await 本会话已排期的 post-commit 失效任务（请求路径同步性保证）。

    E-05 live 隔离语义要求：删除/归档事务 commit 返回后，versioned redis
    键必须已经清除——after_commit 钩子 spawn 的任务由 commit 发起方在此
    await 完成，而非留给事件循环后续 tick（毫秒级异步窗口也不允许）。
    """
    sync_session = db.sync_session
    reg = _POST_COMMIT_INVALIDATION_REGS.get(sync_session)
    if not reg:
        return
    tasks = [t for t in reg["tasks"] if not t.done()]
    reg["tasks"].clear()
    if tasks:
        await asyncio.gather(*tasks)


@dataclass(frozen=True)
class SourceLifecycleResult:
    source: StoredFile
    status: SourceLifecycleStatus
    # FIX-16 ②（N1）语义变更：失效已排期到事务提交后执行，本值为「排期失效
    # 单元数」（1 + 关联群组数）；精确删除键数在异步执行完成后落结构化日志。
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
        invalidated = await self._schedule_post_commit_retrieval_invalidation(db, source)
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
        invalidated = await self._schedule_post_commit_retrieval_invalidation(db, source, group_links=group_links)
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
            invalidated = await self._schedule_post_commit_retrieval_invalidation(db, source)
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

        FIX-16 ②（N1）：检索失效改为「提交后」执行——计划在事务内、群组链接
        尚未软删时捕获（活跃群组身份必须在删除前解析），Redis DEL 与缓存失效
        严格晚于 commit。删除对象存储（密码学擦除边界）保持提交前执行：
        过度擦除安全、擦除不足不安全，方向不可反。
        """
        invalidated = await self._schedule_post_commit_retrieval_invalidation(db, source)
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
        """立即失效来源的检索面（公开同步入口：直调方与测试使用）。

        生命周期转换路径（archive/revoke/goal_close_cleanup/delete）**不再**走
        本方法——它们经 ``_schedule_post_commit_retrieval_invalidation`` 把失效
        排期到事务提交之后（FIX-16 ② N1：提交前的 DEL 会在「DEL→commit 窗口」
        内被并发检索以 READ COMMITTED 旧快照重播删除前 knowledge_version 并
        再缓存 30s，已删内容在删除完成后仍可命中语义缓存）。
        """
        redis = await get_rag_redis()
        group_ids: tuple[UUID, ...] = ()
        if redis is not None:
            if group_links is not None:
                group_ids = tuple(link.group_id for link in group_links)
            elif db is not None:
                group_ids = tuple(link.group_id for link in await self._active_group_links(db, source.id))
        return await self._execute_retrieval_invalidation(
            _RetrievalInvalidationPlan(source_id=source.id, user_id=source.user_id, group_ids=group_ids),
            redis=redis,
        )

    async def _execute_retrieval_invalidation(
        self,
        plan: _RetrievalInvalidationPlan,
        *,
        redis: Any = None,
    ) -> int:
        """执行一份失效计划（Redis chunk key + 派生缓存 + 全局知识版本键）。"""
        if redis is None:
            redis = await get_rag_redis()
        deleted = 0
        if redis is not None:
            deleted += await delete_document_chunk_keys(redis, plan.source_id)
            for group_id in plan.group_ids:
                deleted += await delete_group_document_chunk_keys(redis, group_id, plan.source_id)

        await cache_service.delete_pattern(f"galaxy:node_source_documents:v1:{plan.user_id}:*")
        await cache_service.delete_pattern(f"graphrag:*:{plan.user_id}:*")
        # E-05 D2（R2 返修）：失效全局知识版本缓存（30s TTL）。否则删除/归档后
        # 的 TTL 窗口内，检索仍以旧 knowledge_version 组语义缓存键 → 已删内容
        # 继续命中（exact 与语义相似两条路径）。该键是派生缓存，DEL 后下次
        # 读取自动从 DB 重算，无数据丢失。
        try:
            await cache_service.delete(KNOWLEDGE_VERSION_CACHE_KEY)
        except Exception as exc:
            logger.warning(f"Failed to invalidate knowledge version cache after source invalidation: {exc}")
        return deleted

    async def _schedule_post_commit_retrieval_invalidation(
        self,
        db: AsyncSession,
        source: StoredFile,
        *,
        group_links: list[GroupFile] | None = None,
    ) -> int:
        """FIX-16 ②（N1/D4 follow-up）：把检索失效排期到事务提交之后执行。

        机制：在事务内捕获失效计划（群组身份必须在软删前解析），经 SQLAlchemy
        会话级 ``after_commit`` 事件在事件循环内 spawn 失效任务；``after_rollback``
        时丢弃未执行的计划（回滚的事务无失效需求）。每次 commit 恰好执行一次
        当时刻的全部累积计划（goal_close_cleanup 多源批删同事务共享一次执行）。

        返回值为「排期失效单元数」（1 + 群组数），用于
        ``SourceLifecycleResult.invalidated_keys``；精确删除键数在任务完成后
        落结构化日志（提交前无法预知 SCAN 结果，不再谎报同步计数）。
        """
        redis = await get_rag_redis()
        group_ids: tuple[UUID, ...] = ()
        if redis is not None:
            if group_links is not None:
                group_ids = tuple(link.group_id for link in group_links)
            else:
                group_ids = tuple(link.group_id for link in await self._active_group_links(db, source.id))
        plan = _RetrievalInvalidationPlan(source_id=source.id, user_id=source.user_id, group_ids=group_ids)

        sync_session = db.sync_session
        reg = _POST_COMMIT_INVALIDATION_REGS.get(sync_session)
        if reg is None:
            reg = {"plans": [], "tasks": []}
            _POST_COMMIT_INVALIDATION_REGS[sync_session] = reg

            def _on_commit(session: Any) -> None:
                plans = reg["plans"][:]
                reg["plans"].clear()
                if not plans:
                    return
                self._spawn_post_commit_invalidation(plans, reg)

            def _on_rollback(session: Any) -> None:
                reg["plans"].clear()

            event.listen(sync_session, "after_commit", _on_commit)
            event.listen(sync_session, "after_rollback", _on_rollback)
        reg["plans"].append(plan)
        return 1 + len(group_ids)

    def _spawn_post_commit_invalidation(
        self, plans: list[_RetrievalInvalidationPlan], reg: _InvalidationReg | None = None
    ) -> None:
        """在事件循环内 spawn 提交后失效任务（after_commit 处理器运行于循环线程）。

        任务同时登记进 session 级 reg["tasks"]，供
        ``drain_session_retrieval_invalidations`` 在请求路径上显式 await。
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error(
                "Post-commit retrieval invalidation dropped (no running loop): "
                f"sources={[str(p.source_id) for p in plans]}"
            )
            return
        task = loop.create_task(self._run_scheduled_invalidations(plans))
        if reg is not None:
            reg["tasks"].append(task)
        _PENDING_INVALIDATION_TASKS.add(task)
        task.add_done_callback(_on_invalidation_task_done)

    async def _run_scheduled_invalidations(self, plans: list[_RetrievalInvalidationPlan]) -> int:
        started = time.perf_counter()
        total = 0
        for plan in plans:
            try:
                total += await self._execute_retrieval_invalidation(plan)
            except Exception as exc:
                # 单源失效失败不阻断同批其余源；残留由读侧谓词与版本 TTL 兜底。
                logger.warning(f"Post-commit retrieval invalidation failed for source {plan.source_id}: {exc}")
        logger.info(
            "Post-commit retrieval invalidation complete: "
            f"sources={[str(p.source_id) for p in plans]} deleted_keys={total} "
            f"latency_ms={(time.perf_counter() - started) * 1000:.1f}"
        )
        return total

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
        indexed = await index_document_chunks(redis, source, chunks, db=db)
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
