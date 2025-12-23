"""
Redis Caching Module
负责缓存管理，提供装饰器和工具函数
"""
import json
from typing import Any, Optional, Callable, Union
from functools import wraps
import hashlib
import pickle
from datetime import timedelta

import redis.asyncio as redis
from app.config import settings

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
