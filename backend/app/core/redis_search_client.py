import struct
from typing import List, Dict, Any, Optional
from redis.asyncio import Redis
from redis.commands.search.query import Query
from loguru import logger
from app.config import settings
from app.core.redis_utils import resolve_redis_password

class RedisSearchClient:
    """
    Wrapper for Redis Search (RediSearch)
    Handles Vector Search + Hybrid Search
    """
    def __init__(self, redis_url: str = settings.REDIS_URL, password: Optional[str] = settings.REDIS_PASSWORD):
        resolved_password, _ = resolve_redis_password(redis_url, password)
        self.redis = Redis.from_url(redis_url, password=resolved_password, decode_responses=True)
        self.index_name = "idx:knowledge"

    async def search(self, query: Query, query_params: Optional[Dict[str, Any]] = None):
        """Execute a search query"""
        try:
            return await self.redis.ft(self.index_name).search(query, query_params)
        except Exception as e:
            logger.error(f"Redis search failed: {e}")
            return None

    async def hybrid_search(
        self,
        text_query: str,
        vector: List[float],
        top_k: int = 10,
        vector_field: str = "vector"
    ):
        """
        Perform Hybrid Search (Text Filter + Vector Similarity)
        Syntax: (<text_query>) => [KNN <k> @vector $vec_param AS vector_score]
        """
        # 1. Prepare Vector Blob
        # Convert list of floats to binary string (Little Endian Float32)
        vector_blob = struct.pack(f'{len(vector)}f', *vector)
        
        # 2. Construct Query
        # If text_query is empty, use wildcard
        actual_text = text_query if text_query.strip() else "*"
        
        # RediSearch Query Syntax for Hybrid
        # We want to pre-filter by text, then run KNN on the result.
        # Format: "text_query=>[KNN k @vector $vec AS score]"
        q_str = f"({actual_text})=>[KNN {top_k} @{vector_field} $vec AS vector_score]"
        
        q = (
            Query(q_str)
            .sort_by("vector_score")
            .paging(0, top_k)
            .return_fields("id", "parent_id", "content", "vector_score", "parent_name", "importance")
            .dialect(2)
        )
        
        params = {"vec": vector_blob}
        
        return await self.search(q, params)

    async def close(self):
        await self.redis.close()

# Global Instance
redis_search_client = RedisSearchClient()
