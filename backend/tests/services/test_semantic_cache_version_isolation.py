"""E-05: 语义缓存 delete/version isolation 单元测试（真实 Redis，无 API 调用）。

覆盖：
1. embedding 版本进入缓存键与相似命中判定——重嵌/换模型后旧缓存自动不可见；
2. knowledge_version 变化（对应知识数据写入/删除）后旧缓存条目不可命中
   （delete isolation：删除文档必须让缓存即时失效，即使删的不是最新行）；
3. D2（R2）：删除路径走**真实缓存层**失效 knowledge:version:v1——
   该键 30s TTL 期间旧版本组键会让已删内容继续命中，必须被
   SourceLifecycleService.invalidate_source_retrieval 主动清除；
4. D3（R2）：降级检索结果（embedding 故障后的词法降级）不得写入语义缓存。
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import pytest
import redis.asyncio as redis_asyncio

from app.config import settings
from app.core.redis_utils import resolve_redis_password
from app.services.semantic_cache_service import SemanticCacheService

pytestmark = pytest.mark.asyncio


async def _make_cache() -> tuple[SemanticCacheService, redis_asyncio.Redis]:
    url = settings.REDIS_URL or "redis://localhost:6379/0"
    password, _ = resolve_redis_password(url, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    client = redis_asyncio.from_url(url, password=password, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        pytest.skip(f"redis not reachable at {url}")
    return SemanticCacheService(redis_client=client, default_ttl=60), client


async def _cleanup(client, keys: list[str]):
    if keys:
        await client.delete(*keys)


async def test_embedding_version_changes_cache_key_and_hits():
    cache, client = await _make_cache()
    tag = uuid.uuid4().hex[:8]
    try:
        query = f"e05 测试查询 {tag}"
        # 用 V1 写入
        assert await cache.set(
            query, {"nodes": [{"id": "n1"}]}, user_id="u1", knowledge_version="kv1", embedding_version="V1"
        )
        # 同版本 exact 命中
        hit = await cache.get(query, user_id="u1", knowledge_version="kv1", embedding_version="V1")
        assert hit is not None and hit["nodes"][0]["id"] == "n1"
        # 换 embedding 版本 → exact 键不同 → miss（跨模型缓存条目不可见）
        miss = await cache.get(query, user_id="u1", knowledge_version="kv1", embedding_version="V2")
        assert miss is None
        # 未声明版本（调用方未接入）→ 也不命中旧条目，避免跨版本泄漏
        miss_legacy = await cache.get(query, user_id="u1", knowledge_version="kv1")
        assert miss_legacy is None
    finally:
        keys = [k async for k in client.scan_iter(match=f"{cache.CACHE_PREFIX}*")]
        await _cleanup(client, keys)
        await _cleanup(client, [cache.KEY_SET])
        await client.aclose()


async def test_semantic_similar_hit_respects_embedding_version():
    """相似命中路径：旧模型查询向量 vs 新模型查询向量的余弦相似度无意义，必须隔离。"""
    cache, client = await _make_cache()
    tag = uuid.uuid4().hex[:8]
    try:
        query_a = f"e05 相似查询甲 {tag}"
        dim = settings.EMBEDDING_DIM
        # 构造高相似（同向）的假向量
        vec_a = [1.0] + [0.0] * (dim - 1)
        vec_b = [0.999] + [0.001] * (dim - 1)

        # 以 V1 写入 query_a 的缓存与语义载荷
        key_a = cache._generate_cache_key(query_a, "u1", "kv1", "V1")
        await cache.set(
            query_a, {"nodes": [{"id": "shared"}]}, user_id="u1", knowledge_version="kv1", embedding_version="V1"
        )
        await cache._set_embedding_payload(
            cache_key=key_a,
            embedding=vec_a,
            user_id="u1",
            normalized_query=cache._normalize_query(query_a),
            knowledge_version="kv1",
            ttl=60,
            embedding_version="V1",
        )

        # 同 V1 + 相似向量 → 应能语义命中
        hit_same = await cache._find_similar_cache_key(vec_b, "u1", 0.9, "kv1", "V1")
        assert hit_same is not None, "same-version similar lookup should hit"

        # V2 查询 → 版本不匹配 → 即使向量高相似也不可命中
        hit_cross = await cache._find_similar_cache_key(vec_b, "u1", 0.9, "kv1", "V2")
        assert hit_cross is None, "cross-embedding-version semantic hit must be blocked"

        # knowledge_version 变化（数据删除/写入）→ 同样不可命中
        hit_stale = await cache._find_similar_cache_key(vec_b, "u1", 0.9, "kv1-after-delete", "V1")
        assert hit_stale is None, "stale knowledge_version semantic hit must be blocked"
    finally:
        keys = [k async for k in client.scan_iter(match=f"{cache.CACHE_PREFIX}*")]
        embs = [k async for k in client.scan_iter(match=f"{cache.EMBED_PREFIX}*")]
        await _cleanup(client, keys + embs)
        await _cleanup(client, [cache.KEY_SET])
        await client.aclose()


async def test_cross_user_semantic_hit_blocked():
    """回归守卫：跨用户语义命中必须被拒（wrong-user=0 在缓存层同样成立）。"""
    cache, client = await _make_cache()
    tag = uuid.uuid4().hex[:8]
    try:
        query = f"e05 隔离查询 {tag}"
        dim = settings.EMBEDDING_DIM
        vec = [1.0] + [0.0] * (dim - 1)
        key = cache._generate_cache_key(query, "userA", "kv1", "V1")
        await cache.set(
            query, {"nodes": [{"id": "a-secret"}]}, user_id="userA", knowledge_version="kv1", embedding_version="V1"
        )
        await cache._set_embedding_payload(
            cache_key=key,
            embedding=vec,
            user_id="userA",
            normalized_query=cache._normalize_query(query),
            knowledge_version="kv1",
            ttl=60,
            embedding_version="V1",
        )
        # userB 用完全相同的向量查询 → 不得命中 userA 的条目
        hit = await cache._find_similar_cache_key(vec, "userB", 0.9, "kv1", "V1")
        assert hit is None
        exact = await cache.get(query, user_id="userB", knowledge_version="kv1", embedding_version="V1")
        assert exact is None
    finally:
        keys = [k async for k in client.scan_iter(match=f"{cache.CACHE_PREFIX}*")]
        embs = [k async for k in client.scan_iter(match=f"{cache.EMBED_PREFIX}*")]
        await _cleanup(client, keys + embs)
        await _cleanup(client, [cache.KEY_SET])
        await client.aclose()


async def test_source_invalidation_clears_knowledge_version_cache(monkeypatch):
    """D2（R2）：删除/归档路径必须 DEL knowledge:version:v1（走真实缓存层）。

    R1 的 delete-isolation 测试直调 _compute_knowledge_version() 绕过了这层
    30s Redis 缓存——生产语义里检索读的是 _get_knowledge_version()，缓存键
    不失效则已删内容在 TTL 窗口内继续命中语义缓存（REVIEW_RECEIPT_2 D2）。
    本测试预热真实键 → 执行真实失效函数（外部依赖最小桩化）→ 断言键被清除。
    """
    from app.services import source_lifecycle as sl_mod
    from app.services.galaxy.retrieval_service import KNOWLEDGE_VERSION_CACHE_KEY
    from app.services.source_lifecycle import source_lifecycle_service

    url = settings.REDIS_URL or "redis://localhost:6379/0"
    password, _ = resolve_redis_password(url, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    client = redis_asyncio.from_url(url, password=password, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        pytest.skip(f"redis not reachable at {url}")

    # 保存原值，测试后恢复（该键是 dev 共享的派生缓存：DEL 语义安全，但仍礼貌恢复）
    old_value = await client.get(KNOWLEDGE_VERSION_CACHE_KEY)
    try:
        # 预热版本缓存（模拟删除前 30s 内发生过一次检索）
        assert await client.set(KNOWLEDGE_VERSION_CACHE_KEY, "tsms:1:n1:c1", ex=30)

        # 让失效函数的依赖全部落在同一个真实 Redis 上（cache_service 全局单例
        # 在测试进程中可能未初始化；生产中它与检索读路径共用同一客户端）
        monkeypatch.setattr(sl_mod.cache_service, "redis", client)

        async def _fake_get_rag_redis():
            return client

        monkeypatch.setattr(sl_mod, "get_rag_redis", _fake_get_rag_redis)

        async def _no_group_links(self, db, source_id):
            return []

        monkeypatch.setattr(sl_mod.SourceLifecycleService, "_active_group_links", _no_group_links)

        source = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
        await source_lifecycle_service.invalidate_source_retrieval(None, source)

        # 核心断言：版本缓存键必须被真实清除（30s 陈旧窗口归零）
        assert await client.get(KNOWLEDGE_VERSION_CACHE_KEY) is None, (
            "invalidate_source_retrieval must DEL the knowledge version cache key; "
            "otherwise deleted content stays retrievable via stale-versioned semantic cache for up to 30s (E-05 D2)"
        )
    finally:
        if old_value is not None:
            await client.set(KNOWLEDGE_VERSION_CACHE_KEY, old_value, ex=settings.KNOWLEDGE_VERSION_CACHE_TTL_SECONDS)
        else:
            await client.delete(KNOWLEDGE_VERSION_CACHE_KEY)
        await client.aclose()


async def test_degraded_factory_result_is_not_cached(monkeypatch):
    """D3（R2）：factory 标记 degraded 的结果不得写入语义缓存。

    瞬时 embedding 故障触发词法降级时，降级答案按旧实现会被固化 1h
    （TTL 3600，无降级标记），供应商恢复后同查询继续命中降级答案。
    """
    import app.services.semantic_cache_service as sc_mod

    class _UnconfiguredEmbedding:
        """打桩 embedding 服务：避免 set() 触发真实 API 调用。"""

        @staticmethod
        def is_configured():
            return False

    monkeypatch.setattr(sc_mod, "embedding_service", _UnconfiguredEmbedding)

    cache, client = await _make_cache()
    tag = uuid.uuid4().hex[:8]
    try:
        query = f"e05 降级查询 {tag}"
        calls = []
        degraded_meta: dict = {}

        async def degraded_factory(*args, exec_meta=None, **kwargs):
            calls.append("degraded")
            if exec_meta is not None:
                exec_meta["degraded"] = True  # 模拟 _execute_hybrid_search 的降级标记
            return {"nodes": [{"id": "lexical-only"}]}

        out = await cache.get_with_lock(
            query=query,
            factory_func=degraded_factory,
            user_id="u1",
            similarity_threshold=1.0,  # 只走 exact 命中路径，不打桩向量比较
            knowledge_version="kv1",
            embedding_version="V1",
            factory_meta=degraded_meta,
        )
        assert out == {"nodes": [{"id": "lexical-only"}]}  # 降级结果照常返回（可用性）
        assert degraded_meta.get("degraded") is True  # 通道确实被注入并被 factory 标记
        key = cache._generate_cache_key(query, "u1", "kv1", "V1")
        assert await client.get(key) is None, "degraded result must not be cached (E-05 D3)"

        # 对照：供应商恢复后同一查询重新生成 → 正常结果照常缓存
        async def healthy_factory(*args, exec_meta=None, **kwargs):
            calls.append("healthy")
            return {"nodes": [{"id": "full-quality"}]}

        out2 = await cache.get_with_lock(
            query=query,
            factory_func=healthy_factory,
            user_id="u1",
            similarity_threshold=1.0,
            knowledge_version="kv1",
            embedding_version="V1",
        )
        assert out2 == {"nodes": [{"id": "full-quality"}]}
        assert calls == ["degraded", "healthy"]
        cached_raw = await client.get(key)
        assert cached_raw is not None and "full-quality" in cached_raw
    finally:
        keys = [k async for k in client.scan_iter(match=f"{cache.CACHE_PREFIX}*")]
        embs = [k async for k in client.scan_iter(match=f"{cache.EMBED_PREFIX}*")]
        await _cleanup(client, keys + embs)
        await _cleanup(client, [cache.KEY_SET])
        await client.aclose()
