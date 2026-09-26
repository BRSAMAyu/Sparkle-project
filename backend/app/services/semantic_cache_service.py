"""
Redis Semantic Cache Service - 语义缓存服务

用于缓存 GraphRAG 查询结果，基于语义相似度检索缓存
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, TypeVar, cast

import numpy as np
from loguru import logger
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.core.metrics import (
    SEMANTIC_CACHE_BYPASS_TOTAL,
    SEMANTIC_CACHE_HIT_TOTAL,
    SEMANTIC_CACHE_MISS_TOTAL,
    SEMANTIC_CACHE_WRITE_FAILURE_TOTAL,
)
from app.services.embedding_service import embedding_service


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# V3-FIX-225: get_with_lock 的工厂泛型——返回类型随 factory_func 的 await 结果走
_T = TypeVar("_T")


# ------------------------------------------------------------------ #
# V3-FIX-240：写侧序列化保形——Pydantic 模型归一为 JSON 安全形态并记录
# 重水化骨架；命中侧按骨架重建原模型（真保形，杜绝「未命中 list[Model] /
# 命中 list[dict]」两形态真分裂）。骨架只标记「裸容器里的模型位」，纯 JSON
# 原生载荷不产出骨架，存储形态与旧格式完全一致（向后兼容）。
# ------------------------------------------------------------------ #


def _model_type_path(model: BaseModel) -> str:
    cls = type(model)
    return f"{cls.__module__}:{cls.__qualname__}"


def _load_model_class(type_path: str) -> type[BaseModel] | None:
    """从骨架类型路径还原模型类。

    安全边界（缓存内容驱动 import，必须收敛）：仅接受 ``app.*`` 命名空间
    下的模块，且解析结果必须是 pydantic BaseModel 子类；其余一律拒绝
    （返回 None，调用侧降级为 JSON 形态并留日志）。
    """
    module_name, _, qualname = type_path.partition(":")
    if not module_name.startswith("app.") or not qualname:
        return None
    try:
        obj: Any = importlib.import_module(module_name)
        for part in qualname.split("."):
            obj = getattr(obj, part)
    except (ImportError, AttributeError, ValueError):
        return None
    if isinstance(obj, type) and issubclass(obj, BaseModel):
        return cast("type[BaseModel]", obj)
    return None


def _normalize_for_cache(value: Any) -> tuple[Any, Any]:
    """递归归一：Pydantic 模型 → ``model_dump(mode="json")``，同时产出骨架。

    返回 ``(json 安全值, 骨架)``；子树无模型时原样返回并记骨架 None
    （不重建容器，保证纯 JSON 载荷存储形态与旧格式一致）。tuple 视作
    list（JSON 稳定形态边界，V3-FIX-225 契约不变）。
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json"), {"m": _model_type_path(value)}
    if isinstance(value, (list, tuple)):
        items: list[Any] = []
        skeletons: list[Any] = []
        saw_model = False
        for item in value:
            safe, skeleton = _normalize_for_cache(item)
            items.append(safe)
            skeletons.append(skeleton)
            saw_model = saw_model or skeleton is not None
        if not saw_model:
            return value, None
        return items, {"l": skeletons}
    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        inner: dict[Any, Any] = {}
        saw_model = False
        for key, item in value.items():
            safe, skeleton = _normalize_for_cache(item)
            normalized[key] = safe
            inner[key] = skeleton
            saw_model = saw_model or skeleton is not None
        if not saw_model:
            return value, None
        return normalized, {"d": inner}
    return value, None


def _rehydrate_from_skeleton(value: Any, skeleton: Any) -> Any:
    """按骨架把 JSON 形态重建为原形态（模型位经 pydantic 校验重建）。

    骨架与数据形态不匹配（缓存被外写/版本漂移）时抛 ValueError，由命中侧
    统一降级为 JSON 形态并留 warning 日志——降级可观测，不静默。
    """
    if skeleton is None or value is None:
        return value
    if not isinstance(skeleton, dict):
        return value
    if "m" in skeleton:
        cls = _load_model_class(str(skeleton["m"]))
        if cls is None:
            raise ValueError(f"semantic cache skeleton references unrehydrable model: {skeleton['m']!r}")
        return cls.model_validate(value)
    if "l" in skeleton:
        if not isinstance(value, list):
            raise ValueError("semantic cache skeleton/list shape mismatch")
        return [_rehydrate_from_skeleton(item, skel) for item, skel in zip(value, skeleton["l"], strict=True)]
    if "d" in skeleton:
        if not isinstance(value, dict):
            raise ValueError("semantic cache skeleton/dict shape mismatch")
        inner = skeleton["d"]
        return {key: _rehydrate_from_skeleton(item, inner.get(key)) for key, item in value.items()}
    return value


