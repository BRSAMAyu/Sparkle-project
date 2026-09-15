import asyncio
import os
import sys

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select

from app.config import settings
from app.core.redis_utils import resolve_redis_password
from app.db.session import AsyncSessionLocal
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode
from app.services.embedding_service import embedding_service
from app.services.rag_indexing_service import (
    build_document_chunk_document,
    build_knowledge_chunk_document,
    index_rag_documents,
    vector_to_list,
)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


async def _sync_knowledge_nodes(session, redis, text_splitter) -> int:
    logger.info("📦 Fetching KnowledgeNodes from DB...")
    stmt = select(KnowledgeNode).where(KnowledgeNode.description.isnot(None))
    result = await session.execute(stmt)
    nodes = result.scalars().all()
    logger.info(f"📊 Found {len(nodes)} nodes with descriptions.")

    count = 0
    docs = []
    for node in nodes:
        if not node.description:
            continue

        chunks = text_splitter.split_text(node.description)
        if not chunks:
            continue

        try:
            embeddings = await embedding_service.batch_embeddings(chunks, text_type="document")
            if len(embeddings) != len(chunks):
                raise RuntimeError(f"expected {len(chunks)} embeddings, got {len(embeddings)}")
        except Exception as e:
            logger.error(f"⚠️ Failed to embed node {node.id}; indexing text without vectors: {e}")
            embeddings = [None] * len(chunks)

        for i, (chunk_text, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            docs.append(build_knowledge_chunk_document(node, chunk_text, vector, i, settings.EMBEDDING_DIM))
            count += 1

            if len(docs) >= 100:
                await index_rag_documents(redis, docs)
                docs = []
                logger.info(f"🔄 Synced {count} KnowledgeNode chunks...")

    if docs:
        await index_rag_documents(redis, docs)

    return count


async def _backfill_missing_document_chunk_embeddings(session, rows) -> int:
    missing = [
        chunk for chunk, _file_record in rows
        if chunk.content and _needs_embedding_backfill(chunk.embedding)
    ]
    if not missing:
        return 0

    logger.info(f"🧩 Backfilling embeddings for {len(missing)} DocumentChunks...")
    updated = 0
    batch_size = 16
    for index in range(0, len(missing), batch_size):
        batch = missing[index:index + batch_size]
        texts = [chunk.content for chunk in batch]
        try:
            embeddings = await embedding_service.batch_embeddings(texts, text_type="document")
            if len(embeddings) != len(batch):
                raise RuntimeError(f"expected {len(batch)} embeddings, got {len(embeddings)}")
        except Exception as e:
            logger.error(f"⚠️ Failed to backfill DocumentChunk embeddings; indexing text without vectors: {e}")
            continue

        for chunk, embedding in zip(batch, embeddings, strict=True):
            chunk.embedding = embedding
            updated += 1

        await session.commit()

    return updated


def _needs_embedding_backfill(embedding) -> bool:
    vector = vector_to_list(embedding)
    return vector is None or len(vector) != settings.EMBEDDING_DIM


async def _sync_document_chunks(session, redis) -> int:
    logger.info("📄 Fetching DocumentChunks from DB...")
    stmt = (
        select(DocumentChunk, StoredFile)
        .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
        .where(DocumentChunk.content.isnot(None))
        .order_by(DocumentChunk.file_id, DocumentChunk.chunk_index)
    )
    result = await session.execute(stmt)
    rows = result.all()
    logger.info(f"📊 Found {len(rows)} document chunks.")

    updated = await _backfill_missing_document_chunk_embeddings(session, rows)
    if updated:
        logger.info(f"✅ Backfilled {updated} DocumentChunk embeddings.")

    docs = []
    count = 0
    for chunk, file_record in rows:
        if not chunk.content:
            continue
        docs.append(build_document_chunk_document(chunk, file_record, settings.EMBEDDING_DIM))
        count += 1
        if len(docs) >= 100:
            await index_rag_documents(redis, docs)
            docs = []
            logger.info(f"🔄 Synced {count} DocumentChunks...")

    if docs:
        await index_rag_documents(redis, docs)

    return count


async def sync_data():
    """Sync KnowledgeNodes and DocumentChunks from Postgres to Redis."""
    logger.info("🚀 Starting PG -> Redis Sync...")

    # 1. Connect to Redis
    resolved_password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
    redis = Redis.from_url(
        settings.REDIS_URL,
        username='default',
        password=resolved_password,
        decode_responses=True,
    )
    try:
        await redis.ping()
        logger.info("✅ Redis connected.")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400, # Approx 100-200 tokens
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", ".", " ", ""]
    )

    async with AsyncSessionLocal() as session:
        node_count = await _sync_knowledge_nodes(session, redis, text_splitter)
        document_count = await _sync_document_chunks(session, redis)

    total = node_count + document_count
    logger.success(
        f"✅ Sync complete! KnowledgeNode chunks: {node_count}, "
        f"DocumentChunks: {document_count}, total indexed: {total}"
    )
    if hasattr(redis, "aclose"):
        await redis.aclose()
    else:
        await redis.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sync_data())
