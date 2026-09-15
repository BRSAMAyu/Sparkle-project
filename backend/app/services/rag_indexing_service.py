from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis

from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.group_files import GroupFile

KNOWLEDGE_CHUNK_PREFIX = "sparkle:chunk:"
DOCUMENT_CHUNK_PREFIX = "sparkle:doc_chunk:"
GROUP_DOCUMENT_CHUNK_PREFIX = "sparkle:group:"
RAG_INDEX_PREFIXES = [KNOWLEDGE_CHUNK_PREFIX, DOCUMENT_CHUNK_PREFIX, GROUP_DOCUMENT_CHUNK_PREFIX]

SOURCE_NODE_DESCRIPTION = "node_description"
SOURCE_DOCUMENT_CHUNK = "document_chunk"


def knowledge_chunk_key(node_id: Any, chunk_index: int) -> str:
    return f"{KNOWLEDGE_CHUNK_PREFIX}{node_id}:{chunk_index}"


def document_chunk_key(file_id: Any, chunk_index: int) -> str:
    return f"{DOCUMENT_CHUNK_PREFIX}{file_id}:{chunk_index}"


def group_document_chunk_key(group_id: Any, file_id: Any, chunk_index: int) -> str:
    return f"{GROUP_DOCUMENT_CHUNK_PREFIX}{group_id}:chunk:{file_id}:{chunk_index}"


def vector_to_list(vector: Any) -> list[float] | None:
    if vector is None:
        return None
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return [float(value) for value in vector]


def _keywords_to_text(keywords: Any) -> str:
    if not keywords:
        return ""
    if isinstance(keywords, str):
        return keywords
    if isinstance(keywords, Sequence) and not isinstance(keywords, (bytes, bytearray)):
        return " ".join(str(item) for item in keywords if item is not None)
    return json.dumps(keywords, ensure_ascii=True, default=str)


def build_knowledge_chunk_document(
    node: KnowledgeNode,
    chunk_text: str,
    vector: Any,
    chunk_index: int,
    expected_vector_dim: int | None = None,
) -> dict[str, Any]:
    key = knowledge_chunk_key(node.id, chunk_index)
    doc = {
        "id": key,
        "parent_id": str(node.id),
        "parent_name": node.name,
        "content": chunk_text,
        "keywords": f"{node.name} {_keywords_to_text(node.keywords)}".strip(),
        "subject_id": node.subject_id if node.subject_id is not None else 0,
        "importance": node.importance_level or 1,
        "source_type": SOURCE_NODE_DESCRIPTION,
        "node_id": str(node.id),
        "chunk_index": chunk_index,
    }
    vector_list = vector_to_list(vector)
    if vector_list is not None and (expected_vector_dim is None or len(vector_list) == expected_vector_dim):
        doc["vector"] = vector_list
    return doc


def build_document_chunk_document(
    chunk: DocumentChunk,
    file_record: StoredFile,
    expected_vector_dim: int | None = None,
) -> dict[str, Any]:
    key = document_chunk_key(chunk.file_id, chunk.chunk_index)
    section_title = chunk.section_title or ""
    page_numbers = chunk.page_numbers or []
    page_keywords = " ".join(f"page:{page}" for page in page_numbers)
    doc = {
        "id": key,
        "parent_id": str(chunk.file_id),
        "parent_name": file_record.file_name,
        "content": chunk.content,
        "keywords": f"{file_record.file_name} {section_title} {page_keywords}".strip(),
        "subject_id": 0,
        "importance": max(1, min(5, round((chunk.quality_score or 1.0) * 5))),
        "source_type": SOURCE_DOCUMENT_CHUNK,
        "file_id": str(chunk.file_id),
        "chunk_id": str(chunk.id),
        "user_id": str(chunk.user_id),
        "chunk_index": chunk.chunk_index,
        "page_numbers": page_numbers,
        "section_title": section_title,
        "quality_score": chunk.quality_score if chunk.quality_score is not None else 1.0,
        "pipeline_version": chunk.pipeline_version or "",
        "lifecycle_status": file_record.lifecycle_status or SourceLifecycleStatus.ACTIVE.value,
    }
    vector_list = vector_to_list(chunk.embedding)
    if vector_list is not None and (expected_vector_dim is None or len(vector_list) == expected_vector_dim):
        doc["vector"] = vector_list
    return doc


