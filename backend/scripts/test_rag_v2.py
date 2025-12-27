import asyncio
import sys
import os
import uuid
from loguru import logger

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add current directory to import sibling scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, AsyncMock

from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode
from app.models.subject import Subject
from app.services.galaxy_service import GalaxyService
from app.services.rerank_service import rerank_service
from app.services.embedding_service import embedding_service
from sync_pg_to_redis import sync_data

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Mock Embedding Service
dummy_vector = [0.1] * 1536
embedding_service.get_embedding = AsyncMock(return_value=dummy_vector)
embedding_service.batch_embeddings = AsyncMock(side_effect=lambda texts: [dummy_vector] * len(texts))

async def test_rag_flow():
    """Test RAG v2.0 Flow"""
    logger.info("🧪 Starting RAG v2.0 Test...")
    
    # Ensure Reranker is loaded
    await rerank_service.ensure_model_loaded()
    
    # 1. Create Data
    dummy_id = uuid.uuid4()
    dummy_name = f"TestNode_{dummy_id.hex[:8]}"
    dummy_desc = "RAG v2.0 is a hybrid retrieval system using Redis and Reranking. It combines Vector search and BM25."
    
    async with AsyncSessionLocal() as session:
        # Check if we need a subject
        # Create dummy node
        node = KnowledgeNode(
            id=dummy_id,
            name=dummy_name,
            description=dummy_desc,
            importance_level=1,
            source_type='test',
            is_seed=False,
            keywords=["rag", "redis", "hybrid"]
        )
        session.add(node)
        await session.commit()
        logger.info(f"✅ Created dummy node: {dummy_name}")

    # 2. Sync to Redis
    await sync_data()
    
    # 3. Search
    async with AsyncSessionLocal() as session:
        galaxy_service = GalaxyService(session)
        user_id = uuid.uuid4() # Dummy user
        
        query = "hybrid retrieval system"
        logger.info(f"🔍 Searching for: '{query}'")
        
        results = await galaxy_service.hybrid_search(
            user_id=user_id,
            query=query,
            limit=5
        )
        
        found = False
        for item in results:
            logger.info(f"   -> Found: {item.node.name}")
            if item.node.id == dummy_id:
                found = True
        
        if found:
            logger.success("✅ Test Passed: Dummy node found via Hybrid Search!")
        else:
            logger.error("❌ Test Failed: Dummy node NOT found.")

    # 4. Cleanup
    async with AsyncSessionLocal() as session:
        node = await session.get(KnowledgeNode, dummy_id)
        if node:
            await session.delete(node)
            await session.commit()
            logger.info("🧹 Cleanup complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_rag_flow())
