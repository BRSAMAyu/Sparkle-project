import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis.asyncio import Redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from app.config import settings
from app.core.redis_utils import resolve_redis_password
from loguru import logger

async def init_semantic_cache_index():
    """Initialize Redis Search Index for Semantic Cache (idx:embeddings)"""
    logger.info("Connecting to Redis...")
    # decode_responses=False is important for vector binary data, but for commands we might need mixed.
    # The redis-py client handles arguments well usually.
    resolved_password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
    redis = Redis.from_url(settings.REDIS_URL, password=resolved_password, decode_responses=False)
    
    index_name = "idx:embeddings"
    
    try:
        await redis.ft(index_name).info()
        logger.info(f"Index '{index_name}' already exists.")
        # Optional: Drop if you want to force schema update
        # await redis.ft(index_name).dropindex()
    except Exception:
        logger.info(f"Creating index '{index_name}'...")
        
        # Schema: 
        # - payload: The cached text response
        # - vector: The query embedding
        schema = (
            TextField("payload", weight=1.0),
            VectorField(
                "vector",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": settings.EMBEDDING_DIM, # Ensure this matches your model (e.g. 1536 for OpenAI)
                    "DISTANCE_METRIC": "COSINE",
                }
            ),
        )

        # Definition: Index hashes with prefix "cache:vec:"
        definition = IndexDefinition(prefix=["cache:vec:"], index_type=IndexType.HASH)

        try:
            await redis.ft(index_name).create_index(schema, definition=definition)
            logger.success(f"Index '{index_name}' created successfully!")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")

    await redis.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_semantic_cache_index())
