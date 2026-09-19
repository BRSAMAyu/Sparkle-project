"""E-05 集成守卫（真实 PostgreSQL + pgvector + 真实 embedding API）。

运行条件（保护常规 pytest）：
    E05_LIVE=1 且 backend/.env 有真实 key 且 DATABASE_URL 指向 pgvector 库。
    pytest -m postgres tests/services/test_document_retrieval_isolation.py

覆盖验收：
1. wrong-user=0：两用户各建文档，vector/lexical/hybrid 三路检索零串扰；
2. version isolation：标记为其他 embedding 模型的 chunk 不参与当前检索
   （strict 与过渡 lenient 模式一致排除"不同版本"）；
3. delete isolation：删除文档后——
   a) pgvector 检索立即不可见（lifecycle + 软删谓词）；
   b) Redis 版本化 RAG key 立即删除（含旧版本残留路径）；
   c) 语义缓存因 knowledge_version 变化立即不可命中（删的是非最新行也成立；
      R2 D2 口径：knowledge:version:v1 缓存键本身必须被失效，验证走真实缓存层）。
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.user import User
from app.services.embedding_service import embedding_service
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.rag_indexing_service import (
    document_chunk_key,
    get_rag_redis,
    index_document_chunks,
)
from app.services.source_lifecycle import source_lifecycle_service

pytestmark = [pytest.mark.asyncio, pytest.mark.postgres]

if os.getenv("E05_LIVE") != "1":
    pytest.skip("E05 integration guards require E05_LIVE=1 (real PG + real embedding key)", allow_module_level=True)

if not (settings.DATABASE_URL or "").startswith("postgresql"):
    pytest.skip("E05 integration guards require postgres DATABASE_URL", allow_module_level=True)

USER_A_TEXTS = [
    "用户A的操作系统笔记：进程间通信 IPC 包括管道、消息队列、共享内存与信号量，共享内存最快但需要同步原语配合。",
    "用户A的线性代数笔记：矩阵的秩是列空间的维度，初等行变换不改变秩；满秩方阵可逆，行列式非零。",
]
USER_B_TEXTS = [
    # 刻意与 A 同题（进程间通信）：同题不同所有权才是 wrong-user 泄漏的真实攻击面
    # （例如两个同学各自上传同一门课的笔记）。跨领域内容天然距离远，测不出越权。
    "用户B的私有复习笔记：消息队列是内核维护的消息链表，按类型收发，进程间通信不需要共享地址空间；信号量用于同步互斥。",
    "用户B的吉他笔记：C 大调和弦进行 1-5-6-4，横按 F 和弦时食指需要稍微侧压以按紧一二弦。",
]
QUERY_A = "进程之间怎么通信，哪种方式最快？"
QUERY_B = "消息队列是怎么在进程间传数据的？"


@pytest_asyncio.fixture(name="live_engine")
async def live_engine_fixture():
    engine = create_async_engine(settings.DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(name="live_session")
async def live_session_fixture(live_engine):
    maker = async_sessionmaker(live_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture(name="two_users_with_docs")
async def two_users_with_docs_fixture(live_session: AsyncSession):
    """两用户 + 各 1 文件 + 各 2 chunk（1 次批量真实 embedding，共 4 条）。"""
    if not embedding_service.is_configured():
        pytest.skip("no embedding provider key configured")
    suffix = uuid.uuid4().hex[:8]

    users, files = [], []
    for label, _texts in (("a", USER_A_TEXTS), ("b", USER_B_TEXTS)):
        user = User(username=f"e05iso_{label}_{suffix}", email=f"e05iso_{label}_{suffix}@t.local", hashed_password="x")
        live_session.add(user)
        await live_session.flush()
        file_record = StoredFile(
            user_id=user.id,
            file_name=f"e05iso_{label}_{suffix}.txt",
            mime_type="text/plain",
            status="processed",
            file_size=0,
            bucket="e05-iso",
            object_key=f"e05-iso/{suffix}/{label}.txt",
        )
        live_session.add(file_record)
        await live_session.flush()
        users.append(user)
        files.append(file_record)

    vectors = await embedding_service.batch_embeddings(USER_A_TEXTS + USER_B_TEXTS, text_type="document")
    version = embedding_service.current_embedding_version()
    vec_iter = iter(vectors)
    for (user, file_record), texts in zip(zip(users, files, strict=True), (USER_A_TEXTS, USER_B_TEXTS), strict=True):
        for i, text in enumerate(texts):
            vector = next(vec_iter)
            live_session.add(
                DocumentChunk(
                    file_id=file_record.id,
                    user_id=user.id,
                    chunk_index=i,
                    section_title=f"{file_record.file_name}#{i}",
                    content=text,
                    embedding=vector,
                    quality_score=1.0,
                    pipeline_version="e05-iso",
                    embedding_model=version,
                    embedding_dim=len(vector),
                )
            )
    await live_session.commit()
    yield users, files
    # teardown：测试数据用完清理
    for file_record in files:
        await live_session.execute(delete(DocumentChunk).where(DocumentChunk.file_id == file_record.id))
        await live_session.execute(delete(StoredFile).where(StoredFile.id == file_record.id))
    for user in users:
        await live_session.execute(delete(User).where(User.id == user.id))
    await live_session.commit()


async def test_wrong_user_isolation_all_three_strategies(live_session, two_users_with_docs):
    users, files = two_users_with_docs
    user_a, user_b = users
    retrieval = KnowledgeRetrievalService(live_session)
    file_ids = [f.id for f in files]

    for user, query in ((user_a, QUERY_A), (user_b, QUERY_B)):
        # 显式绑定循环变量，避免闭包晚绑定（B023）
        for strategy in (
            lambda q, _u=user: retrieval.document_vector_search(
                user_id=_u.id, query=q, file_ids=file_ids, limit=5, threshold=0.6
            ),
            lambda q, _u=user: retrieval.document_lexical_search(user_id=_u.id, query=q, file_ids=file_ids, limit=5),
            lambda q, _u=user: retrieval.document_hybrid_search(
                user_id=_u.id, query=q, file_ids=file_ids, limit=5, threshold=0.6, use_reranker=False
            ),
        ):
            items = await strategy(query)
            assert items, f"user {user.username} should retrieve own chunks ({query})"
            wrong = [item for item in items if item.chunk.user_id != user.id]
            assert wrong == [], f"cross-user leak in retrieval: {[(w.chunk.id, w.chunk.user_id) for w in wrong]}"

    # 反向验证检索确实有区分度：A 的查询在 A 的结果里排第一且内容相关
    items_a = await retrieval.document_vector_search(
        user_id=user_a.id, query=QUERY_A, file_ids=file_ids, limit=5, threshold=0.6
    )
    assert "IPC" in items_a[0].chunk.content or "进程" in items_a[0].chunk.content


async def test_embedding_version_isolation(live_session, two_users_with_docs):
    """标记为其他模型的向量不参与检索（跨模型余弦无意义）。"""
    users, files = two_users_with_docs
    user_a = users[0]
    retrieval = KnowledgeRetrievalService(live_session)

    base = await retrieval.document_vector_search(
        user_id=user_a.id, query=QUERY_A, file_ids=[files[0].id], limit=5, threshold=0.6
    )
    assert len(base) >= 1

    # 把 A 的 chunk 0 标记成另一个模型
    chunk = (
        await live_session.execute(
            select(DocumentChunk).where(DocumentChunk.file_id == files[0].id, DocumentChunk.chunk_index == 0)
        )
    ).scalar_one()
    original_model = chunk.embedding_model
    chunk.embedding_model = "other/model@999"
    await live_session.commit()

    after = await retrieval.document_vector_search(
        user_id=user_a.id, query=QUERY_A, file_ids=[files[0].id], limit=5, threshold=0.6
    )
    assert chunk.id not in {item.chunk.id for item in after}, "foreign-version vector must be excluded"

    chunk.embedding_model = original_model
    await live_session.commit()


async def test_delete_isolation_pg_redis_semantic_cache(live_session, two_users_with_docs):
    users, files = two_users_with_docs
    user_a = users[0]
    file_a = files[0]
    retrieval = KnowledgeRetrievalService(live_session)

    # 写入 Redis 版本化索引
    redis = await get_rag_redis()
    assert redis is not None, "redis required for delete isolation test"
    chunks = (
        (
            await live_session.execute(
                select(DocumentChunk)
                .where(DocumentChunk.file_id == file_a.id, DocumentChunk.deleted_at.is_(None))
                .order_by(DocumentChunk.chunk_index)
            )
        )
        .scalars()
        .all()
    )
    indexed = await index_document_chunks(redis, file_a, chunks)
    assert indexed == len(chunks)
    versioned_keys = [document_chunk_key(file_a.id, c.chunk_index) for c in chunks]
    existing = await redis.exists(*versioned_keys)
    assert existing == len(versioned_keys)

    # 预热语义缓存：knowledge_version 走**真实缓存层**（_get_knowledge_version，
    # R2 D2 口径修正：R1 直调 _compute_knowledge_version() 绕过了 30s Redis
    # 版本缓存，测不出"删除未失效缓存键 → TTL 窗口内旧版本组键继续命中"）
    from app.core.cache import cache_service
    from app.services.galaxy.retrieval_service import KNOWLEDGE_VERSION_CACHE_KEY
    from app.services.semantic_cache_service import SemanticCacheService

    if not cache_service.redis:
        await cache_service.init_redis()
    assert cache_service.redis is not None, "semantic version cache layer required for delete-isolation test"

    cache = SemanticCacheService(redis_client=cache_service.redis, default_ttl=120)
    kv_before = await retrieval._get_knowledge_version()
    # 确认版本确实已被缓存层缓存（后续断言才有意义：删除必须把它打掉）
    assert await cache_service.get(KNOWLEDGE_VERSION_CACHE_KEY) == kv_before
    await cache.set(
        QUERY_A,
        {"nodes": [{"id": "e05-delete-canary"}]},
        user_id=str(user_a.id),
        knowledge_version=kv_before,
        embedding_version=embedding_service.current_embedding_version(),
    )
    warm = await cache.get(
        QUERY_A,
        user_id=str(user_a.id),
        knowledge_version=kv_before,
        embedding_version=embedding_service.current_embedding_version(),
    )
    assert warm is not None

    # 另一用户先写一条更新的 chunk，确保被删的 A 文件**不是**最新行
    # （回归旧行为：旧 knowledge_version = max(updated_at) 时删非最新行不变版本）
    other_user = User(
        username=f"e05iso_newer_{uuid.uuid4().hex[:6]}",
        email=f"e05iso_n_{uuid.uuid4().hex[:6]}@t.local",
        hashed_password="x",
    )
    live_session.add(other_user)
    await live_session.flush()
    newer_file = StoredFile(
        user_id=other_user.id,
        file_name="e05iso_newer.txt",
        mime_type="text/plain",
        status="processed",
        file_size=0,
        bucket="e05-iso",
        object_key=f"e05-iso/{uuid.uuid4().hex}/newer.txt",
    )
    live_session.add(newer_file)
    await live_session.flush()
    from datetime import UTC, datetime, timedelta

    vec = chunks[0].embedding
    newer_chunk = DocumentChunk(
        file_id=newer_file.id,
        user_id=other_user.id,
        chunk_index=0,
        content="占位：让 updated_at 晚于被删文件",
        embedding=vec,
        pipeline_version="e05-iso",
        embedding_model=chunks[0].embedding_model,
        embedding_dim=chunks[0].embedding_dim,
        updated_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1),
    )
    live_session.add(newer_chunk)
    await live_session.commit()

    # 执行删除（真实生命周期路径：Redis key + chunk 软删 + lifecycle）
    await source_lifecycle_service.delete(live_session, source=file_a, reason="e05_delete_isolation_test")

    # a) pgvector 立即不可见
    after_delete = await retrieval.document_vector_search(
        user_id=user_a.id, query=QUERY_A, file_ids=[files[1].id, file_a.id], limit=5, threshold=0.6
    )
    assert file_a.id not in {item.chunk.file_id for item in after_delete}, "deleted file must be invisible immediately"

    # b) Redis 版本化 key（含所有版本）即时清除
    remaining = await redis.exists(*versioned_keys)
    assert remaining == 0, "versioned redis keys must be deleted immediately"

    # c) 语义缓存：D2 口径——删除必须**先失效 knowledge:version:v1 缓存键**，
    #    随后的 _get_knowledge_version() 走缓存层取到新版本（若未失效则会命中
    #    30s TTL 内的旧值 → 旧语义缓存条目在窗口期内继续可命中）
    assert await cache_service.get(KNOWLEDGE_VERSION_CACHE_KEY) is None, (
        "invalidate_source_retrieval must DEL the knowledge version cache key (E-05 D2)"
    )
    kv_after = await retrieval._get_knowledge_version()
    assert kv_after != kv_before, "knowledge_version must change on chunk deletion"
    stale = await cache.get(
        QUERY_A,
        user_id=str(user_a.id),
        knowledge_version=kv_after,
        embedding_version=embedding_service.current_embedding_version(),
    )
    assert stale is None, "semantic cache entry must not survive its knowledge_version"

    # 清理新增的 newer 行
    await live_session.execute(delete(DocumentChunk).where(DocumentChunk.id == newer_chunk.id))
    await live_session.execute(delete(StoredFile).where(StoredFile.id == newer_file.id))
    await live_session.execute(delete(User).where(User.id == other_user.id))
    await live_session.commit()
    keys = [k async for k in redis.scan_iter(match="semantic_cache:*")]
    if keys:
        await redis.delete(*keys)
    members = await redis.smembers(cache.KEY_SET)
    if members:
        await redis.srem(cache.KEY_SET, *members)
