from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.standard_workflow import generation_node
from app.core.agent_profiles import TaskType
from app.orchestration.statechart_engine import WorkflowState


class _FakeGenerationLLM:
    def __init__(self):
        self.agent_role = "deep_analyst"

    def is_thinking_mode(self):
        return False

    def get_current_selection(self):
        return SimpleNamespace(config=SimpleNamespace(model_name="deep-analyst-model"))

    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="分析完成")


@pytest.mark.asyncio
async def test_generation_node_uses_role_and_task_scoped_llm(monkeypatch):
    fake_llm = _FakeGenerationLLM()
    get_llm_mock = AsyncMock(return_value=fake_llm)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{"role": "user", "content": "请深度分析这个问题"}],
        context_data={
            "chat_mode": "deep_analysis",
            "selected_experts": ["deep_analyst"],
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    get_llm_mock.assert_awaited_once_with("deep_analyst", TaskType.DEEP_REASONING)
    assert new_state.context_data["active_generation_agent_role"] == "deep_analyst"
    assert new_state.context_data["active_generation_model"] == "deep-analyst-model"
    assert new_state.messages[-1]["role"] == "assistant"
    assert new_state.messages[-1]["content"] == "分析完成"
