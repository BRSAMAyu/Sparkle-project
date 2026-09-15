"""
Intent Classification Cache

Reduces LLM calls by caching intent classification results for common patterns.
Target: 60%+ cache hit rate, sub-millisecond lookup latency.
"""
import hashlib
import json

from loguru import logger


class IntentCache:
    """Intent classification result cache

    Caches common intent patterns to reduce expensive LLM calls.
    Uses message hash as key for fast lookup.

    Performance targets:
    - Cache hit latency: <1ms (Redis lookup)
    - Cache TTL: 1 hour (patterns remain valid)
    - Hit rate target: 60%+
    """

    CACHE_KEY_PREFIX = "intent:cache:"
    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self, redis_client, ttl: int = DEFAULT_TTL):
        """
        Args:
            redis_client: Redis client instance (aioredis)
            ttl: Cache time-to-live in seconds
        """
        self.redis = redis_client
        self.ttl = ttl

        if not redis_client:
            logger.warning("IntentCache initialized without Redis client (cache disabled)")

    def _hash_message(self, message: str) -> str:
        """Generate stable hash for message

        Uses SHA256 for fast collision-resistant hashing.
        Normalizes whitespace before hashing.
        """
        # Normalize: lowercase, strip extra whitespace
        normalized = " ".join(message.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def get_cached_intent(self, message: str) -> tuple[str, float] | None:
        """Get cached intent classification

        Args:
            message: User message to look up

        Returns:
            (intent, confidence) tuple if cached, None otherwise
        """
        if not self.redis:
            return None

        try:
            message_hash = self._hash_message(message)
            key = f"{self.CACHE_KEY_PREFIX}{message_hash}"

            cached = await self.redis.get(key)
            if cached:
                data = json.loads(cached)
                logger.debug(f"Intent cache HIT: '{message[:30]}...' -> {data['intent']}")
                return data["intent"], data["confidence"]
            else:
                logger.debug(f"Intent cache MISS: '{message[:30]}...'")

        except Exception as e:
            logger.warning(f"Intent cache lookup failed: {e}")

        return None

    async def cache_intent(
        self,
        message: str,
        intent: str,
        confidence: float,
        source: str = "classifier"
    ):
        """Cache intent classification result

        Args:
            message: User message
            intent: Classified intent
            confidence: Confidence score
            source: Classification source (llm/keyword/rules)
        """
        if not self.redis:
            return

        try:
            message_hash = self._hash_message(message)
            key = f"{self.CACHE_KEY_PREFIX}{message_hash}"

            data = {
                "intent": intent,
                "confidence": confidence,
                "source": source
            }

            await self.redis.setex(key, self.ttl, json.dumps(data))
            logger.debug(f"Cached intent: {intent} (conf={confidence:.2f}, src={source})")

        except Exception as e:
            logger.warning(f"Intent cache write failed: {e}")

    async def get_cache_stats(self) -> dict:
        """Get cache statistics (if available)

        Returns:
            Dictionary with cache stats
        """
        if not self.redis:
            return {"enabled": False}

        try:
            # Get cache info using Redis INFO
            info = await self.redis.info("stats")
            return {
                "enabled": True,
                "ttl_seconds": self.ttl,
                "key_count": info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    async def clear_user_cache(self, pattern: str = "*"):
        """Clear cache entries matching pattern

        Args:
            pattern: Glob pattern for keys to delete (default: all)
        """
        if not self.redis:
            return

        try:
            search_pattern = f"{self.CACHE_KEY_PREFIX}{pattern}"
            keys = await self.redis.keys(search_pattern)

            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} intent cache entries")

        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