def _write_failure_reason(exc: BaseException) -> str:
    """写失败归因：序列化（json/pydantic）与传输（redis/网络）分开计数。"""
    if isinstance(exc, (TypeError, ValueError)):
        return "serialization"
    if isinstance(exc, (OSError, RedisError)):
        return "redis"
    return "unknown"


class SemanticCacheService:
    """
    语义缓存服务

    功能：
    - 基于查询文本的语义哈希缓存
    - TTL 管理（根据内容类型设置不同过期时间）
    - 缓存命中率统计
    - LRU 驱逐策略
    - 互斥锁防止缓存击穿 (Cache Stampede Protection)
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        default_ttl: int = 3600,  # 1小时
        max_cache_size: int = 10000,
        lock_timeout: float = 5.0,  # 锁超时时间
    ):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.lock_timeout = lock_timeout

        # 缓存键前缀
        self.CACHE_PREFIX = "semantic_cache:"
        self.STATS_KEY = "semantic_cache:stats"
        self.LOCK_PREFIX = "semantic_cache:lock:"
        self.EMBED_PREFIX = "semantic_cache:emb:"
        self.KEY_SET = "semantic_cache:keys"
        self.max_candidates = settings.SEMANTIC_CACHE_MAX_CANDIDATES

        # 初始化统计
        # 注意：这里不能在 __init__ 中 await，所以统计初始化改为按需触发或单独的 async init 方法
        # 为了兼容性，我们在第一次写入时检查，或者接受外部传入的 redis_client 已经准备好
        # 暂时移除 __init__ 中的异步调用，防止 event loop 问题

    async def _init_stats(self):
        """初始化缓存统计"""
        if not self.redis:
            return

        exists = await self.redis.exists(self.STATS_KEY)
        if not exists:
            stats = {
                "total_hits": 0,
                "total_misses": 0,
                "total_sets": 0,
                "semantic_hits": 0,
                "start_time": _utcnow().isoformat(),
            }
            await self.redis.hset(self.STATS_KEY, mapping={k: json.dumps(v) for k, v in stats.items()})

    def _normalize_query(self, query: str) -> str:
        """Normalize query for stable cache keys."""
        normalized = " ".join(query.strip().lower().split())
        return normalized

    def _generate_cache_key(
        self,
        query: str,
        user_id: str | None = None,
        knowledge_version: str | None = None,
        embedding_version: str | None = None,
    ) -> str:
        """
        生成缓存键

        使用查询文本的 SHA256 哈希 + 用户ID（可选）+ 知识版本 + embedding 版本
        """
        # 标准化查询文本
        normalized_query = self._normalize_query(query)

        # 生成哈希
        parts = [normalized_query]
        if user_id:
            parts.append(user_id)
        if knowledge_version:
            parts.append(f"kv={knowledge_version}")
        # E-05: embedding 版本参与缓存键——重嵌/换模型后旧缓存（含旧模型
        # 查询向量）自动失效，防止跨模型语义命中污染
        if embedding_version:
            parts.append(f"ev={embedding_version}")

        cache_input = ":".join(parts)

        hash_key = hashlib.sha256(cache_input.encode()).hexdigest()

        return f"{self.CACHE_PREFIX}{hash_key}"

    def _embedding_key(self, cache_key: str) -> str:
        return f"{self.EMBED_PREFIX}{cache_key}"

    def _generate_lock_key(self, cache_key: str) -> str:
        """生成锁键"""
        return f"{self.LOCK_PREFIX}{cache_key}"

    async def _get_embedding_payload(self, cache_key: str) -> dict[str, Any] | None:
        if not self.redis:
            return None
        if not settings.SEMANTIC_CACHE_ENABLED:
            return None
        emb_key = self._embedding_key(cache_key)
        payload_raw = await self.redis.get(emb_key)
        if not payload_raw:
            return None
        try:
            return cast("dict[str, Any] | None", (json.loads(payload_raw)))
        except json.JSONDecodeError:
            return None

    async def _set_embedding_payload(
        self,
        cache_key: str,
        embedding: list[float],
        user_id: str | None,
        normalized_query: str,
        knowledge_version: str | None,
        ttl: int,
        embedding_version: str | None = None,
    ) -> None:
        if not self.redis:
            return
        emb_key = self._embedding_key(cache_key)
        payload = {
            "embedding": embedding,
            "user_id": user_id,
            "normalized_query": normalized_query,
            "knowledge_version": knowledge_version,
            "embedding_version": embedding_version,
            "updated_at": _utcnow().isoformat(),
        }
        await self.redis.setex(emb_key, ttl, json.dumps(payload))
        await ensure_awaitable(self.redis.sadd(self.KEY_SET, cache_key))

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        vec_a = np.array(a, dtype=np.float32)
        vec_b = np.array(b, dtype=np.float32)
        denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        if denom == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)

    async def _find_similar_cache_key(
        self,
        query_embedding: list[float],
        user_id: str | None,
        threshold: float,
        knowledge_version: str | None,
        embedding_version: str | None = None,
    ) -> tuple[str, float] | None:
        if not self.redis:
            return None

        total_keys = await ensure_awaitable(self.redis.scard(self.KEY_SET))
        if total_keys == 0:
            return None

        candidate_keys: list[Any] | set[Any] | str | None
        if total_keys > self.max_candidates:
            candidate_keys = await ensure_awaitable(self.redis.srandmember(self.KEY_SET, number=self.max_candidates))
        else:
            candidate_keys = await ensure_awaitable(self.redis.smembers(self.KEY_SET))

        if not candidate_keys:
            return None

        best_key = None
        best_score = 0.0

        for cache_key in candidate_keys:
            payload = await self._get_embedding_payload(cache_key)
            if not payload:
                continue
            # 严格可见性：仅同用户（或双方均为匿名全局条目）可命中，
            # caller 未带 user_id 时不得读取任何已归属用户的条目（防跨用户泄漏）。
            if payload.get("user_id") != user_id:
                continue
            if knowledge_version and payload.get("knowledge_version") != knowledge_version:
                continue
            # E-05: embedding 版本隔离——旧模型查询向量与新模型查询向量的
            # 余弦相似度无意义，绝不允许跨版本语义命中
            if embedding_version and payload.get("embedding_version") != embedding_version:
                continue

            embedding = payload.get("embedding")
            if not embedding:
                continue
            score = self._cosine_similarity(query_embedding, embedding)
            if score >= threshold and score > best_score:
                best_score = score
                best_key = cache_key

        if best_key:
            return best_key, best_score
        return None

    async def get(
        self,
        query: str,
        user_id: str | None = None,
        similarity_threshold: float = 0.95,
        knowledge_version: str | None = None,
        embedding_version: str | None = None,
    ) -> Any | None:
        """
        从缓存获取查询结果
        包含缓存击穿保护 (Mutex Lock)

        Args:
            query: 查询文本
            user_id: 用户ID（可选，用于个性化缓存）
            similarity_threshold: 相似度阈值（暂未实现向量相似度，使用精确匹配）

        Returns:
            缓存的结果（V3-FIX-240：写入侧含 Pydantic 模型的载荷按骨架重水化
            回原模型形态，真保形；其余为 JSON 反序列化形态），如果未命中则
            返回 None。不再谎称仅 dict。
        """
        if not self.redis:
            return None

        try:
            await self._init_stats()
            cache_key = self._generate_cache_key(query, user_id, knowledge_version, embedding_version)
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                # 命中
                await ensure_awaitable(self.redis.hincrby(self.STATS_KEY, "total_hits", 1))
                SEMANTIC_CACHE_HIT_TOTAL.inc()
                result = json.loads(cached_data)

                logger.debug(f"Cache HIT: query='{query[:30]}...', " f"cached_at={result.get('cached_at')}")

                return self._payload_data(result)
            # 语义相似检索
            # E-05: embedding 供应商未配置时跳过（避免每次未命中都触发
            # 3 次重试 x 2 供应商的失败风暴）；exact-match 缓存仍可用
            if similarity_threshold < 1.0 and embedding_service.is_configured():
                normalized_query = self._normalize_query(query)
                query_embedding = await embedding_service.get_embedding(normalized_query, text_type="query")
                similar = await self._find_similar_cache_key(
                    query_embedding,
                    user_id,
                    similarity_threshold,
                    knowledge_version,
                    embedding_version or embedding_service.current_embedding_version(),
                )
                if similar:
                    similar_key, score = similar
                    cached_similar = await self.redis.get(similar_key)
                    if cached_similar:
                        await ensure_awaitable(self.redis.hincrby(self.STATS_KEY, "total_hits", 1))
                        await ensure_awaitable(self.redis.hincrby(self.STATS_KEY, "semantic_hits", 1))
                        SEMANTIC_CACHE_HIT_TOTAL.inc()
                        result = json.loads(cached_similar)
                        logger.debug(f"Cache SEMANTIC HIT: query='{query[:30]}...', score={score:.3f}")
                        return self._payload_data(result)

            # 未命中
            await ensure_awaitable(self.redis.hincrby(self.STATS_KEY, "total_misses", 1))
            SEMANTIC_CACHE_MISS_TOTAL.inc()
            logger.debug(f"Cache MISS: query='{query[:30]}...'")
            return None

        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    @staticmethod
    def _payload_data(result: dict[str, Any]) -> Any:
        """取缓存载荷 data 并按骨架重水化（V3-FIX-240）。

        骨架缺失（旧条目/纯 JSON 载荷）原样返回；重水化失败（模型类漂移、
        缓存被外写导致骨架/数据形态错位）降级为 JSON 形态并留 warning——
        降级可观测，不静默，绝不让命中路径因重水化失败而炸穿。
        """
        data = result.get("data")
        skeleton = result.get("data_skeleton")
        if skeleton is None:
            return data
        try:
            return _rehydrate_from_skeleton(data, skeleton)
        except Exception as exc:
            logger.warning(f"Cache HIT rehydration degraded to JSON form: {exc}")
            return data

    async def get_with_lock(
        self,
        query: str,
        factory_func: Callable[..., Awaitable[_T]],
        user_id: str | None = None,
        ttl: int | None = None,
        similarity_threshold: float | None = None,
        knowledge_version: str | None = None,
        embedding_version: str | None = None,
        factory_meta: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """
        获取缓存，如果未命中则使用 factory_func 生成并缓存
        使用互斥锁防止缓存击穿 (Cache Stampede)

        Args:
            query: 查询字符串
            factory_func: 如果缓存未命中，用于生成数据的异步函数。
                类型契约（V3-FIX-225）：返回类型 _T 随 factory_func 泛型——
                工厂可返回 list 等任意异型（如 galaxy/retrieval_service 把
                返回 ``list[SearchResultItem]`` 的实现传入），不再被静态
                谎称 ``dict | None``。仅当工厂自身产出 None 时本方法才为
                None（命中路径有 ``is not None`` 守卫，其余路径一律透传
                工厂结果）。
            user_id: 用户 ID
            ttl: 过期时间
            factory_meta: E-05 D3 降级标记通道。传入的 dict 会以 ``exec_meta``
                关键字转发给 factory_func；factory 在产出**降级结果**（如
                embedding 故障后的纯词法检索）时置 ``exec_meta["degraded"]=True``，
                该结果照常返回但**不写入缓存**——瞬时故障的降级答案不得被固化
                到缓存（否则供应商恢复后同查询最长继续命中降级答案 1h）。
            *args, **kwargs: 传递给 factory_func 的参数

        Returns:
            数据：未命中/异常降级路径返回工厂原返回值（原对象透传）；命中路径
            返回缓存载荷的反序列化形态——V3-FIX-240 起写侧对 Pydantic 模型
            归一并记录骨架、命中侧按骨架重建模型（真保形：``list[SearchResultItem]``
            等形态往返同型同值，证据见
            ``tests/services/test_semantic_cache_pydantic_payload.py``）；JSON
            稳定形态（dict/list/标量）保持 json 往返同型同值（证据见
            ``tests/services/test_semantic_cache_generic_factory.py``）。
            tuple 往返变型维持 JSON 稳定形态边界；真异型载荷写入失败按
            reason 落 ``SEMANTIC_CACHE_WRITE_FAILURE_TOTAL``（不再静默）。
        """
        if not self.redis:
            SEMANTIC_CACHE_BYPASS_TOTAL.inc()
            return await self._call_factory(factory_func, factory_meta, *args, **kwargs)
        if not settings.SEMANTIC_CACHE_ENABLED:
            SEMANTIC_CACHE_BYPASS_TOTAL.inc()
            return await self._call_factory(factory_func, factory_meta, *args, **kwargs)

        # 1. 尝试获取缓存
        effective_threshold = similarity_threshold if similarity_threshold is not None else 1.0
        data = await self.get(query, user_id, effective_threshold, knowledge_version, embedding_version)
        if data is not None:
            # 命中载荷是工厂结果的 JSON 往返形态（保形契约见 docstring 与保形证据测试）
            return cast("_T", data)

        cache_key = self._generate_cache_key(query, user_id, knowledge_version, embedding_version)
        lock_key = self._generate_lock_key(cache_key)

        # 2. 获取分布式锁 (Async)
        try:
            lock = self.redis.lock(lock_key, timeout=self.lock_timeout, blocking_timeout=2.0)

            # 使用 async context manager 自动处理 acquire/release
            # acquire 内部默认是阻塞的 (blocking=True)，但它是 async 的，
            # 所以会释放 event loop，不会阻塞其他协程。
            async with lock:
                # 双重检查 (Double-Checked Locking)
                data = await self.get(query, user_id, effective_threshold, knowledge_version, embedding_version)
                if data is not None:
                    return cast("_T", data)

                # 3. 生成数据
                logger.info(f"Cache MISS & Lock Acquired. Generating data for query='{query[:30]}...'")
                result = await self._call_factory(factory_func, factory_meta, *args, **kwargs)

                # 4. 写入缓存（E-05 D3：降级结果拒绝固化——瞬时故障的降级答案
                #    不得进入缓存，供应商恢复后同查询必须重新生成全质量结果）
                if result and not (factory_meta or {}).get("degraded"):
                    await self.set(query, result, user_id, ttl, knowledge_version, embedding_version)
                elif factory_meta and factory_meta.get("degraded"):
                    SEMANTIC_CACHE_BYPASS_TOTAL.inc()
                    logger.info(
                        f"Cache SET skipped for degraded result query='{query[:30]}...' "
                        "(transient degradation must not be cached; E-05 D3)"
                    )

                return result

        except Exception as e:
            # redis.exceptions.LockError 可能会在锁获取超时抛出
            if type(e).__name__ == "LockError":
                logger.warning(f"Failed to acquire lock for {cache_key} (Timeout). Waiting...")
                # 稍微等待一下再尝试获取（降级策略）
                await asyncio.sleep(0.1)
                # V3-FIX-255：降级路径与主路径同源阈值——effective_threshold
                # 缺省 0.95 比主路径（调用方传入/未传收敛 1.0）更严，两路口径须一致
                # 保持旧 ``or`` 语义：truthy 命中直接用，falsy/None 命中仍走工厂
                fallback_hit = cast(
                    "_T | None",
                    (
                        await self.get(
                            query,
                            user_id,
                            effective_threshold,
                            knowledge_version=knowledge_version,
                            embedding_version=embedding_version,
                        )
                    ),
                )
                if fallback_hit:
                    return fallback_hit
                return await self._call_factory(factory_func, factory_meta, *args, **kwargs)

            logger.error(f"Cache Mutex Error: {e}")
            # 出错时降级为直接调用
            return await self._call_factory(factory_func, factory_meta, *args, **kwargs)

    @staticmethod
    async def _call_factory(
        factory_func: Callable[..., Awaitable[_T]],
        factory_meta: dict[str, Any] | None,
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """调用 factory；提供 factory_meta 时以 ``exec_meta`` 关键字注入（D3 通道）。"""
        if factory_meta is None:
            return await factory_func(*args, **kwargs)
        return await factory_func(*args, exec_meta=factory_meta, **kwargs)

    async def set(
        self,
        query: str,
        data: Any,
        user_id: str | None = None,
        ttl: int | None = None,
        knowledge_version: str | None = None,
        embedding_version: str | None = None,
    ) -> bool:
        """
        设置缓存

        Args:
            query: 查询文本
            data: 要缓存的数据。V3-FIX-240：Pydantic 模型（含嵌在 list/dict
                里的模型位）在写侧归一为 JSON 安全形态并记录重水化骨架，命中
                侧经骨架重建原模型（真保形，杜绝「未命中 list[SearchResultItem]
                / 命中 list[dict]」两形态真分裂——此前该形态 json.dumps
                TypeError 被静默吞掉，galaxy hybrid_search 载荷零命中）。真异型
                （不可序列化且非模型）仍会失败，但失败按 reason 落
                ``SEMANTIC_CACHE_WRITE_FAILURE_TOTAL``，不再静默。
            user_id: 用户ID（可选）
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            是否成功
        """
        if not self.redis:
            return False

        try:
            await self._init_stats()
            normalized_query = self._normalize_query(query)
            cache_key = self._generate_cache_key(query, user_id, knowledge_version, embedding_version)

            # V3-FIX-240：写侧归一（模型→dict + 骨架），纯 JSON 载荷原样
            json_safe_data, data_skeleton = _normalize_for_cache(data)

            # 包装数据，添加元信息
            cache_value = {
                "data": json_safe_data,
                "query": query,
                "normalized_query": normalized_query,
                "user_id": user_id,
                "cached_at": _utcnow().isoformat(),
            }
            if data_skeleton is not None:
                cache_value["data_skeleton"] = data_skeleton

            # 序列化并存储
            ttl_value = ttl or self.default_ttl
            await self.redis.setex(cache_key, ttl_value, json.dumps(cache_value))
            # E-05: embedding 未配置或调用失败时跳过语义载荷（exact-match
            # 缓存仍写入），缓存写路径绝不因 embedding 失败而整体失败
            if embedding_service.is_configured():
                try:
                    embedding_payload = await embedding_service.get_embedding(normalized_query, text_type="query")
                    await self._set_embedding_payload(
                        cache_key=cache_key,
                        embedding=embedding_payload,
                        user_id=user_id,
                        normalized_query=normalized_query,
                        knowledge_version=knowledge_version,
                        ttl=ttl_value,
                        embedding_version=embedding_version or embedding_service.current_embedding_version(),
                    )
                except Exception as emb_exc:
                    logger.debug(f"Semantic cache embedding payload skipped: {emb_exc}")

            # 更新统计
            await ensure_awaitable(self.redis.hincrby(self.STATS_KEY, "total_sets", 1))

            logger.debug(f"Cache SET: query='{query[:30]}...', ttl={ttl_value}s")

            return True

        except Exception as e:
            # V3-FIX-240：写失败必须可观测——按归因落指标（序列化/传输），
            # 不允许只留一行 error 日志静默返回 False
            reason = _write_failure_reason(e)
            SEMANTIC_CACHE_WRITE_FAILURE_TOTAL.labels(reason=reason).inc()
            logger.error(f"Cache SET error ({reason}): {e}")
            return False

    async def invalidate(self, query: str, user_id: str | None = None, knowledge_version: str | None = None) -> bool:
        """
        失效特定缓存

        Args:
            query: 查询文本
            user_id: 用户ID

        Returns:
            是否成功删除
        """
        if not self.redis:
            return False

        try:
            cache_key = self._generate_cache_key(query, user_id, knowledge_version)
            deleted = await self.redis.delete(cache_key)
            logger.info(f"Cache INVALIDATE: query='{query[:30]}...', deleted={deleted}")
            return cast("bool", (deleted > 0))

        except Exception as e:
            logger.error(f"Cache INVALIDATE error: {e}")
            return False

    async def clear_all(self) -> int:
        """
        清空所有语义缓存

        Returns:
            删除的键数量
        """
        if not self.redis:
            return 0

        try:
            # Use SCAN instead of KEYS for production safety
            keys = []
            async for key in self.redis.scan_iter(match=f"{self.CACHE_PREFIX}*"):
                keys.append(key)
            emb_keys = []
            async for key in self.redis.scan_iter(match=f"{self.EMBED_PREFIX}*"):
                emb_keys.append(key)

            if keys or emb_keys:
                delete_keys = list(keys) + list(emb_keys) + [self.KEY_SET]
                deleted = await self.redis.delete(*delete_keys)
                logger.warning(f"Cache CLEAR_ALL: deleted {deleted} keys")
                return cast("int", (deleted))
            else:
                logger.info("Cache CLEAR_ALL: no keys to delete")
                return 0

        except Exception as e:
            logger.error(f"Cache CLEAR_ALL error: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计数据
        """
        if not self.redis:
            return {"error": "Redis not available"}

        try:
            stats_raw = await ensure_awaitable(self.redis.hgetall(self.STATS_KEY))
            stats = {k.decode(): json.loads(v.decode()) for k, v in stats_raw.items()}

            # 计算命中率
            total_requests = stats.get("total_hits", 0) + stats.get("total_misses", 0)
            hit_rate = stats.get("total_hits", 0) / total_requests * 100 if total_requests > 0 else 0

            stats["hit_rate_percent"] = round(hit_rate, 2)
            stats["total_requests"] = total_requests

            return stats

        except Exception as e:
            logger.error(f"Cache STATS error: {e}")
            return {"error": str(e)}

    async def get_cache_size(self) -> int:
        """获取当前缓存大小（键数量）"""
        if not self.redis:
            return 0

        try:
            count = 0
            async for _ in self.redis.scan_iter(match=f"{self.CACHE_PREFIX}*"):
                count += 1
            return count

        except Exception as e:
            logger.error(f"Cache SIZE error: {e}")
            return 0

    # --- High-level methods for KnowledgeRetrievalService ---

    async def get_cached_result(
        self, query: str, user_id: str | None = None, threshold: float = 0.9, knowledge_version: str | None = None
    ) -> list[Any] | None:
        """获取缓存的知识节点列表"""
        # Note: Currently uses exact query match (threshold ignored for now)
        data = await self.get(query, user_id, knowledge_version=knowledge_version)
        if not data or "nodes" not in data:
            return None

        # Rehydrate from JSON
        from app.models.galaxy import KnowledgeNode

        nodes = []
        for node_dict in data["nodes"]:
            # Basic rehydration (just for the fields we need in SearchResultItem)
            # In a real system, we might want to fetch from DB if we need full SQLAlchemy objects,
            # but here we return populated models.
            node = KnowledgeNode()
            for k, v in node_dict.items():
                if hasattr(node, k):
                    setattr(node, k, v)
            nodes.append(node)
        return nodes

    async def cache_result(
        self,
        query: str,
        nodes: list[Any],
        user_id: str | None = None,
        ttl: int | None = None,
        knowledge_version: str | None = None,
    ):
        """缓存知识节点列表"""
        # Serialize nodes to dict
        node_dicts = []
        for node in nodes:
            # Simple serialization
            d = {
                "id": str(node.id),
                "name": node.name,
                "name_en": node.name_en,
                "description": node.description,
                "importance_level": node.importance_level,
                "is_seed": node.is_seed,
            }
            # Add subject/parent info if available
            if node.subject:
                d["subject"] = {"sector_code": node.subject.sector_code}
            if node.parent:
                d["parent"] = {"name": node.parent.name}
            node_dicts.append(d)

        await self.set(query, {"nodes": node_dicts}, user_id, ttl, knowledge_version)


# 便捷函数：创建服务实例
def create_semantic_cache(redis_client: Redis) -> SemanticCacheService:
    """创建语义缓存服务实例"""
    return SemanticCacheService(redis_client=redis_client, default_ttl=3600, max_cache_size=10000)  # 1小时


# 全局实例，使用核心缓存模块的 Redis 客户端
from app.core.cache import cache_service
from app.core.redis_utils import ensure_awaitable

semantic_cache_service = SemanticCacheService(redis_client=cache_service.redis)
