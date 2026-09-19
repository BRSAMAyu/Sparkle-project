from uuid import uuid4

import pytest

from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.group_files import GroupFile
from app.services.rag_indexing_service import (
    DOCUMENT_CHUNK_PREFIX,
    GROUP_DOCUMENT_CHUNK_PREFIX,
    RAG_INDEX_PREFIXES,
    SOURCE_DOCUMENT_CHUNK,
    SOURCE_NODE_DESCRIPTION,
    build_document_chunk_document,
    build_group_document_chunk_document,
    build_knowledge_chunk_document,
    delete_document_chunk_keys,
    document_chunk_key,
    group_document_chunk_key,
    index_document_chunks,
    knowledge_chunk_key,
    rag_version_token,
    source_is_active_fresh,
)


def test_document_chunk_document_uses_requested_key_and_source_type():
    file_id = uuid4()
    user_id = uuid4()
    chunk_id = uuid4()
    file_record = StoredFile(
        id=file_id,
        user_id=user_id,
        file_name="OS_Textbook.pdf",
        mime_type="application/pdf",
        file_size=1234,
        bucket="files",
        object_key="uploads/os.pdf",
    )
    chunk = DocumentChunk(
        id=chunk_id,
        file_id=file_id,
        user_id=user_id,
        chunk_index=7,
        content="A process scheduler decides which ready process runs next.",
        embedding=[0.1, 0.2, 0.3],
        page_numbers=[42],
        section_title="CPU Scheduling",
        quality_score=0.9,
        pipeline_version="v1",
    )

    doc = build_document_chunk_document(chunk, file_record)

    assert doc["id"] == document_chunk_key(file_id, 7)
    # E-05: key 携带 embedding 版本 token（版本化命名空间，新旧模型隔离）
    token = rag_version_token()
    assert doc["id"] == f"sparkle:doc_chunk:{token}:{file_id}:7"
    assert doc["source_type"] == SOURCE_DOCUMENT_CHUNK
    assert doc["parent_id"] == str(file_id)
    assert doc["parent_name"] == "OS_Textbook.pdf"
    assert doc["chunk_id"] == str(chunk_id)
    assert doc["vector"] == [0.1, 0.2, 0.3]
    assert "CPU Scheduling" in doc["keywords"]


def test_knowledge_node_document_marks_source_type():
    node_id = uuid4()
    node = KnowledgeNode(
        id=node_id,
        name="Schedulers",
        description="Process scheduling overview",
        keywords=["os", "process"],
        importance_level=4,
        subject_id=3,
    )

    doc = build_knowledge_chunk_document(node, "Round-robin scheduling uses time slices.", [0.4, 0.5], 2)

    assert doc["id"] == knowledge_chunk_key(node_id, 2)
    assert doc["id"].startswith(f"sparkle:chunk:{rag_version_token()}:{node_id}:")
    assert doc["source_type"] == SOURCE_NODE_DESCRIPTION
    assert doc["parent_id"] == str(node_id)
    assert doc["keywords"] == "Schedulers os process"
    assert doc["vector"] == [0.4, 0.5]


def test_rag_index_prefixes_include_document_chunks():
    assert DOCUMENT_CHUNK_PREFIX in RAG_INDEX_PREFIXES
    assert GROUP_DOCUMENT_CHUNK_PREFIX in RAG_INDEX_PREFIXES


def test_group_document_chunk_document_uses_group_namespace_and_metadata():
    group_id = uuid4()
    file_id = uuid4()
    user_id = uuid4()
    group_file_id = uuid4()
    chunk_id = uuid4()
    file_record = StoredFile(
        id=file_id,
        user_id=user_id,
        file_name="CET6_Vocabulary.pdf",
        mime_type="application/pdf",
        file_size=4321,
        bucket="files",
        object_key="uploads/cet6.pdf",
    )
    group_file = GroupFile(
        id=group_file_id,
        group_id=group_id,
        file_id=file_id,
        shared_by_id=user_id,
    )
    chunk = DocumentChunk(
        id=chunk_id,
        file_id=file_id,
        user_id=user_id,
        chunk_index=2,
        content="abandon: to give up completely.",
        embedding=[0.2, 0.4, 0.6],
        page_numbers=[3],
        section_title="Word List A",
        quality_score=0.95,
        pipeline_version="v1",
    )

    doc = build_group_document_chunk_document(
        chunk,
        file_record,
        group_file,
        trust_level="verified",
    )

    assert doc["id"] == group_document_chunk_key(group_id, file_id, 2)
    assert doc["group_id"] == str(group_id)
    assert doc["shared_by_user_id"] == str(user_id)
    assert doc["trust_level"] == "verified"
    assert doc["document_scope"] == "group"


