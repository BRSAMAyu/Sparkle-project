from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.standard_workflow import _classify_user_intent, generation_node
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


class _FailIfCalledLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        raise AssertionError("LLM should not be called for explicit recent-memory answers")


class _LowInfoLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="我来帮你查询CS101课程的相关信息。")


class _LowInfoPrivateAgentLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="我来帮你给阿泽写一条合适的私聊消息。")


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


def test_exam_fact_query_does_not_trigger_exam_preparation():
    intent = _classify_user_intent("CS101课程期末考试占比多少？")
    assert intent is None

    planning_intent = _classify_user_intent("我下周要准备期末考试，帮我做复习计划")
    assert planning_intent == "exam_preparation"

    community_prompt_intent = _classify_user_intent(
        "你是Sparkle内置的私聊AI助手，正在协助我与「阿泽」的对话。\n\n用户问题:\n"
        "帮我给阿泽写一条简短、自然、可直接发送的私聊回复，约今晚一起过一下 CS101 期末考点。"
    )
    assert community_prompt_intent is None


@pytest.mark.asyncio
async def test_generation_node_answers_recent_memory_question_without_llm(monkeypatch):
    get_llm_mock = AsyncMock(return_value=_FailIfCalledLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[
            {"role": "user", "content": "记住我的代号是海王星，只回复“已记住”。"},
            {"role": "assistant", "content": "已记住"},
            {"role": "user", "content": "我的代号是什么？只回复代号本身。"},
        ],
        context_data={
            "user_context": {},
            "conversation_context": {
                "messages": [
                    {"role": "user", "content": "记住我的代号是海王星，只回复“已记住”。"},
                    {"role": "assistant", "content": "已记住"},
                ]
            },
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    assert new_state.context_data["generation_shortcut"] == "recent_memory"
    assert new_state.messages[-1]["content"] == "海王星"
    get_llm_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_node_replaces_low_information_reply_with_retrieval_fact(monkeypatch):
    get_llm_mock = AsyncMock(return_value=_LowInfoLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{"role": "user", "content": "CS101课程期末考试占比多少？"}],
        context_data={
            "user_context": {},
            "conversation_context": {"messages": []},
            "knowledge_context": (
                "Relevant Knowledge Base (Graph Augmented):\n"
                "- [CS101 课程说明]: CS101 课程是计算机科学入门。期末考试占比 40%，期中考试 20%，平时作业 40%。"
            ),
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    assert "40%" in new_state.messages[-1]["content"]
    assert "我来帮你查询" not in new_state.messages[-1]["content"]


@pytest.mark.asyncio
async def test_generation_node_replaces_low_information_private_agent_reply(monkeypatch):
    get_llm_mock = AsyncMock(return_value=_LowInfoPrivateAgentLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{
            "role": "user",
            "content": (
                "你是Sparkle内置的私聊AI助手，正在协助我与「阿泽」的对话。\n"
                "请给出简洁、有礼貌、可直接发送的回复建议，避免过度输出。\n\n"
                "最近对话:\n"
                "我: 最近在复习期末内容。\n\n"
                "用户问题:\n"
                "帮我给阿泽写一条简短、自然、可直接发送的私聊回复，约今晚一起过一下 CS101 期末考点。"
            ),
        }],
        context_data={
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    assert "我来帮你给阿泽写一条" not in new_state.messages[-1]["content"]
    assert "阿泽" in new_state.messages[-1]["content"]
    assert "CS101" in new_state.messages[-1]["content"]
