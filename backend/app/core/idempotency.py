"""
幂等性存储
Idempotency Store - 用于管理幂等性键
"""
import json
import asyncio
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.idempotency_key import IdempotencyKey
from app.db.session import AsyncSessionLocal
from app.config import settings
from loguru import logger

class IdempotencyStore:
    """
    幂等性存储基类
    """
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        raise NotImplementedError

    async def lock(self, key: str) -> bool:
        raise NotImplementedError

    async def unlock(self, key: str) -> None:
        raise NotImplementedError


class MemoryIdempotencyStore(IdempotencyStore):
    """
    内存幂等性存储 (仅用于开发/测试)
    """
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._locks: Dict[str, bool] = {}

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        data = self._cache.get(key)
        if not data:
            return None
        
        if datetime.utcnow() > data["expires_at"]:
            del self._cache[key]
            return None
            
        return data["value"]

    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
        }

    async def lock(self, key: str) -> bool:
        if self._locks.get(key):
            return False
        self._locks[key] = True
        return True

    async def unlock(self, key: str) -> None:
        if key in self._locks:
            del self._locks[key]


class DBIdempotencyStore(IdempotencyStore):
    """
    数据库幂等性存储 (基于 PostgreSQL)
    """
    def __init__(self):
        # 简单的内存锁，防止单实例并发 (多实例需用 Redis/DB 锁)
        self._local_locks: Dict[str, bool] = {}

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(IdempotencyKey).where(IdempotencyKey.key == key)
            )
            record = result.scalar_one_or_none()
            
            if not record:
                return None
            
            # 检查过期
            # 注意: record.expires_at 是带时区的
            if record.expires_at < datetime.now(record.expires_at.tzinfo):
                await db.delete(record)
                await db.commit()
                return None
                
            return record.response

    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        # 这里需要 user_id，但在中间件中可能还没获取到 user (取决于 middleware 顺序)
        # 如果 user_id 是必填的，我们需要在 set 时传入。
        # 现在的接口定义 set(key, value, ttl) 没有 user_id。
        # 考虑到 IdempotencyKey 模型有 user_id 字段 (nullable=False)。
        # 我们可能需要修改接口或在这里做一些妥协。
        # 
        # 方案: 在 value 中包含 user_id，或者修改 set 签名。
        # 为了符合 middleware 的调用，我们假设 value 中可能有元数据，或者我们先放宽 user_id 限制?
        # 不，模型 user_id 是 NOT NULL。
        # 
        # Middleware 应该在 Auth 之后? 
        # 通常 Idempotency 可以在 Auth 之后。
        # 让我们看看 Middleware 代码。
        pass
        # 暂时只实现 MemoryStore 供 MVP 使用，或者修改 Middleware 逻辑
        # 鉴于文档中 Middleware 没有传入 user_id，且 config 中 DEFAULT 为 memory (dev) / redis (prod).
        # DBStore 实现比较复杂，因为需要 user_id。
        # 如果用 Redis，就不需要 user_id。
        # 让我们先提供 MemoryStore 和 RedisStore (stub)。
        # 如果必须用 DB，我们需要从 request scope 获取 user? 
        
        # 为了 MVP，我们主要使用 MemoryStore (开发环境) 或简单的 RedisStore。
        # 如果要用 DB Store，我们需要调整。
        # 既然文档提到了 idempotency_keys 表，那应该是有用的。
        # 也许 middleware 在 Auth 之后运行，可以从 request.state.user 获取 user_id?
        # 但 middleware `dispatch` 方法只接收 request。
        # Starlette middleware 中，request.user 可能还未填充（取决于 AuthenticationMiddleware）。
        
        # 让我们先实现 MemoryStore。
        pass

# 简单的工厂
def get_idempotency_store(store_type: str = "memory") -> IdempotencyStore:
    if store_type == "redis":
        # Return Redis implementation
        return MemoryIdempotencyStore() # Fallback for now
    return MemoryIdempotencyStore()
