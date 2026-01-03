import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.validator import ValidationResult
from app.services.llm_service import StreamChunk


async def _stub_router_node(state):
    state.context_data["router_decision"] = "generation"
    return state


@pytest.mark.asyncio
async def test_context_injection_includes_tasks_in_prompt():
    tasks = [
        {"title": "复习微积分笔记", "estimated_minutes": 30, "type": "study"},
        {"title": "练习英语听力", "estimated_minutes": 20, "type": "practice"},
        {"title": "完成10道物理题", "estimated_minutes": 40, "type": "practice"},
    ]

    user_context = {
        "user_context": {"nickname": "TestUser", "timezone": "Asia/Shanghai", "is_pro": False, "preferences": {}},
        "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
        "next_actions": tasks,
        "active_plans": [{"title": "期末冲刺计划", "type": "exam_prep", "progress": 0.2}],
        "focus_stats": {"total_minutes": 15, "pomodoro_count": 1},
    }

    async def mock_stream(system_prompt, user_message, tools):
        assert "复习微积分笔记" in system_prompt
        assert "练习英语听力" in system_prompt
        assert "完成10道物理题" in system_prompt
        yield StreamChunk(type="text", content="建议你先复习微积分和英语听力。")

    with patch("app.agents.standard_workflow.llm_service") as mock_llm, patch(
        "app.agents.standard_workflow.router_node", new=_stub_router_node
    ), patch.object(ChatOrchestrator, "_ensure_tools_registered", return_value=None):
        mock_llm.chat_stream_with_tools = mock_stream

        orchestrator = ChatOrchestrator(db_session=AsyncMock(), redis_client=AsyncMock())
        orchestrator._build_user_context = AsyncMock(return_value=user_context)
        orchestrator._build_conversation_context = AsyncMock(return_value={"messages": [], "summary": None})
        orchestrator._get_tools_schema = AsyncMock(return_value=[])
        orchestrator._check_idempotency = AsyncMock(return_value=None)
        orchestrator._acquire_session_lock = AsyncMock(return_value=True)
        orchestrator._release_session_lock = AsyncMock()
        orchestrator._cache_response = AsyncMock()
        orchestrator._update_state = AsyncMock()
        orchestrator.validator.validate_chat_request = AsyncMock(return_value=ValidationResult(True))

        request = agent_service_pb2.ChatRequest(
            request_id="req_1",
            session_id="sess_1",
            user_id=str(uuid.uuid4()),
            message="我现在该做什么？",
        )

        responses = [resp async for resp in orchestrator.process_stream(request)]
        delta_text = "".join([resp.delta for resp in responses if resp.delta])
        full_text = "".join([resp.full_text for resp in responses if resp.full_text]) or delta_text

        assert "微积分" in full_text or "英语" in full_text
