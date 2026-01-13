import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.orchestration.orchestrator import ChatOrchestrator, STATE_DONE
from app.gen.agent.v1 import agent_service_pb2

@pytest.mark.asyncio
async def test_orchestrator_basic_flow():
    # Mock dependencies
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.incrby.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.eval.return_value = 1
    
    # Mock LLM Service stream
    mock_chunk = MagicMock()
    mock_chunk.type = "text"
    mock_chunk.content = "Hello, I am Sparkle AI."
    
    async def mock_stream(*args, **kwargs):
        yield mock_chunk

    with patch("app.agents.standard_workflow.llm_service") as mock_llm:
        mock_llm.chat_stream_with_tools = mock_stream
        mock_llm.chat_json = AsyncMock(return_value={})
        
        # Mock KnowledgeService
        with patch("app.agents.standard_workflow.KnowledgeService") as mock_ks_cls:
            mock_ks = mock_ks_cls.return_value
            mock_ks.retrieve_context = AsyncMock(return_value="Mocked Context")
            
            orchestrator = ChatOrchestrator(db_session=mock_db, redis_client=mock_redis)
            
            request = agent_service_pb2.ChatRequest(
                request_id="test_req",
                session_id="test_sess",
                user_id=str(uuid.uuid4()),
                message="Hi"
            )
            
            responses = []
            async for resp in orchestrator.process_stream(request):
                responses.append(resp)
            
            # Assertions
            assert len(responses) > 0
            # Check for thinking status
            assert any(r.HasField("status_update") and r.status_update.state == agent_service_pb2.AgentStatus.THINKING for r in responses)
            # Check for text delta
            assert any(r.delta == "Hello, I am Sparkle AI." for r in responses)
            # Check for finish
            assert any(r.finish_reason == agent_service_pb2.STOP for r in responses)
            
            print("\n✅ Orchestrator basic flow test passed!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_basic_flow())
