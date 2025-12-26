"""
Redis Caching Module
负责缓存管理，提供装饰器和工具函数
"""
import json
import asyncio
from typing import Any, Optional, Callable, Union
from functools import wraps
import hashlib
import pickle
from datetime import timedelta

import redis.asyncio as redis
from app.config import settings

from contextlib import asynccontextmanager

class CacheService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.default_ttl = 300  # 5 minutes default

    async def init_redis(self):
        """Initialize Redis connection pool"""
        self.redis = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=False # We use pickle for complex objects
        )

    @asynccontextmanager
    async def distributed_lock(self, lock_key: str, expire: int = 10):
        """
        简单 Redis 分布式锁
        """
        if not self.redis:
            yield # Fallback: No lock if redis is not ready
            return

        # key naming
        key = f"lock:{lock_key}"
        # try to acquire
        locked = await self.redis.set(key, "1", ex=expire, nx=True)
        
        if not locked:
            # Retry once after 1s? Or just fail? For simplicity, we fail or wait.
            # In MVP, let's wait a bit.
            for _ in range(3):
                await asyncio.sleep(0.5)
                locked = await self.redis.set(key, "1", ex=expire, nx=True)
                if locked: break
        
        if not locked:
            raise Exception(f"Failed to acquire lock for {lock_key}")
            
        try:
            yield
        finally:
            # safe release (only if exists)
            await self.redis.delete(key)

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Any:
        if not self.redis: return None
        data = await self.redis.get(key)
        if data:
            return pickle.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: int = None):
        if not self.redis: return
        dumped = pickle.dumps(value)
        await self.redis.set(key, dumped, ex=ttl or self.default_ttl)

    async def delete(self, key: str):
        if not self.redis: return
        await self.redis.delete(key)
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.redis: return
        # Scan and delete
        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)

cache_service = CacheService()

def cached(
    ttl: int = 300, 
    key_builder: Callable = None, 
    namespace: str = "view"
):
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
