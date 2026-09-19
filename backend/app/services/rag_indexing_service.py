from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.group_files import GroupFile
from app.services.embedding_service import embedding_service

KNOWLEDGE_CHUNK_PREFIX = "sparkle:chunk:"
DOCUMENT_CHUNK_PREFIX = "sparkle:doc_chunk:"
GROUP_DOCUMENT_CHUNK_PREFIX = "sparkle:group:"
RAG_INDEX_PREFIXES = [KNOWLEDGE_CHUNK_PREFIX, DOCUMENT_CHUNK_PREFIX, GROUP_DOCUMENT_CHUNK_PREFIX]

SOURCE_NODE_DESCRIPTION = "node_description"
SOURCE_DOCUMENT_CHUNK = "document_chunk"


def rag_version_token() -> str:
    """当前 embedding 版本的 Redis 安全 token（见 EmbeddingService.current_version_token）。"""
    return embedding_service.current_version_token()


def rag_index_prefixes(version_token: str | None = None) -> list[str]:
    """给定 embedding 版本的 Redis 索引前缀（版本化 key 命名空间）。

    E-05：不同 embedding 版本的 chunk 写入不同前缀的 key，配合版本化索引名
    （idx:knowledge@{ver}），保证切换模型后新旧向量永不混入同一 KNN 查询，
    且旧版本索引天然保留、可切回（rollback 路径）。
    """
    token = version_token or rag_version_token()
    return [f"{KNOWLEDGE_CHUNK_PREFIX}{token}:", f"{DOCUMENT_CHUNK_PREFIX}{token}:", f"{GROUP_DOCUMENT_CHUNK_PREFIX}{token}:"]


def rag_index_name(version_token: str | None = None) -> str:
    """给定 embedding 版本的 RediSearch 索引名。

    旧索引名 "idx:knowledge"（无版本后缀）在 E-05 后成为 legacy 资产：
    重建脚本把它指向的数据重嵌到版本化 key 后可安全删除（--prune-legacy）。
    """
    token = version_token or rag_version_token()
    return f"idx:knowledge@{token}"


def knowledge_chunk_key(node_id: Any, chunk_index: int, version_token: str | None = None) -> str:
    token = version_token or rag_version_token()
    return f"{KNOWLEDGE_CHUNK_PREFIX}{token}:{node_id}:{chunk_index}"


def document_chunk_key(file_id: Any, chunk_index: int, version_token: str | None = None) -> str:
    token = version_token or rag_version_token()
    return f"{DOCUMENT_CHUNK_PREFIX}{token}:{file_id}:{chunk_index}"


def group_document_chunk_key(group_id: Any, file_id: Any, chunk_index: int, version_token: str | None = None) -> str:
    token = version_token or rag_version_token()
    return f"{GROUP_DOCUMENT_CHUNK_PREFIX}{token}:{group_id}:chunk:{file_id}:{chunk_index}"


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
        "embedding_model": node.embedding_model or "",
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
        "embedding_model": chunk.embedding_model or "",
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
    """删除某文件在**所有 embedding 版本**（含旧无版本格式）下的 Redis chunk key。

    E-05 delete isolation：文档删除必须即时不可见，不能因为 key 换了版本
    命名空间而漏删旧版本残留。
    """
    deleted = 0
    # 版本化格式：sparkle:doc_chunk:{ver}:{file}:{idx}
    deleted += await delete_rag_chunk_keys(redis, f"{DOCUMENT_CHUNK_PREFIX}*:{file_id}:*")
    # 旧格式（E-05 之前）：sparkle:doc_chunk:{file}:{idx}
    deleted += await delete_rag_chunk_keys(redis, f"{DOCUMENT_CHUNK_PREFIX}{file_id}:*")
    return deleted


async def delete_group_document_chunk_keys(redis: Redis, group_id: UUID | str, file_id: UUID | str) -> int:
    """删除某群组文档在**所有 embedding 版本**（含旧格式）下的 Redis chunk key。"""
    deleted = 0
    # 版本化格式：sparkle:group:{ver}:chunk:{file}:{idx}
    deleted += await delete_rag_chunk_keys(redis, f"{GROUP_DOCUMENT_CHUNK_PREFIX}*:{group_id}:chunk:{file_id}:*")
    # 旧格式：sparkle:group:{group}:chunk:{file}:{idx}
    deleted += await delete_rag_chunk_keys(redis, f"{GROUP_DOCUMENT_CHUNK_PREFIX}{group_id}:chunk:{file_id}:*")
    return deleted


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


