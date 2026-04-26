from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.task import Task
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.task_document_service import task_document_service


class FocusContextService:
    """Preload and retrieve task-scoped document context for focus sessions."""

    CACHE_TTL_SECONDS = 2 * 60 * 60
    CACHE_VERSION = 1

    @classmethod
    def _cache_key(cls, *, user_id: UUID, task_id: UUID) -> str:
        return f"focus_context_pool:v{cls.CACHE_VERSION}:{user_id}:{task_id}"

    @classmethod
    async def invalidate_for_task(cls, *, user_id: UUID, task_id: UUID) -> None:
        await cache_service.delete(cls._cache_key(user_id=user_id, task_id=task_id))

    @classmethod
    async def preload_for_task(
        cls,
        db: AsyncSession,
        *,
        user_id: UUID,
        task: Task,
        seed_query: str | None = None,
        max_chunks: int | None = None,
    ) -> dict[str, Any]:
        if not settings.ENABLE_FOCUS_DOCUMENT_CONTEXT:
            return {"task_id": str(task.id), "file_count": 0, "chunks": []}

        await task_document_service.ensure_focus_documents(db, task=task)
        file_ids = await task_document_service.resolve_focus_file_ids(db, task=task)
        if not file_ids:
            payload = {"task_id": str(task.id), "file_count": 0, "chunks": []}
            await cache_service.set(cls._cache_key(user_id=user_id, task_id=task.id), payload, ttl=cls.CACHE_TTL_SECONDS)
            return payload

        chunks = await cls._retrieve_chunks(
            db,
            user_id=user_id,
            file_ids=file_ids,
            query=seed_query or task.title,
            max_chunks=max_chunks or settings.DOCUMENT_CONTEXT_MAX_CHUNKS,
        )
        payload = {
            "task_id": str(task.id),
            "file_ids": [str(file_id) for file_id in file_ids],
            "file_count": len(file_ids),
            "chunks": chunks,
        }
        await cache_service.set(cls._cache_key(user_id=user_id, task_id=task.id), payload, ttl=cls.CACHE_TTL_SECONDS)
        return payload

    @classmethod
    async def get_guidance_context(
        cls,
        db: AsyncSession,
        *,
        user_id: UUID,
        task: Task,
        task_context: str,
        user_query: str,
        max_chunks: int | None = None,
    ) -> str:
        if not settings.ENABLE_FOCUS_DOCUMENT_CONTEXT:
            return ""

        cache_key = cls._cache_key(user_id=user_id, task_id=task.id)
        cached = await cache_service.get(cache_key)
        if not cached:
            cached = await cls.preload_for_task(
                db,
                user_id=user_id,
                task=task,
                seed_query=task_context or task.title,
                max_chunks=max_chunks,
            )

        file_ids = [UUID(file_id) for file_id in (cached.get("file_ids") or [])]
        if not file_ids:
            return ""

        ranked_chunks = cls._rank_cached_chunks(cached.get("chunks") or [], user_query, limit=max_chunks)
        if not ranked_chunks:
            ranked_chunks = await cls._retrieve_chunks(
                db,
                user_id=user_id,
                file_ids=file_ids,
                query=user_query or task_context or task.title,
                max_chunks=max_chunks or settings.DOCUMENT_CONTEXT_MAX_CHUNKS,
            )
            cached["chunks"] = ranked_chunks
            await cache_service.set(cache_key, cached, ttl=cls.CACHE_TTL_SECONDS)

        return cls._format_chunks(ranked_chunks[: max_chunks or settings.DOCUMENT_CONTEXT_MAX_CHUNKS])

    @classmethod
    async def _retrieve_chunks(
        cls,
        db: AsyncSession,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        query: str,
        max_chunks: int,
    ) -> list[dict[str, Any]]:
        retriever = KnowledgeRetrievalService(db)
        try:
            results = await retriever.document_vector_search(
                user_id=user_id,
                query=query or "",
                file_ids=file_ids,
                limit=max_chunks,
            )
        except Exception:
            results = []
        if results:
            return [
                cls._serialize_chunk(
                    chunk=result.chunk,
                    file_name=result.file_name,
                    score=result.score,
                    source="vector_search",
                )
                for result in results
            ]

        rows = (
            await db.execute(
                select(DocumentChunk, StoredFile.file_name)
                .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
                .where(DocumentChunk.user_id == user_id)
                .where(DocumentChunk.file_id.in_(file_ids))
                .where(DocumentChunk.deleted_at.is_(None))
                .order_by(DocumentChunk.quality_score.desc().nulls_last(), DocumentChunk.chunk_index.asc())
                .limit(max_chunks)
            )
        ).all()
        return [
            cls._serialize_chunk(
                chunk=chunk,
                file_name=file_name,
                score=float(getattr(chunk, "quality_score", 0.0) or 0.0),
                source="fallback_quality",
            )
            for chunk, file_name in rows
        ]

    @staticmethod
    def _serialize_chunk(
        *,
        chunk: DocumentChunk,
        file_name: str,
        score: float,
        source: str,
    ) -> dict[str, Any]:
        return {
            "file_id": str(chunk.file_id),
            "file_name": file_name,
            "chunk_id": str(chunk.id),
            "chunk_index": int(chunk.chunk_index or 0),
            "section_title": chunk.section_title,
            "page_numbers": list(chunk.page_numbers or []),
            "content": chunk.content,
            "score": float(score),
            "source": source,
        }

    @staticmethod
    def _rank_cached_chunks(chunks: list[dict[str, Any]], query: str, *, limit: int | None) -> list[dict[str, Any]]:
        normalized_terms = {
            token for token in "".join(char.lower() if char.isalnum() else " " for char in (query or "")).split() if token
        }
        if not normalized_terms:
            return chunks[: limit or len(chunks)]

        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in chunks:
            text = " ".join(
                str(part or "")
                for part in (chunk.get("file_name"), chunk.get("section_title"), chunk.get("content"))
            ).lower()
            overlap = sum(1 for term in normalized_terms if term in text)
            score = float(chunk.get("score") or 0.0) + overlap
            if overlap:
                scored.append((score, chunk))

        if not scored:
            return chunks[: limit or len(chunks)]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[: limit or len(scored)]]

    @staticmethod
    def _format_chunks(chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return ""

        parts = ["[Focus Study Context]"]
        for chunk in chunks:
            page_numbers = list(chunk.get("page_numbers") or [])
            page_label = ""
            if page_numbers:
                page_label = f" | Pages: {', '.join(str(page) for page in page_numbers[:3])}"
            section = str(chunk.get("section_title") or "—").strip()
            parts.append(f"[Source: {chunk.get('file_name')} | Section: {section}{page_label}]")
            parts.append(str(chunk.get("content") or "").strip())
            parts.append("")
        return "\n".join(parts).rstrip()


focus_context_service = FocusContextService()
