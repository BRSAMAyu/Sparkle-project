"""
File processing orchestrator
文件处理编排服务
"""
import json
import os
import tempfile
from typing import Optional
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.services.document_service import document_service
from app.services.embedding_service import embedding_service
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
        thumbnail_upload_url: Optional[str] = None,
    ) -> dict:
        file_record = await self.db.get(StoredFile, file_id)
        if not file_record or file_record.user_id != user_id:
            raise ValueError("File record not found")

        await self._update_status(file_record, "processing")
        await self._publish_status(file_id, user_id, "processing", 10)

        temp_path = await self._download_file(download_url, file_name)
        try:
            chunks = await document_service.extract_vector_chunks(temp_path)
            if not chunks:
                raise ValueError("No extractable content for vectorization")

            await self._replace_chunks(file_id)
            await self._store_chunks(file_id, user_id, chunks)

            await self._publish_status(file_id, user_id, "processing", 80)

            await thumbnail_service.generate_and_upload(temp_path, file_id, thumbnail_upload_url)

            await self._update_status(file_record, "processed")
            await self._publish_status(file_id, user_id, "processed", 100)

            return {"status": "processed", "file_id": str(file_id)}
        except Exception as exc:
            await self._update_status(file_record, "failed", error_message=str(exc))
            await self._publish_status(file_id, user_id, "failed", 100, error=str(exc))
            raise
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def _download_file(self, download_url: str, file_name: str) -> str:
        suffix = os.path.splitext(file_name)[1] or ".bin"
        handle, temp_path = tempfile.mkstemp(prefix="file_process_", suffix=suffix)
        os.close(handle)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            with open(temp_path, "wb") as outfile:
                async for chunk in resp.aiter_bytes():
                    outfile.write(chunk)

        return temp_path

    async def _replace_chunks(self, file_id: UUID) -> None:
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.file_id == file_id))
        await self.db.commit()

    async def _store_chunks(self, file_id: UUID, user_id: UUID, chunks) -> None:
        texts = [chunk.content for chunk in chunks]
        batch_size = 16
        index = 0

        while index < len(texts):
            batch_texts = texts[index:index + batch_size]
            embeddings = await embedding_service.batch_embeddings(batch_texts)
            items = []
            for offset, (chunk, embedding) in enumerate(zip(chunks[index:index + batch_size], embeddings)):
                items.append(DocumentChunk(
                    file_id=file_id,
                    user_id=user_id,
                    chunk_index=index + offset,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    embedding=embedding,
                ))
            self.db.add_all(items)
            await self.db.commit()
            index += batch_size

    async def _update_status(self, record: StoredFile, status: str, error_message: Optional[str] = None) -> None:
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
        error: Optional[str] = None,
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
