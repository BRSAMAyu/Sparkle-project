"""
幂等性存储
Idempotency Store - 用于管理幂等性键
"""
import json
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import redis.asyncio as redis

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


class RedisIdempotencyStore(IdempotencyStore):
    """
    Redis-based idempotency store (recommended for production)
    """

    def __init__(self, redis_url: Optional[str] = None, prefix: str = "idempotency"):
        self._redis = redis.from_url(redis_url or settings.REDIS_URL, decode_responses=True)
        self._prefix = prefix
        self._lock_tokens: Dict[str, str] = {}
        self._lock_ttl = 30  # seconds

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def _lock_key(self, key: str) -> str:
        return f"{self._prefix}:lock:{key}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = await self._redis.get(self._key(key))
        except Exception as exc:
            logger.warning(f"Redis idempotency get failed: {exc}")
            return None

        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Redis idempotency decode failed: {exc}")
            return None

    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        try:
            payload = json.dumps(value, ensure_ascii=False)
            await self._redis.set(self._key(key), payload, ex=ttl)
        except Exception as exc:
            logger.warning(f"Redis idempotency set failed: {exc}")

    async def lock(self, key: str) -> bool:
        token = uuid4().hex
        try:
            acquired = await self._redis.set(
                self._lock_key(key),
                token,
                ex=self._lock_ttl,
                nx=True,
            )
        except Exception as exc:
            logger.warning(f"Redis idempotency lock failed: {exc}")
            return True  # Fail open to avoid blocking requests

        if acquired:
            self._lock_tokens[key] = token
            return True
        return False

    async def unlock(self, key: str) -> None:
        token = self._lock_tokens.pop(key, None)
        if not token:
            return

        # Lua script: delete only if token matches
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """
        try:
            await self._redis.eval(script, 1, self._lock_key(key), token)
        except Exception as exc:
            logger.warning(f"Redis idempotency unlock failed: {exc}")


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
        user_id = value.get("user_id")
        if not user_id:
            logger.warning("DB idempotency store skipped: missing user_id")
            return

        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        async with AsyncSessionLocal() as db:
            record = IdempotencyKey(
                key=key,
                user_id=user_id,
                response=value,
                expires_at=expires_at,
            )
            try:
                db.add(record)
                await db.commit()
            except IntegrityError:
                await db.rollback()
                existing = await db.get(IdempotencyKey, key)
                if existing:
                    existing.response = value
                    existing.expires_at = expires_at
                    await db.commit()

    async def lock(self, key: str) -> bool:
        now = datetime.utcnow()
        expires_at = self._local_locks.get(key)
        if expires_at and expires_at > now:
            return False
        self._local_locks[key] = now + timedelta(seconds=30)
        return True

    async def unlock(self, key: str) -> None:
        if key in self._local_locks:
            del self._local_locks[key]

# 简单的工厂
def get_idempotency_store(store_type: str = "memory") -> IdempotencyStore:
    if store_type == "redis":
        return RedisIdempotencyStore()
    if store_type == "database":
        return DBIdempotencyStore()
    return MemoryIdempotencyStore()