# --------------------------------------------------------------------------- #
# E-05 D4（R2 返修）：删除 × 迟到索引写竞态——写前新鲜复查 + 写后补偿清理。
# 真实 Redis（键带 uuid 无碰撞，finally 清理）；db 用可控桩模拟行存活状态。
# --------------------------------------------------------------------------- #


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeDB:
    """按调用次序返回 (lifecycle_status, deleted_at) 列值的假 AsyncSession。"""

    def __init__(self, rows):
        self._rows = list(rows)
        self.queries = 0

    async def execute(self, stmt):
        self.queries += 1
        row = self._rows.pop(0) if self._rows else ("active", None)
        return _FakeResult(row)


async def _make_index_redis():
    import os

    import redis.asyncio as redis_asyncio

    from app.config import settings
    from app.core.redis_utils import resolve_redis_password

    url = settings.REDIS_URL or "redis://localhost:6379/0"
    password, _ = resolve_redis_password(url, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    client = redis_asyncio.from_url(url, password=password, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        pytest.skip(f"redis not reachable at {url}")
    return client


def _active_file_record(file_id):
    return StoredFile(
        id=file_id,
        user_id=uuid4(),
        file_name="race.pdf",
        mime_type="application/pdf",
        file_size=10,
        bucket="files",
        object_key=f"uploads/{file_id}.pdf",
        lifecycle_status="active",
    )


def _chunks_for(file_id, n=2):
    return [
        DocumentChunk(
            id=uuid4(),
            file_id=file_id,
            user_id=uuid4(),
            chunk_index=i,
            content=f"chunk content {i}",
            embedding=[0.1, 0.2, 0.3],
            quality_score=1.0,
            pipeline_version="e05-d4",
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_index_skipped_when_db_says_deleted_despite_stale_memory():
    """写前校验：内存态 ACTIVE 但 DB 已删 → 不写入且清残留。"""
    redis = await _make_index_redis()
    file_id = uuid4()
    try:
        db = _FakeDB([("revoked", "2026-09-19 00:00:00")])  # DB 新鲜态：已软删
        indexed = await index_document_chunks(
            redis, _active_file_record(file_id), _chunks_for(file_id), db=db
        )
        assert indexed == 0
        assert db.queries == 1  # 写前复查发生了（且只发生一次——直接短路）
        assert await redis.exists(document_chunk_key(file_id, 0)) == 0
    finally:
        await delete_document_chunk_keys(redis, file_id)
        await redis.aclose()


@pytest.mark.asyncio
async def test_index_compensated_when_deleted_during_write():
    """写后补偿：写前存活、写入期间被删（复查时已死）→ 已写 key 立即清理，
    不留永久残留（原实现会永久残留，Redis JSON.SET 无 TTL）。"""
    redis = await _make_index_redis()
    file_id = uuid4()
    try:
        db = _FakeDB([("active", None), ("revoked", "2026-09-19 00:00:00")])
        indexed = await index_document_chunks(
            redis, _active_file_record(file_id), _chunks_for(file_id), db=db
        )
        assert indexed == 0  # 补偿路径按"未索引"上报
        assert db.queries == 2  # 写前 + 写后复核
        for i in range(2):
            assert await redis.exists(document_chunk_key(file_id, i)) == 0, (
                "just-written keys must be compensated (deleted) once the source is found dead"
            )
    finally:
        await delete_document_chunk_keys(redis, file_id)
        await redis.aclose()


@pytest.mark.asyncio
async def test_index_proceeds_when_source_alive():
    """对照：行存活时正常索引（写前/写后复查都放行）。"""
    redis = await _make_index_redis()
    file_id = uuid4()
    try:
        db = _FakeDB([("active", None), ("active", None)])
        indexed = await index_document_chunks(
            redis, _active_file_record(file_id), _chunks_for(file_id), db=db
        )
        assert indexed == 2
        assert await redis.exists(document_chunk_key(file_id, 0), document_chunk_key(file_id, 1)) == 2
    finally:
        await delete_document_chunk_keys(redis, file_id)
        await redis.aclose()


@pytest.mark.asyncio
async def test_source_is_active_fresh_interpretation():
    """新鲜复查的判定口径：行不存在/软删/非 ACTIVE 均为死。"""
    db = _FakeDB([])
    assert await source_is_active_fresh(db, uuid4()) is True  # 兜底默认 active（列缺省）

    db = _FakeDB([("archived", None)])
    assert await source_is_active_fresh(db, uuid4()) is False

    db = _FakeDB([("active", "2026-09-19 00:00:00")])
    assert await source_is_active_fresh(db, uuid4()) is False

    db = _FakeDB([(None, None)])
    assert await source_is_active_fresh(db, uuid4()) is True  # NULL 视为默认 ACTIVE