async def source_is_active_fresh(db: AsyncSession, file_id: UUID | str) -> bool:
    """E-05 D4（R2）：对文件生命周期做**新鲜**复查（直查列值，不经 ORM 身份映射）。

    ``index_document_chunks`` 的调用方（Celery 处理链）手里的 ``file_record``
    是可能过期的内存态：处理期间文件被并发删除/归档时，删除侧的
    SCAN-DELETE 先跑完，之后落地的索引写入就无人再删（JSON.SET 无 TTL）。
    READ COMMITTED 下每条 SELECT 取新快照，能看到其它事务已提交的状态。
    """
    row = (
        await db.execute(
            select(StoredFile.lifecycle_status, StoredFile.deleted_at).where(StoredFile.id == file_id)
        )
    ).first()
    if row is None:
        return False
    lifecycle_status, deleted_at = row
    return deleted_at is None and (lifecycle_status or SourceLifecycleStatus.ACTIVE.value) == SourceLifecycleStatus.ACTIVE.value


async def index_document_chunks(
    redis: Redis,
    file_record: StoredFile,
    chunks: Iterable[DocumentChunk],
    *,
    replace_existing: bool = True,
    db: AsyncSession | None = None,
) -> int:
    """把 document chunks 写入版本化 Redis 索引。

    E-05 D4（R2）：``file_record.lifecycle_status`` 是调用方内存态，仅凭它把关
    会把"处理中被并发删除的文件"的 chunk 永久写进 Redis。传入 db 时：
    写前新鲜复查行存活（省掉无效写）；写后复核——若删除竞态发生（删除侧
    SCAN-DELETE 已先跑过、本次写入无人再删），立即补偿清理全部版本 key。
    剩余窗口仅"删除事务在校验之后才提交"的毫秒级交错，远小于原先整个
    Celery 处理时长；彻底闭环需要删除侧改为"DB 提交后再失效"（记 follow-up）。
    """
    inactive = (file_record.lifecycle_status or SourceLifecycleStatus.ACTIVE.value) != SourceLifecycleStatus.ACTIVE.value
    if db is not None and not inactive:
        # 内存态说活着——用 DB 新鲜态复核（内存态说死了则无需复查，下面统一清理）
        if not await source_is_active_fresh(db, file_record.id):
            inactive = True
    if inactive:
        if replace_existing:
            deleted = await delete_document_chunk_keys(redis, file_record.id)
            if deleted:
                logger.info(f"Deleted {deleted} Redis document chunks for inactive source {file_record.id}")
        return 0
    if replace_existing:
        deleted = await delete_document_chunk_keys(redis, file_record.id)
        if deleted:
            logger.info(f"Deleted {deleted} stale Redis document chunks for file {file_record.id}")
    indexed = await index_rag_documents(
        redis,
        (build_document_chunk_document(chunk, file_record) for chunk in chunks),
    )
    if db is not None and indexed and not await source_is_active_fresh(db, file_record.id):
        # D4 写后补偿：索引写入与删除竞态（删除的 SCAN-DELETE 已先跑过）→
        # 本次写入的 key 不会再被任何人删除，立即清理，杜绝永久残留。
        compensated = await delete_document_chunk_keys(redis, file_record.id)
        logger.warning(
            f"E-05 D4 compensation: source {file_record.id} deactivated during indexing; "
            f"removed {compensated} just-written chunk key(s)"
        )
        return 0
    return indexed


async def index_group_document_chunks(
    redis: Redis,
    group_file: GroupFile,
    file_record: StoredFile,
    chunks: Iterable[DocumentChunk],
    *,
    trust_level: str,
    replace_existing: bool = True,
    db: AsyncSession | None = None,
) -> int:
    """把群组文档 chunks 写入版本化 Redis 索引（D4 语义同 index_document_chunks）。"""
    inactive = (file_record.lifecycle_status or SourceLifecycleStatus.ACTIVE.value) != SourceLifecycleStatus.ACTIVE.value
    if db is not None and not inactive:
        if not await source_is_active_fresh(db, file_record.id):
            inactive = True
    if inactive:
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
    indexed = await index_rag_documents(
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
    if db is not None and indexed and not await source_is_active_fresh(db, file_record.id):
        compensated = await delete_group_document_chunk_keys(redis, group_file.group_id, file_record.id)
        logger.warning(
            f"E-05 D4 compensation: source {file_record.id} deactivated during group indexing; "
            f"removed {compensated} just-written chunk key(s)"
        )
        return 0
    return indexed
