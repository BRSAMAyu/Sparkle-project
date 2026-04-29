"""
File processing orchestrator
文件处理编排服务
"""
from __future__ import annotations

import json
import os
import tempfile
from uuid import UUID

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.task_monitor import task_monitor_service
from app.models.background_task import BackgroundTaskStatus, BackgroundTaskType
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.group_files import GroupFile
from app.services.document_service import document_service
from app.services.document_upload_storage import document_upload_storage
from app.services.embedding_service import embedding_service
from app.services.openclaw.url_guard import stream_download_to_path
from app.services.rag_indexing_service import (
    delete_group_document_chunk_keys,
    get_rag_redis,
    index_document_chunks,
    index_group_document_chunks,
)
from app.services.thumbnail_service import thumbnail_service


class FileProcessingOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_file(
        self,
        file_id: UUID,
        user_id: UUID,
        download_url: str,
        file_name: str,
        mime_type: str,
        thumbnail_upload_url: str | None = None,
        external_task_id: str | None = None,
    ) -> dict:
        file_record = await self.db.get(StoredFile, file_id)
        if not file_record or file_record.user_id != user_id:
            raise ValueError("File record not found")

        await self._update_status(file_record, "processing")
        await self._publish_status(
            file_id,
            user_id,
            "processing",
            10,
            external_task_id=external_task_id,
            file_name=file_name,
        )

        temp_path = await self._download_file(download_url, file_name)
        try:
            chunks = await document_service.extract_vector_chunks(temp_path)
            if not chunks:
                raise ValueError("No extractable content for vectorization")

            # 1. Quality Check
            quality = document_service.check_quality(chunks)
            if not quality.passed:
                error_msg = f"Quality Gate Failed: {'; '.join(quality.issues)}"
                await self._update_status(file_record, "failed", error_message=error_msg)
                await self._publish_status(
                    file_id,
                    user_id,
                    "failed",
                    100,
                    error=error_msg,
                    external_task_id=external_task_id,
                    file_name=file_name,
                )
                return {"status": "failed", "error": error_msg}

            await self._replace_chunks(file_id)
            stored_chunks = await self._store_chunks(file_id, user_id, chunks, quality.score, document_title=file_name)
            await self._index_chunks_realtime(file_record, stored_chunks)

            await self._publish_status(
                file_id,
                user_id,
                "processing",
                80,
                external_task_id=external_task_id,
                file_name=file_name,
            )

            # 2. Drafting
            await document_service.draft_knowledge_nodes(self.db, file_id, user_id, chunks)

            await thumbnail_service.generate_and_upload(temp_path, file_id, thumbnail_upload_url)

            await self._update_status(file_record, "processed")
            await self._publish_status(
                file_id,
                user_id,
                "processed",
                100,
                external_task_id=external_task_id,
                file_name=file_name,
            )

            # V-14: Notify Spine of file upload for signal pipeline
            try:
                from app.signals.spine_orchestrator import SpineOrchestrator
                from app.core.redis_client import get_redis
                spine = SpineOrchestrator(redis=get_redis())
                summary = chunks[0].get("text", "")[:500] if chunks else ""
                await spine.on_file_uploaded(
                    user_id=str(user_id),
                    file_id=str(file_id),
                    filename=file_name,
                    parsed_summary=summary,
                    mime_type=file_record.mime_type or "application/octet-stream",
                )
            except Exception as spine_err:
                logger.debug("Spine on_file_uploaded skipped: {}", spine_err)

            return {"status": "processed", "file_id": str(file_id)}
        except Exception as exc:
            await self._update_status(file_record, "failed", error_message=str(exc))
            await self._publish_status(
                file_id,
                user_id,
                "failed",
                100,
                error=str(exc),
                external_task_id=external_task_id,
                file_name=file_name,
            )
            raise
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def _download_file(self, download_url: str, file_name: str) -> str:
        suffix = os.path.splitext(file_name)[1] or ".bin"
        handle, temp_path = tempfile.mkstemp(prefix="file_process_", suffix=suffix)
        os.close(handle)
        await stream_download_to_path(download_url, temp_path)
        return temp_path

    async def _replace_chunks(self, file_id: UUID) -> None:
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.file_id == file_id))
        await self.db.commit()

    async def _store_chunks(
        self,
        file_id: UUID,
        user_id: UUID,
        chunks,
        quality_score: float = 1.0,
        document_title: str | None = None,
    ) -> list[DocumentChunk]:
        texts = await document_service.build_contextual_embedding_texts(
            document_title=document_title or str(file_id),
            chunks=chunks,
        )
        batch_size = 16
        index = 0
        stored_chunks: list[DocumentChunk] = []

        while index < len(texts):
            batch_texts = texts[index:index + batch_size]
            embeddings = await embedding_service.batch_embeddings(batch_texts, text_type="document")
            if len(embeddings) != len(batch_texts):
                raise RuntimeError(f"Embedding count mismatch: expected {len(batch_texts)}, got {len(embeddings)}")
            items = []
            for offset, (chunk, embedding) in enumerate(zip(chunks[index:index + batch_size], embeddings, strict=True)):
                if embedding is None or len(embedding) != settings.EMBEDDING_DIM:
                    actual_dim = len(embedding) if embedding is not None else 0
                    raise RuntimeError(
                        f"Invalid embedding for chunk {index + offset}: "
                        f"expected {settings.EMBEDDING_DIM}, got {actual_dim}"
                    )
                items.append(DocumentChunk(
                    file_id=file_id,
                    user_id=user_id,
                    chunk_index=index + offset,
                    page_numbers=chunk.page_numbers, # JSON list
                    section_title=chunk.section_title,
                    content=chunk.content,
                    embedding=embedding,
                    quality_score=quality_score,
                    pipeline_version="v1"
                ))
            self.db.add_all(items)
            await self.db.commit()
            stored_chunks.extend(items)
            index += batch_size
        return stored_chunks

    async def _index_chunks_realtime(self, file_record: StoredFile, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        try:
            redis = await get_rag_redis()
            if not redis:
                logger.warning(f"Skipping real-time RAG indexing for file {file_record.id}: Redis unavailable")
                return
            indexed = await index_document_chunks(redis, file_record, chunks, replace_existing=True)
            logger.info(f"Indexed {indexed} document chunks to Redis for file {file_record.id}")
        except Exception as exc:
            logger.warning(f"Failed to index document chunks to Redis for file {file_record.id}: {exc}")

    async def process_group_file(
        self,
        *,
        group_id: UUID,
        file_id: UUID,
        shared_by_user_id: UUID,
        external_task_id: str | None = None,
    ) -> dict:
        group_file = await self.db.scalar(
            select(GroupFile).where(
                GroupFile.group_id == group_id,
                GroupFile.file_id == file_id,
                GroupFile.not_deleted_filter(),
            )
        )
        if not group_file:
            await self.delete_group_file_index(group_id=group_id, file_id=file_id)
            return {
                "status": "deleted",
                "group_id": str(group_id),
                "file_id": str(file_id),
            }

        file_record = await self.db.get(StoredFile, file_id)
        if not file_record or file_record.is_deleted:
            await self.delete_group_file_index(group_id=group_id, file_id=file_id)
            raise ValueError("Stored file not found for group indexing")

        chunks = await self._load_chunks(file_id)
        if not chunks:
            if file_record.status in {"uploading", "queued", "processing"}:
                raise RuntimeError(f"Source file {file_id} is not ready for group indexing")
            download_url = document_upload_storage.create_presigned_get_url(object_key=file_record.object_key)
            await self.process_file(
                file_id=file_id,
                user_id=file_record.user_id,
                download_url=download_url,
                file_name=file_record.file_name,
                mime_type=file_record.mime_type,
                external_task_id=external_task_id,
            )
            chunks = await self._load_chunks(file_id)
            if not chunks:
                raise RuntimeError(f"No document chunks available for group file {file_id}")

        trust_level = str(getattr(group_file.trust_level, "value", group_file.trust_level) or "member")
        indexed = await self._index_group_chunks_realtime(
            group_file=group_file,
            file_record=file_record,
            chunks=chunks,
            trust_level=trust_level,
        )
        return {
            "status": "processed",
            "group_id": str(group_id),
            "file_id": str(file_id),
            "shared_by_user_id": str(shared_by_user_id),
            "indexed_chunks": indexed,
        }

    async def delete_group_file_index(self, *, group_id: UUID, file_id: UUID) -> dict:
        redis = await get_rag_redis()
        if not redis:
            return {
                "status": "skipped",
                "group_id": str(group_id),
                "file_id": str(file_id),
                "deleted_chunks": 0,
            }
        deleted = await delete_group_document_chunk_keys(redis, group_id, file_id)
        return {
            "status": "deleted",
            "group_id": str(group_id),
            "file_id": str(file_id),
            "deleted_chunks": deleted,
        }

    async def _load_chunks(self, file_id: UUID) -> list[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.file_id == file_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def _index_group_chunks_realtime(
        self,
        *,
        group_file: GroupFile,
        file_record: StoredFile,
        chunks: list[DocumentChunk],
        trust_level: str,
    ) -> int:
        if not chunks:
            return 0
        try:
            redis = await get_rag_redis()
            if not redis:
                logger.warning(
                    f"Skipping real-time group RAG indexing for group {group_file.group_id} file {file_record.id}: Redis unavailable"
                )
                return 0
            indexed = await index_group_document_chunks(
                redis,
                group_file,
                file_record,
                chunks,
                trust_level=trust_level,
                replace_existing=True,
            )
            logger.info(
                f"Indexed {indexed} group document chunks to Redis for group {group_file.group_id} file {file_record.id}"
            )
            return indexed
        except Exception as exc:
            logger.warning(
                f"Failed to index group document chunks to Redis for group {group_file.group_id} file {file_record.id}: {exc}"
            )
            return 0

    async def _update_status(self, record: StoredFile, status: str, error_message: str | None = None) -> None:
        record.status = status
        record.error_message = error_message
        self.db.add(record)
        await self.db.commit()

    async def _publish_status(
        self,
        file_id: UUID,
        user_id: UUID,
        status: str,
        progress: int,
        error: str | None = None,
        external_task_id: str | None = None,
        file_name: str | None = None,
    ) -> None:
        if not cache_service.redis:
            await cache_service.init_redis()
        if not cache_service.redis:
            return
        payload = {
            "type": "file_status",
            "file_id": str(file_id),
            "user_id": str(user_id),
            "status": status,
            "progress": progress,
        }
        if error:
            payload["error"] = error[:200]
        try:
            await cache_service.redis.publish("file_status", json.dumps(payload, ensure_ascii=True))
        except Exception as exc:
            logger.warning(f"Failed to publish file status: {exc}")
        await task_monitor_service.publish_progress(
            user_id=user_id,
            task_type=BackgroundTaskType.DATA_SYNC,
            name=f"文档分析: {file_name or file_id}",
            status={
                "processing": BackgroundTaskStatus.RUNNING,
                "processed": BackgroundTaskStatus.COMPLETED,
                "failed": BackgroundTaskStatus.FAILED,
            }.get(status, BackgroundTaskStatus.PENDING),
            progress=max(0.0, min(progress / 100.0, 1.0)),
            progress_message=(
                "AI 正在分析知识结构..."
                if status == "processing" and progress >= 70
                else ("处理完成" if status == "processed" else (error or status))
            ),
            external_task_id=external_task_id,
            related_entity_id=file_id,
            related_entity_type="stored_file",
            result_data={"file_id": str(file_id), "status": status} if status == "processed" else None,
            error_message=error,
        )
