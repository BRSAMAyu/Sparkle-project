import json
import time
import asyncio
from typing import Optional, Dict
from loguru import logger
from functools import wraps
import networkx as nx

class RouteCache:
    """Multi-level cache: L1(Memory) + L2(Redis)"""
    
    def __init__(self, redis_client, ttl: int = 300):
        self.redis = redis_client
        self.ttl = ttl
        self.local_cache = {}
        self.local_ttl = {}
        self._local_hits = 0
        self._redis_hits = 0
        self._total_requests = 0
    
    async def get_route(self, source: str, target: str) -> Optional[str]:
        """Query cache"""
        self._total_requests += 1
        cache_key = f"route:{source}->{target}"
        
        # L1: Local Memory
        if cache_key in self.local_cache:
            if self._is_local_cache_valid(cache_key):
                logger.debug(f"L1 Cache HIT: {cache_key}")
                self._local_hits += 1
                return self.local_cache[cache_key]
            else:
                del self.local_cache[cache_key]
                del self.local_ttl[cache_key]
        
        # L2: Redis
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                self.local_cache[cache_key] = cached
                self.local_ttl[cache_key] = time.time() + 60 # Local TTL shorter
                logger.debug(f"L2 Cache HIT: {cache_key}")
                self._redis_hits += 1
                return cached
            else:
                logger.debug(f"Cache MISS: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Redis cache error: {e}")
            return None
    
    async def set_route(self, source: str, target: str, route: str, ttl: Optional[int] = None):
        """Set cache"""
        cache_key = f"route:{source}->{target}"
        ttl = ttl or self.ttl
        
        self.local_cache[cache_key] = route
        self.local_ttl[cache_key] = time.time() + 60
        
        try:
            await self.redis.setex(cache_key, ttl, route)
            logger.debug(f"Cache SET: {cache_key}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"Failed to set Redis cache: {e}")
    
    def invalidate(self, source: str, target: str):
        """Invalidate cache"""
        cache_key = f"route:{source}->{target}"
        self.local_cache.pop(cache_key, None)
        self.local_ttl.pop(cache_key, None)
        asyncio.create_task(self._invalidate_redis(cache_key))
    
    async def _invalidate_redis(self, cache_key: str):
        try:
            await self.redis.delete(cache_key)
        except Exception as e:
            logger.error(f"Failed to invalidate Redis cache: {e}")
    
    def _is_local_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.local_ttl:
            return False
        return time.time() < self.local_ttl[cache_key]
    
    def clear_local(self):
        self.local_cache.clear()
        self.local_ttl.clear()
        logger.info("Local cache cleared")
    
    async def get_stats(self) -> Dict:
        return {
            "local_size": len(self.local_cache),
            "local_hit_rate": self._local_hits / max(self._total_requests, 1),
            "redis_hit_rate": self._redis_hits / max(self._total_requests, 1)
        }

class PrecomputedRouter:
    """Pre-compute optimal paths for all node pairs"""
    
    def __init__(self, graph_router, cache: RouteCache):
        self.graph = graph_router
        self.cache = cache
        self.precomputed = False
    
    async def find_route(self, source: str, target: str) -> Optional[str]:
        # 1. Cache
        cached = await self.cache.get_route(source, target)
        if cached:
            return cached
        
        # 2. Compute
        route = self._compute_route(source, target)
        
        # 3. Cache
        if route:
            await self.cache.set_route(source, target, route)
        
        return route
    
    def _compute_route(self, source: str, target: str) -> Optional[str]:
        try:
            if source not in self.graph.graph or target not in self.graph.graph:
                return None
            
            path = nx.shortest_path(
                self.graph.graph,
                source=source,
                target=target,
                weight="weight"
            )
            
            if len(path) > 1:
                return path[1]
            else:
                return None
                
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.error(f"Route computation error: {e}")
            return None
    
    async def precompute_all(self):
        nodes = list(self.graph.graph.nodes())
        total = len(nodes) * (len(nodes) - 1)
        
        logger.info(f"Precomputing {total} routes...")
        
        count = 0
        for source in nodes:
            for target in nodes:
                if source != target:
                    route = self._compute_route(source, target)
                    if route:
                        await self.cache.set_route(source, target, route, ttl=3600)
                    count += 1
        
        self.precomputed = True
        logger.info("Precomputation complete")

def cache_route(cache: RouteCache):
    """Decorator for route caching"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, source: str, target: str, *args, **kwargs):
            cached = await cache.get_route(source, target)
            if cached:
                return cached
            
            result = await func(self, source, target, *args, **kwargs)
            
            if result:
                await cache.set_route(source, target, result)
            
            return result
        return wrapper
    return decorator
