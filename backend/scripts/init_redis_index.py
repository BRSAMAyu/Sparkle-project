import asyncio
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis.asyncio import Redis
from redis.commands.search.field import TextField, NumericField, VectorField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from app.config import settings
from app.core.redis_utils import resolve_redis_password
from loguru import logger

async def init_index():
    """Initialize Redis Search Index for RAG v2.0"""
    logger.info("Connecting to Redis...")
    # Ensure decode_responses=True for text handling
    resolved_password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
    redis = Redis.from_url(settings.REDIS_URL, password=resolved_password, decode_responses=True)
    
    index_name = "idx:knowledge"
    
    try:
        # Check if index exists
        await redis.ft(index_name).info()
        logger.info(f"Index '{index_name}' already exists. Dropping to update schema...")
        await redis.ft(index_name).dropindex(delete_documents=False)
    except Exception:
        pass
        
    logger.info(f"Creating index '{index_name}'...")
    
    # Schema Definition
    schema = (
        TextField("$.content", as_name="content", weight=1.0),
        TextField("$.keywords", as_name="keywords", weight=2.0),
        TagField("$.parent_id", as_name="parent_id"),
        TextField("$.parent_name", as_name="parent_name"),
        NumericField("$.subject_id", as_name="subject_id"),
        NumericField("$.importance", as_name="importance"),
        # Vector Field Definition
        VectorField(
            "$.vector",
            "HNSW",
            {
                "TYPE": "FLOAT32",
                "DIM": settings.EMBEDDING_DIM,
                "DISTANCE_METRIC": "COSINE",
                "M": 16,
                "EF_CONSTRUCTION": 200, 
            },
            as_name="vector",
        ),
    )

    # Index Definition
    definition = IndexDefinition(prefix=["sparkle:chunk:"], index_type=IndexType.JSON)

    try:
        await redis.ft(index_name).create_index(schema, definition=definition)
        logger.success(f"Index '{index_name}' created successfully!")
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        raise e

    await redis.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_index())
