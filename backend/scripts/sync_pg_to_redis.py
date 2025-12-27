import asyncio
import sys
import os
import json
import logging

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from redis.asyncio import Redis
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode
from app.services.embedding_service import embedding_service
from app.config import settings

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

async def sync_data():
    """Sync KnowledgeNodes from Postgres to Redis with Chunking"""
    logger.info("🚀 Starting PG -> Redis Sync...")

    # 1. Connect to Redis
    redis = Redis.from_url(settings.REDIS_URL, password=settings.REDIS_PASSWORD, decode_responses=True)
    try:
        await redis.ping()
        logger.info("✅ Redis connected.")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return

    # 2. Connect to Postgres & Fetch Nodes
    logger.info("📦 Fetching KnowledgeNodes from DB...")
    async with AsyncSessionLocal() as session:
        stmt = select(KnowledgeNode).where(KnowledgeNode.description.isnot(None))
        result = await session.execute(stmt)
        nodes = result.scalars().all()
    
    logger.info(f"📊 Found {len(nodes)} nodes with descriptions.")

    # 3. Setup Splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400, # Approx 100-200 tokens
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", ".", " ", ""]
    )

    # 4. Process Nodes
    pipeline = redis.pipeline()
    count = 0
    
    for node in nodes:
        if not node.description:
            continue
            
        chunks = text_splitter.split_text(node.description)
        
        # Batch embedding if possible, but embedding_service handles batching?
        # embedding_service.batch_embeddings takes a list of strings.
        try:
            embeddings = await embedding_service.batch_embeddings(chunks)
        except Exception as e:
            logger.error(f"⚠️ Failed to embed node {node.id}: {e}")
            continue

        for i, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
            key = f"sparkle:chunk:{node.id}:{i}"
            
            # Prepare document
            doc = {
                "id": key,
                "parent_id": str(node.id),
                "parent_name": node.name,
                "content": chunk_text,
                "keywords": f"{node.name} {node.keywords if node.keywords else ''}",
                "subject_id": node.subject_id if node.subject_id else 0,
                "importance": node.importance_level,
                "vector": vector
            }
            
            # Redis JSON.SET
            pipeline.json().set(key, "$", doc)
            count += 1
            
            if count % 100 == 0:
                await pipeline.execute()
                pipeline = redis.pipeline()
                logger.info(f"🔄 Synced {count} chunks...")

    # Execute remaining
    if count % 100 != 0:
        await pipeline.execute()

    logger.success(f"✅ Sync complete! Total chunks indexed: {count}")
    await redis.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sync_data())
