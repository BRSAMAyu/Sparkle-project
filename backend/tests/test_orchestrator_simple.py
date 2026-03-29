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
    mock_redis.ping.return_value = True

    # Mock LLM Service stream
    mock_chunk = MagicMock()
    mock_chunk.type = "text"
    mock_chunk.content = "Hello, I am Sparkle AI."

    async def mock_stream(*args, **kwargs):
        yield mock_chunk

    # Patch must be applied before creating orchestrator
    with patch("app.services.llm_service.llm_service.chat_stream_with_tools", mock_stream):
        with patch("app.services.llm_service.llm_service.chat_json", AsyncMock(return_value={})):
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
                # Check for text output (schema may use delta/full_text depending on path)
                assert any((getattr(r, "delta", "") or getattr(r, "full_text", "")) for r in responses)
                # Check for finish
                assert any(r.finish_reason == agent_service_pb2.STOP for r in responses)

                print("\n✅ Orchestrator basic flow test passed!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_basic_flow())


@pytest.mark.asyncio
async def test_bridge_short_circuit_skips_session_start_updates():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.incrby.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.eval.return_value = 1
    mock_redis.ping.return_value = True

    orchestrator = ChatOrchestrator(db_session=mock_db, redis_client=mock_redis)
    orchestrator._validate_request = AsyncMock(return_value=None)
    orchestrator._check_idempotency_response = AsyncMock(return_value=None)
    orchestrator._acquire_session_lock = AsyncMock(return_value=True)
    orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))
    orchestrator._update_state = AsyncMock()
    orchestrator._build_full_context = AsyncMock(
        side_effect=AssertionError("bridge short circuit should bypass context building")
    )
    orchestrator._resolve_active_tools = MagicMock(return_value=["run_quick_simulation"])
    orchestrator._maybe_short_circuit_bridge_tool = AsyncMock(
        return_value=[
            agent_service_pb2.ChatResponse(
                full_text="仿真预览已准备好",
                finish_reason=agent_service_pb2.STOP,
            )
        ]
    )
    orchestrator._maybe_enqueue_perceptible_insight = AsyncMock(
        side_effect=AssertionError("bridge short circuit should bypass perceptible insight updates")
    )
    orchestrator._maybe_enqueue_understanding_depth = AsyncMock(
        side_effect=AssertionError("bridge short circuit should bypass understanding depth updates")
    )
    orchestrator._drain_system_updates = AsyncMock(
        side_effect=AssertionError("bridge short circuit should bypass session start system updates")
    )
    orchestrator._cleanup = AsyncMock()

    request = agent_service_pb2.ChatRequest(
        request_id="bridge_req",
        session_id="bridge_session",
        user_id=str(uuid.uuid4()),
        message="我想模拟一下学习场景",
    )

    responses = []
    async for resp in orchestrator.process_stream(request):
        responses.append(resp)

    assert any(resp.full_text == "仿真预览已准备好" for resp in responses)
    orchestrator._maybe_short_circuit_bridge_tool.assert_awaited_once()
    orchestrator._build_full_context.assert_not_awaited()
    orchestrator._maybe_enqueue_perceptible_insight.assert_not_awaited()
    orchestrator._maybe_enqueue_understanding_depth.assert_not_awaited()
    orchestrator._drain_system_updates.assert_not_awaited()
