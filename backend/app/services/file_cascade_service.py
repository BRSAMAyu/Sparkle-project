"""
文件删除级联服务
处理文件删除时的级联操作：
- 删除关联的 document_chunks
- 删除关联的 knowledge_nodes (draft)
- 删除关联的 embeddings
- 清理 MinIO 存储
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from loguru import logger

from app.models.file_storage import StoredFile
from app.models.document_chunks import DocumentChunk
from app.models.galaxy import KnowledgeNode
from app.config.phase5_config import phase5_config


class FileCascadeService:
    """
    文件级联删除服务

    支持两种删除模式：
    1. 软删除：标记 deleted_at，保留数据一段时间
    2. 硬删除：物理删除数据库记录和文件存储
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def soft_delete_file(
        self,
        file_id: UUID,
        user_id: Optional[UUID] = None
    ) -> dict:
        """
        软删除文件及其关联数据

        流程：
        1. 标记文件为已删除
        2. 标记关联的 chunks 为已删除
        3. 标记关联的草稿节点为已删除
        4. 记录删除日志

        Args:
            file_id: 文件 ID
            user_id: 执行删除的用户 ID（权限检查）

        Returns:
            dict: 删除操作的统计信息
        """
        now = datetime.utcnow()
        stats = {
            "file_deleted": False,
            "chunks_deleted": 0,
            "nodes_deleted": 0,
            "errors": []
        }

        try:
            # 1. 获取并验证文件
            file_stmt = select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.deleted_at.is_(None)
            )

            if user_id:
                file_stmt = file_stmt.where(StoredFile.user_id == user_id)

            result = await self.db.execute(file_stmt)
            file = result.scalar_one_or_none()

            if not file:
                stats["errors"].append(f"File {file_id} not found or already deleted")
                return stats

            # 2. 软删除文件记录
            file.deleted_at = now
            stats["file_deleted"] = True

            logger.info(f"Soft deleted file {file_id}: {file.file_name}")

            # 3. 软删除关联的 document_chunks
            if phase5_config.DELETION_CASCADE_EMBEDDINGS:
                chunks_stmt = (
                    update(DocumentChunk)
                    .where(
                        DocumentChunk.file_id == file_id,
                        DocumentChunk.deleted_at.is_(None)
                    )
                    .values(deleted_at=now)
                )
                chunks_result = await self.db.execute(chunks_stmt)
                stats["chunks_deleted"] = chunks_result.rowcount

                logger.info(f"Soft deleted {stats['chunks_deleted']} chunks for file {file_id}")

            # 4. 软删除关联的草稿节点
            if phase5_config.DELETION_CASCADE_DRAFT_NODES:
                nodes_stmt = (
                    update(KnowledgeNode)
                    .where(
                        KnowledgeNode.source_file_id == file_id,
                        KnowledgeNode.status == "draft",
                        KnowledgeNode.deleted_at.is_(None)
                    )
                    .values(deleted_at=now)
                )
                nodes_result = await self.db.execute(nodes_stmt)
                stats["nodes_deleted"] = nodes_result.rowcount

                logger.info(f"Soft deleted {stats['nodes_deleted']} draft nodes for file {file_id}")

            # 5. 提交事务
            await self.db.commit()

            logger.success(f"Soft delete cascade completed for file {file_id}: {stats}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Soft delete cascade failed for file {file_id}: {e}")
            stats["errors"].append(str(e))

        return stats

    async def hard_delete_file(
        self,
        file_id: UUID,
        user_id: Optional[UUID] = None,
        force: bool = False
    ) -> dict:
        """
        硬删除文件及其关联数据（不可恢复）

        流程：
        1. 验证权限
        2. 物理删除 chunks（如果配置启用）
        3. 物理删除草稿节点（如果配置启用）
        4. 删除 MinIO 文件（TODO）
        5. 物理删除文件记录

        Args:
            file_id: 文件 ID
            user_id: 执行删除的用户 ID
            force: 是否强制删除（跳过软删除检查）

        Returns:
            dict: 删除操作的统计信息
        """
        stats = {
            "file_deleted": False,
            "chunks_deleted": 0,
            "nodes_deleted": 0,
            "storage_deleted": False,
            "errors": []
        }

        try:
            # 1. 获取并验证文件
            file_stmt = select(StoredFile).where(StoredFile.id == file_id)

            if user_id:
                file_stmt = file_stmt.where(StoredFile.user_id == user_id)

            result = await self.db.execute(file_stmt)
            file = result.scalar_one_or_none()

            if not file:
                stats["errors"].append(f"File {file_id} not found")
                return stats

            # 2. 检查是否需要先软删除
            if not force and phase5_config.DELETION_SOFT_DELETE:
                if file.deleted_at is None:
                    stats["errors"].append(
                        "File must be soft-deleted first. "
                        "Use soft_delete_file() or pass force=True"
                    )
                    return stats

                # 检查保留期是否已过
                retention_days = phase5_config.DELETION_RETENTION_DAYS
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

                if file.deleted_at > cutoff_date:
                    stats["errors"].append(
                        f"File is within retention period ({retention_days} days). "
                        f"Can be permanently deleted after {file.deleted_at + timedelta(days=retention_days)}"
                    )
                    return stats

            # 3. 物理删除 chunks
            if phase5_config.DELETION_CASCADE_EMBEDDINGS:
                chunks_stmt = delete(DocumentChunk).where(
                    DocumentChunk.file_id == file_id
                )
                chunks_result = await self.db.execute(chunks_stmt)
                stats["chunks_deleted"] = chunks_result.rowcount

                logger.info(f"Hard deleted {stats['chunks_deleted']} chunks for file {file_id}")

            # 4. 物理删除草稿节点
            if phase5_config.DELETION_CASCADE_DRAFT_NODES:
                # 先查找关联的节点
                nodes_stmt = select(KnowledgeNode).where(
                    KnowledgeNode.source_file_id == file_id,
                    KnowledgeNode.status == "draft"
                )
                nodes_result = await self.db.execute(nodes_stmt)
                nodes = nodes_result.scalars().all()

                # 删除节点（注意外键约束）
                for node in nodes:
                    await self.db.delete(node)
                    stats["nodes_deleted"] += 1

                logger.info(f"Hard deleted {stats['nodes_deleted']} draft nodes for file {file_id}")

            # 5. TODO: 删除 MinIO 存储
            # 这需要 MinIO 客户端，暂时跳过
            # if file.object_key:
            #     await minio_client.remove_object(bucket, file.object_key)
            #     stats["storage_deleted"] = True

            # 6. 物理删除文件记录
            await self.db.delete(file)
            stats["file_deleted"] = True

            # 7. 提交事务
            await self.db.commit()

            logger.success(f"Hard delete cascade completed for file {file_id}: {stats}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Hard delete cascade failed for file {file_id}: {e}")
            stats["errors"].append(str(e))

        return stats

    async def cleanup_expired_soft_deletes(self) -> dict:
        """
        清理过期的软删除记录（超过保留期）

        定期任务调用，清理超过保留期的软删除数据

        Returns:
            dict: 清理统计
        """
        stats = {
            "files_cleaned": 0,
            "chunks_cleaned": 0,
            "nodes_cleaned": 0,
            "errors": []
        }

        try:
            retention_days = phase5_config.DELETION_RETENTION_DAYS
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # 1. 查找过期的软删除文件
            expired_files_stmt = select(StoredFile).where(
                StoredFile.deleted_at.isnot(None),
                StoredFile.deleted_at < cutoff_date
            )

            result = await self.db.execute(expired_files_stmt)
            expired_files = result.scalars().all()

            logger.info(f"Found {len(expired_files)} expired soft-deleted files")

            # 2. 硬删除每个过期文件
            for file in expired_files:
                file_stats = await self.hard_delete_file(
                    file.id,
                    force=True  # 已经检查过期时间，强制删除
                )

                if not file_stats["errors"]:
                    stats["files_cleaned"] += 1
                    stats["chunks_cleaned"] += file_stats["chunks_deleted"]
                    stats["nodes_cleaned"] += file_stats["nodes_deleted"]
                else:
                    stats["errors"].extend(file_stats["errors"])

            logger.success(f"Cleanup completed: {stats}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            stats["errors"].append(str(e))

        return stats

    async def restore_soft_deleted_file(
        self,
        file_id: UUID,
        user_id: Optional[UUID] = None
    ) -> dict:
        """
        恢复软删除的文件

        Args:
            file_id: 文件 ID
            user_id: 执行恢复的用户 ID

        Returns:
            dict: 恢复操作的统计信息
        """
        stats = {
            "file_restored": False,
            "chunks_restored": 0,
            "nodes_restored": 0,
            "errors": []
        }

        try:
            # 1. 查找软删除的文件
            file_stmt = select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.deleted_at.isnot(None)
            )

            if user_id:
                file_stmt = file_stmt.where(StoredFile.user_id == user_id)

            result = await self.db.execute(file_stmt)
            file = result.scalar_one_or_none()

            if not file:
                stats["errors"].append(f"Soft-deleted file {file_id} not found")
                return stats

            # 2. 恢复文件
            file.deleted_at = None
            stats["file_restored"] = True

            # 3. 恢复关联的 chunks
            chunks_stmt = (
                update(DocumentChunk)
                .where(
                    DocumentChunk.file_id == file_id,
                    DocumentChunk.deleted_at.isnot(None)
                )
                .values(deleted_at=None)
            )
            chunks_result = await self.db.execute(chunks_stmt)
            stats["chunks_restored"] = chunks_result.rowcount

            # 4. 恢复关联的节点
            nodes_stmt = (
                update(KnowledgeNode)
                .where(
                    KnowledgeNode.source_file_id == file_id,
                    KnowledgeNode.status == "draft",
                    KnowledgeNode.deleted_at.isnot(None)
                )
                .values(deleted_at=None)
            )
            nodes_result = await self.db.execute(nodes_stmt)
            stats["nodes_restored"] = nodes_result.rowcount

            # 5. 提交事务
            await self.db.commit()

            logger.success(f"File {file_id} restored: {stats}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Restore failed for file {file_id}: {e}")
            stats["errors"].append(str(e))

        return stats

    async def get_cascade_preview(
        self,
        file_id: UUID
    ) -> dict:
        """
        预览删除文件将影响的数据

        不执行实际删除，只返回统计信息

        Args:
            file_id: 文件 ID

        Returns:
            dict: 受影响的数据统计
        """
        preview = {
            "file_exists": False,
            "file_name": None,
            "chunks_count": 0,
            "draft_nodes_count": 0,
            "published_nodes_count": 0,
            "warning": None
        }

        try:
            # 1. 查找文件
            file_stmt = select(StoredFile).where(StoredFile.id == file_id)
            result = await self.db.execute(file_stmt)
            file = result.scalar_one_or_none()

            if not file:
                return preview

            preview["file_exists"] = True
            preview["file_name"] = file.file_name

            # 2. 统计 chunks
            chunks_stmt = select(func.count(DocumentChunk.id)).where(
                DocumentChunk.file_id == file_id,
                DocumentChunk.deleted_at.is_(None)
            )
            chunks_result = await self.db.execute(chunks_stmt)
            preview["chunks_count"] = chunks_result.scalar()

            # 3. 统计草稿节点
            draft_nodes_stmt = select(func.count(KnowledgeNode.id)).where(
                KnowledgeNode.source_file_id == file_id,
                KnowledgeNode.status == "draft",
                KnowledgeNode.deleted_at.is_(None)
            )
            draft_result = await self.db.execute(draft_nodes_stmt)
            preview["draft_nodes_count"] = draft_result.scalar()

            # 4. 统计已发布节点
            published_nodes_stmt = select(func.count(KnowledgeNode.id)).where(
                KnowledgeNode.source_file_id == file_id,
                KnowledgeNode.status == "published",
                KnowledgeNode.deleted_at.is_(None)
            )
            published_result = await self.db.execute(published_nodes_stmt)
            preview["published_nodes_count"] = published_result.scalar()

            # 5. 警告
            if preview["published_nodes_count"] > 0:
                preview["warning"] = (
                    f"This file has {preview['published_nodes_count']} published knowledge nodes. "
                    "Deleting this file may break existing knowledge relationships."
                )

        except Exception as e:
            logger.error(f"Preview failed for file {file_id}: {e}")
            preview["error"] = str(e)

        return preview


# 便利函数

async def cascade_delete_file(
    db: AsyncSession,
    file_id: UUID,
    user_id: Optional[UUID] = None,
    hard: bool = False,
    force: bool = False
) -> dict:
    """
    删除文件的快捷函数

    Args:
        db: 数据库会话
        file_id: 文件 ID
        user_id: 用户 ID
        hard: 是否硬删除
        force: 是否强制删除（硬删除时有效）

    Returns:
        dict: 删除统计
    """
    service = FileCascadeService(db)

    if hard:
        return await service.hard_delete_file(file_id, user_id, force)
    else:
        return await service.soft_delete_file(file_id, user_id)
