"""
Redis Caching Module
负责缓存管理，提供装饰器和工具函数
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from functools import wraps
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.core.redis_utils import format_redis_url_for_log, resolve_redis_password


class CacheService:
    def __init__(self):
        self.redis: redis.Redis | None = None
        self.default_ttl = 300  # 5 minutes default
        self._local_cache: dict[str, tuple[Any, float | None]] = {}
        self._local_cache_ops = 0
        self._local_cache_cleanup_interval = 100
        self._max_local_cache_entries = 5000

    async def init_redis(self):
        """Initialize Redis connection pool"""
        password, password_source = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
        kwargs = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        if password:
            kwargs["password"] = password

        # Log connection attempt (masked)
        safe_url = format_redis_url_for_log(settings.REDIS_URL)
        logger.info(
            "Connecting to Redis Cache: {}, Password={}, PasswordSource={}".format(
                safe_url,
                "Yes" if password else "No",
                password_source,
            )
        )

        self.redis = redis.from_url(settings.REDIS_URL, **kwargs)
        try:
            await self.redis.ping()
            logger.info("Redis Cache initialized successfully")
        except Exception as e:
            self.redis = None
            logger.warning(f"Redis Cache connection failed: {e}")
            logger.warning("To start Redis: `docker compose up -d redis` or `systemctl start redis`")

    # Lua script: delete the lock key only if its value matches the expected token.
    # Prevents a late-releasing holder from deleting a lock already re-acquired by
    # another caller (TOCTOU: check-then-delete must be atomic).
    _RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

    @asynccontextmanager
    async def distributed_lock(self, lock_key: str, expire: int = 10):
        """
        Redis 分布式锁（使用 Lua 脚本原子释放，防止 TOCTOU 竞态）
        """
        import secrets

        if not self.redis:
            yield  # Fallback: No lock if redis is not ready
            return

        key = f"lock:{lock_key}"
        token = secrets.token_hex(16)

        locked = await self.redis.set(key, token, ex=expire, nx=True)

        if not locked:
            for attempt in range(3):
                await asyncio.sleep(min(0.2 * (2**attempt), 1.0))
                locked = await self.redis.set(key, token, ex=expire, nx=True)
                if locked:
                    break

        if not locked:
            raise Exception(f"Failed to acquire lock for {lock_key}")

        try:
            yield
        finally:
            # Atomically release only if we still own the lock
            try:
                await self.redis.eval(self._RELEASE_LOCK_SCRIPT, 1, key, token)
            except Exception as e:
                logger.warning(f"Failed to release lock for {lock_key}: {e}")

    async def close(self):
        if self.redis:
            if hasattr(self.redis, "aclose"):
                await self.redis.aclose()
            else:
                await self.redis.close()

    async def get(self, key: str) -> Any:
        if not self.redis:
            self._maybe_cleanup_local_cache()
            cached = self._local_cache.get(key)
            if cached is None:
                return None
            value, expires_at = cached
            if expires_at is not None and time.time() > expires_at:
                self._local_cache.pop(key, None)
                return None
            return value
        data = await self.redis.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data

    async def set(self, key: str, value: Any, ttl: int = None, ex: int = None):
        # Support both 'ttl' and 'ex' parameter names (standard Redis naming)
        ttl_value = ttl or ex
        if not self.redis:
            self._maybe_cleanup_local_cache()
            expires_at = None
            effective_ttl = ttl_value or self.default_ttl
            if effective_ttl:
                expires_at = time.time() + effective_ttl
            self._local_cache[key] = (value, expires_at)
            self._maybe_cleanup_local_cache()
            return
        dumped = json.dumps(value, default=_json_default, ensure_ascii=True)
        await self.redis.set(key, dumped, ex=ttl_value or self.default_ttl)

    async def incr(self, key: str, amount: int = 1) -> int:
        if not self.redis:
            return 0
        return await self.redis.incrby(key, amount)

    async def expire(self, key: str, ttl: int) -> bool:
        if not self.redis:
            return False
        return await self.redis.expire(key, ttl)

    async def delete(self, key: str):
        if not self.redis:
            self._local_cache.pop(key, None)
            return
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.redis:
            return
        # Scan and delete
        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)

    def _maybe_cleanup_local_cache(self):
        self._local_cache_ops += 1
        needs_cleanup = (
            self._local_cache_ops % self._local_cache_cleanup_interval == 0
            or len(self._local_cache) > self._max_local_cache_entries
        )
        if not needs_cleanup:
            return

        now = time.time()
        expired_keys = [
            key for key, (_, expires_at) in self._local_cache.items() if expires_at is not None and now > expires_at
        ]
        for key in expired_keys:
            self._local_cache.pop(key, None)

        overflow = len(self._local_cache) - self._max_local_cache_entries
        if overflow <= 0:
            return
        # Remove oldest keys first (dict preserves insertion order on Python 3.7+).
        keys_to_remove = list(self._local_cache.keys())[:overflow]
        for key in keys_to_remove:
            self._local_cache.pop(key, None)


cache_service = CacheService()


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def cached(ttl: int = 300, key_builder: Callable = None, namespace: str = "view"):
    """
    Cache Decorator for Async Functions

    :param ttl: Time to live in seconds
    :param key_builder: Custom function to build cache key from args
    :param namespace: Key prefix
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. Build Key
            if key_builder:
                key_part = key_builder(*args, **kwargs)
            else:
                # Default: hash of args/kwargs
                # Note: This is simplistic. For complex objects (like Pydantic models in args),
                # you might need a custom key_builder.
                # Here we assume arguments are simple or we just use function name + basic args string
                arg_str = str(args) + str(kwargs)
                key_part = hashlib.md5(arg_str.encode()).hexdigest()

            cache_key = f"{settings.APP_NAME}:{namespace}:{func.__name__}:{key_part}"

            # 2. Check Cache
            cached_val = await cache_service.get(cache_key)
            if cached_val is not None:
                return cached_val

            # 3. Execute Function
            result = await func(*args, **kwargs)

            # 4. Save to Cache
            # Only cache if result is not None (optional decision)
            if result is not None:
                await cache_service.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator
