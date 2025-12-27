import asyncio
import sys
import os
import uuid
from loguru import logger
from typing import AsyncGenerator

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.orchestration.orchestrator import ChatOrchestrator
from app.gen.agent.v1 import agent_service_pb2
from app.db.session import AsyncSessionLocal
from app.services.llm_service import llm_service
from redis.asyncio import Redis
from app.config import settings

# Mock LLM Service stream
async def mock_chat_stream(*args, **kwargs):
    yield type('Chunk', (), {'type': 'text', 'content': 'Answer based on RAG.'})()

async def test_rag_flow():
    # Setup
    redis = Redis.from_url(settings.REDIS_URL, password=settings.REDIS_PASSWORD, decode_responses=True)
    
    # Mock LLM
    llm_service.chat_stream_with_tools = mock_chat_stream
    
    orchestrator = ChatOrchestrator(redis_client=redis)
    
    req_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4()) # Needs to be a valid UUID for UUID(user_id) conversion in code?
    # Actually Orchestrator converts to UUID, so string must be valid UUID format.
    
    request = agent_service_pb2.ChatRequest(
        request_id=req_id,
        session_id=session_id,
        user_id=user_id,
        message="CS101"
    )

    logger.info("🚀 Starting RAG Flow Test...")
    
    async with AsyncSessionLocal() as session:
        # Mock UserService if needed or ensure it handles missing user gracefully (it does fallback)
        async for response in orchestrator.process_stream(request, db_session=session):
            if response.HasField("status_update"):
                status = response.status_update
                logger.info(f"STATUS: {status.state} - {status.details}")
                if status.state == agent_service_pb2.AgentStatus.SEARCHING:
                     logger.info(f"✅ AGENT NAME: {status.current_agent_name}")
                     if status.current_agent_name == "SearchAgent":
                         logger.success("✅ SearchAgent Identified!")
            
            if response.HasField("citations"):
                citations = response.citations.citations
                logger.info(f"📚 Citations: {len(citations)}")
                for c in citations:
                    logger.info(f"   - [{c.score:.2f}] {c.title}: {c.content[:50]}...")
                if len(citations) > 0:
                    logger.success("✅ Citations received!")

    await redis.close()

if __name__ == "__main__":
    asyncio.run(test_rag_flow())