def build_group_document_chunk_document(
    chunk: DocumentChunk,
    file_record: StoredFile,
    group_file: GroupFile,
    *,
    trust_level: str,
    expected_vector_dim: int | None = None,
) -> dict[str, Any]:
    doc = build_document_chunk_document(
        chunk,
        file_record,
        expected_vector_dim=expected_vector_dim,
    )
    doc["id"] = group_document_chunk_key(group_file.group_id, chunk.file_id, chunk.chunk_index)
    doc["group_id"] = str(group_file.group_id)
    doc["shared_by_user_id"] = str(group_file.shared_by_id)
    doc["trust_level"] = str(trust_level or "member")
    doc["document_scope"] = "group"
    return doc


async def get_rag_redis() -> Redis | None:
    if not cache_service.redis:
        await cache_service.init_redis()
    return cache_service.redis


async def delete_document_chunk_keys(redis: Redis, file_id: UUID | str) -> int:
    pattern = document_chunk_key(file_id, "*")
    return await delete_rag_chunk_keys(redis, pattern)


async def delete_group_document_chunk_keys(redis: Redis, group_id: UUID | str, file_id: UUID | str) -> int:
    pattern = group_document_chunk_key(group_id, file_id, "*")
    return await delete_rag_chunk_keys(redis, pattern)


async def delete_rag_chunk_keys(redis: Redis, pattern: str) -> int:
    keys: list[str] = []
    deleted = 0
    async for key in redis.scan_iter(match=pattern, count=100):
        keys.append(key)
        if len(keys) >= 100:
            deleted += await redis.delete(*keys)
            keys = []
    if keys:
        deleted += await redis.delete(*keys)
    return deleted


async def index_rag_documents(redis: Redis, docs: Iterable[dict[str, Any]], batch_size: int = 100) -> int:
    pipeline = redis.pipeline()
    count = 0
    pending = 0
    for doc in docs:
        pipeline.json().set(doc["id"], "$", doc)
        count += 1
        pending += 1
        if pending >= batch_size:
            await pipeline.execute()
            pipeline = redis.pipeline()
            pending = 0
    if pending:
        await pipeline.execute()
    return count


async def index_document_chunks(
    redis: Redis,
    file_record: StoredFile,
    chunks: Iterable[DocumentChunk],
    *,
    replace_existing: bool = True,
) -> int:
    if (file_record.lifecycle_status or SourceLifecycleStatus.ACTIVE.value) != SourceLifecycleStatus.ACTIVE.value:
        if replace_existing:
            deleted = await delete_document_chunk_keys(redis, file_record.id)
            if deleted:
                logger.info(f"Deleted {deleted} Redis document chunks for inactive source {file_record.id}")
        return 0
    if replace_existing:
        deleted = await delete_document_chunk_keys(redis, file_record.id)
        if deleted:
            logger.info(f"Deleted {deleted} stale Redis document chunks for file {file_record.id}")
    return await index_rag_documents(
        redis,
        (build_document_chunk_document(chunk, file_record) for chunk in chunks),
    )


async def index_group_document_chunks(
    redis: Redis,
    group_file: GroupFile,
    file_record: StoredFile,
    chunks: Iterable[DocumentChunk],
    *,
    trust_level: str,
    replace_existing: bool = True,
) -> int:
    if (file_record.lifecycle_status or SourceLifecycleStatus.ACTIVE.value) != SourceLifecycleStatus.ACTIVE.value:
        if replace_existing:
            deleted = await delete_group_document_chunk_keys(redis, group_file.group_id, file_record.id)
            if deleted:
                logger.info(
                    f"Deleted {deleted} Redis group document chunks for inactive source {file_record.id}"
                )
        return 0
    if replace_existing:
        deleted = await delete_group_document_chunk_keys(redis, group_file.group_id, file_record.id)
        if deleted:
            logger.info(
                f"Deleted {deleted} stale Redis group document chunks for group {group_file.group_id} file {file_record.id}"
            )
    return await index_rag_documents(
        redis,
        (
            build_group_document_chunk_document(
                chunk,
                file_record,
                group_file,
                trust_level=trust_level,
            )
            for chunk in chunks
        ),
    )
