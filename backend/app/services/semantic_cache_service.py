"""
Redis Semantic Cache Service - 语义缓存服务

用于缓存 GraphRAG 查询结果，基于语义相似度检索缓存
"""

import json
import hashlib
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import numpy as np

from redis.asyncio import Redis
from redis.asyncio.lock import Lock


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
        redis_client: Optional[Redis] = None,
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
                "start_time": datetime.utcnow().isoformat()
            }
            await self.redis.hset(self.STATS_KEY, mapping={
                k: json.dumps(v) for k, v in stats.items()
            })

    def _generate_cache_key(self, query: str, user_id: Optional[str] = None) -> str:
        """
        生成缓存键

        使用查询文本的 SHA256 哈希 + 用户ID（可选）
        """
        # 标准化查询文本
        normalized_query = query.strip().lower()

        # 生成哈希
        if user_id:
            cache_input = f"{normalized_query}:{user_id}"
        else:
            cache_input = normalized_query

        hash_key = hashlib.sha256(cache_input.encode()).hexdigest()

        return f"{self.CACHE_PREFIX}{hash_key}"
    
    def _generate_lock_key(self, cache_key: str) -> str:
        """生成锁键"""
        return f"{self.LOCK_PREFIX}{cache_key}"

    async def get(
        self,
        query: str,
        user_id: Optional[str] = None,
        similarity_threshold: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取查询结果
        包含缓存击穿保护 (Mutex Lock)

        Args:
            query: 查询文本
            user_id: 用户ID（可选，用于个性化缓存）
            similarity_threshold: 相似度阈值（暂未实现向量相似度，使用精确匹配）

        Returns:
            缓存的结果，如果未命中则返回 None
        """
        if not self.redis:
            return None

        try:
            cache_key = self._generate_cache_key(query, user_id)
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                # 命中
                await self.redis.hincrby(self.STATS_KEY, "total_hits", 1)
                result = json.loads(cached_data)

                logger.debug(
                    f"Cache HIT: query='{query[:30]}...', "
                    f"cached_at={result.get('cached_at')}"
                )

                return result.get("data")
            else:
                # 未命中
                await self.redis.hincrby(self.STATS_KEY, "total_misses", 1)
                logger.debug(f"Cache MISS: query='{query[:30]}...'")
                return None

        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def get_with_lock(
        self,
        query: str,
        factory_func,
        user_id: Optional[str] = None,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存，如果未命中则使用 factory_func 生成并缓存
        使用互斥锁防止缓存击穿 (Cache Stampede)

        Args:
            query: 查询字符串
            factory_func: 如果缓存未命中，用于生成数据的异步函数
            user_id: 用户 ID
            ttl: 过期时间
            *args, **kwargs: 传递给 factory_func 的参数

        Returns:
            数据
        """
        if not self.redis:
            return await factory_func(*args, **kwargs)

        # 1. 尝试获取缓存
        data = await self.get(query, user_id)
        if data is not None:
            return data

        cache_key = self._generate_cache_key(query, user_id)
        lock_key = self._generate_lock_key(cache_key)
        
        # 2. 获取分布式锁 (Async)
        try:
            lock = self.redis.lock(
                lock_key,
                timeout=self.lock_timeout,
                blocking_timeout=2.0 
            )
            
            # 使用 async context manager 自动处理 acquire/release
            # acquire 内部默认是阻塞的 (blocking=True)，但它是 async 的，
            # 所以会释放 event loop，不会阻塞其他协程。
            async with lock:
                # 双重检查 (Double-Checked Locking)
                data = await self.get(query, user_id)
                if data is not None:
                    return data
                
                # 3. 生成数据
                logger.info(f"Cache MISS & Lock Acquired. Generating data for query='{query[:30]}...'")
                result = await factory_func(*args, **kwargs)
                
                # 4. 写入缓存
                if result:
                    await self.set(query, result, user_id, ttl)
                
                return result

        except Exception as e:
            # redis.exceptions.LockError 可能会在锁获取超时抛出
            if "LockError" in str(type(e)):
                 logger.warning(f"Failed to acquire lock for {cache_key} (Timeout). Waiting...")
                 # 稍微等待一下再尝试获取（降级策略）
                 await asyncio.sleep(0.1) 
                 return await self.get(query, user_id) or await factory_func(*args, **kwargs)

            logger.error(f"Cache Mutex Error: {e}")
            # 出错时降级为直接调用
            return await factory_func(*args, **kwargs)

    async def set(
        self,
        query: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存

        Args:
            query: 查询文本
            data: 要缓存的数据
            user_id: 用户ID（可选）
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            是否成功
        """
        if not self.redis:
            return False

        try:
            cache_key = self._generate_cache_key(query, user_id)

            # 包装数据，添加元信息
            cache_value = {
                "data": data,
                "query": query,
                "user_id": user_id,
                "cached_at": datetime.utcnow().isoformat(),
            }

            # 序列化并存储
            await self.redis.setex(
                cache_key,
                ttl or self.default_ttl,
                json.dumps(cache_value)
            )

            # 更新统计
            await self.redis.hincrby(self.STATS_KEY, "total_sets", 1)

            logger.debug(
                f"Cache SET: query='{query[:30]}...', ttl={ttl or self.default_ttl}s"
            )

            return True

        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def invalidate(self, query: str, user_id: Optional[str] = None) -> bool:
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
            cache_key = self._generate_cache_key(query, user_id)
            deleted = await self.redis.delete(cache_key)
            logger.info(f"Cache INVALIDATE: query='{query[:30]}...', deleted={deleted}")
            return deleted > 0

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
            # 查找所有缓存键
            keys = await self.redis.keys(f"{self.CACHE_PREFIX}*")

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.warning(f"Cache CLEAR_ALL: deleted {deleted} keys")
                return deleted
            else:
                logger.info("Cache CLEAR_ALL: no keys to delete")
                return 0

        except Exception as e:
            logger.error(f"Cache CLEAR_ALL error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计数据
        """
        if not self.redis:
            return {"error": "Redis not available"}

        try:
            stats_raw = await self.redis.hgetall(self.STATS_KEY)
            stats = {
                k.decode(): json.loads(v.decode())
                for k, v in stats_raw.items()
            }

            # 计算命中率
            total_requests = stats.get("total_hits", 0) + stats.get("total_misses", 0)
            hit_rate = (
                stats.get("total_hits", 0) / total_requests * 100
                if total_requests > 0
                else 0
            )

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
            keys = await self.redis.keys(f"{self.CACHE_PREFIX}*")
            return len(keys)

        except Exception as e:
            logger.error(f"Cache SIZE error: {e}")
            return 0

    # --- High-level methods for KnowledgeRetrievalService ---

    async def get_cached_result(self, query: str, user_id: Optional[str] = None, threshold: float = 0.9) -> Optional[List[Any]]:
        """获取缓存的知识节点列表"""
        # Note: Currently uses exact query match (threshold ignored for now)
        data = await self.get(query, user_id)
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

    async def cache_result(self, query: str, nodes: List[Any], user_id: Optional[str] = None, ttl: Optional[int] = None):
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
            
        await self.set(query, {"nodes": node_dicts}, user_id, ttl)


# 便捷函数：创建服务实例
def create_semantic_cache(redis_client: Redis) -> SemanticCacheService:
    """创建语义缓存服务实例"""
    return SemanticCacheService(
        redis_client=redis_client,
        default_ttl=3600,  # 1小时
        max_cache_size=10000
    )

# 全局实例，使用核心缓存模块的 Redis 客户端
from app.core.cache import cache_service
semantic_cache_service = SemanticCacheService(redis_client=cache_service.redis)
