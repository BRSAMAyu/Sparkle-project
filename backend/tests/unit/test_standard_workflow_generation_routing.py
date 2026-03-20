from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.standard_workflow import (
    _classify_user_intent,
    _should_disable_tools_for_deep_analysis,
    _should_disable_tools_for_light_standard_reply,
    _should_use_slim_standard_context,
    _should_use_slim_deep_analysis_context,
    _sanitize_community_sendable_response,
    collaboration_post_process_node,
    generation_node,
    router_node,
)
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.orchestration.statechart_engine import WorkflowState


class _FakeGenerationLLM:
    def __init__(self):
        self.agent_role = "deep_analyst"

    def is_thinking_mode(self):
        return False

    def get_current_selection(self):
        return SimpleNamespace(
            model_key="dashscope_fast",
            is_fallback=False,
            estimated_cost_per_1k=0.0001,
            config=SimpleNamespace(
                model_name="deep-analyst-model",
                provider=SimpleNamespace(value="dashscope"),
                tier=SimpleNamespace(value="fast"),
            ),
        )

    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="分析完成")


class _ChunkedGenerationLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        for part in ["这是一段", "被拆成很多", "碎片的流式", "输出文本。"]:
            yield SimpleNamespace(type="text", content=part)


class _ToolLoopGenerationLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="我继续检查一下。")
        yield SimpleNamespace(
            type="tool_call_end",
            tool_call_id="tool-1",
            tool_name="get_plan_state",
            full_arguments={"plan_id": "current"},
        )


class _ToolCaptureGenerationLLM(_FakeGenerationLLM):
    def __init__(self):
        super().__init__()
        self.tools_seen = None

    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        self.tools_seen = tools
        yield SimpleNamespace(type="text", content="这是基于已查询计划整理出的最终执行建议。")


class _FailIfCalledLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        raise AssertionError("LLM should not be called for explicit recent-memory answers")


class _LowInfoLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="我来帮你查询CS101课程的相关信息。")


class _LowInfoPrivateAgentLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="我来帮你给阿泽写一条合适的私聊消息。")


class _LeadInGroupAgentLLM(_FakeGenerationLLM):
    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content="你可以这样发：\n大家今晚 8 点前同步一下各自的复习进度。")


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


@pytest.mark.asyncio
async def test_generation_node_forces_fast_tier_for_standard_chat(monkeypatch):
    fake_llm = _FakeGenerationLLM()
    get_tier_mock = AsyncMock(return_value=fake_llm)
    get_llm_mock = AsyncMock(side_effect=AssertionError("standard chat should use fast tier helper"))
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{"role": "user", "content": "帮我快速看一下这段话怎么优化"}],
        context_data={
            "chat_mode": "standard",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    get_tier_mock.assert_awaited_once_with(
        "generation",
        ModelTier.FAST,
        task_type=TaskType.STANDARD_RESPONSE,
    )
    assert new_state.context_data["first_touch_model_tier"] == ModelTier.FAST.value
    assert new_state.messages[-1]["content"] == "分析完成"


@pytest.mark.asyncio
async def test_generation_node_uses_custom_expert_specific_model(monkeypatch):
    fake_llm = _FakeGenerationLLM()
    get_specific_mock = AsyncMock(return_value=fake_llm)
    monkeypatch.setattr("app.agents.standard_workflow.get_llm_service_for_specific_model", get_specific_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    captured = {}

    async def _chat_stream(system_prompt, user_message, tools, user_context):
        captured["system_prompt"] = system_prompt
        yield SimpleNamespace(type="text", content="自定义专家分析完成")

    fake_llm.chat_stream_with_tools = _chat_stream

    state = WorkflowState(
        messages=[{"role": "user", "content": "帮我从反例角度分析这个问题"}],
        context_data={
            "chat_mode": "expert::custom_expert:test",
            "selected_experts": ["custom_expert:test"],
            "_custom_expert_profiles": {
                "custom_expert:test": {
                    "display_name": "批判专家",
                    "system_prompt": "必须补充两个反例。",
                    "base_expert_id": "deep_analyst",
                    "preferred_model_key": "mimo_pro",
                    "reasoning_mode": "deep",
                }
            },
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    get_specific_mock.assert_awaited_once_with("mimo_pro", AgentRole.DEEP_ANALYST)
    assert "必须补充两个反例" in captured["system_prompt"]
    assert new_state.messages[-1]["content"] == "自定义专家分析完成"


@pytest.mark.asyncio
async def test_router_node_forces_collaboration_for_explicit_team():
    state = WorkflowState(
        messages=[{"role": "user", "content": "给我一个综合方案"}],
        context_data={
            "chat_mode": 'team::{"agents":["deep_analyst","custom_expert:test"],"final_agents":["custom_expert:test"]}',
            "selected_experts": ["deep_analyst", "custom_expert:test"],
            "answer_experts": ["custom_expert:test"],
        },
    )

    routed = await router_node(state)

    assert routed.context_data["router_decision"] == "collaboration"
    assert routed.context_data["router_confidence"] == 1.0


@pytest.mark.asyncio
async def test_collaboration_post_process_ends_explicit_team_after_final_response():
    state = WorkflowState(
        messages=[{"role": "user", "content": "给我一个综合方案"}],
        context_data={
            "chat_mode": 'team::{"agents":["deep_analyst","time_tutor"],"final_agents":["deep_analyst"]}',
            "selected_experts": ["deep_analyst", "time_tutor"],
            "answer_experts": ["deep_analyst"],
            "collaboration_result": SimpleNamespace(final_response="这里是团队综合后的最终答案。", outputs=[]),
        },
    )

    updated = await collaboration_post_process_node(state)

    assert updated.next_step == "__end__"
    assert updated.messages[-1]["role"] == "assistant"
    assert updated.messages[-1]["content"] == "这里是团队综合后的最终答案。"


@pytest.mark.asyncio
async def test_collaboration_post_process_falls_back_to_tool_planning_without_explicit_team():
    state = WorkflowState(
        messages=[{"role": "user", "content": "继续"}],
        context_data={
            "chat_mode": "standard",
            "collaboration_result": SimpleNamespace(final_response="中间协作结果", outputs=[]),
        },
    )

    updated = await collaboration_post_process_node(state)

    assert updated.next_step == "tool_planning"


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


def test_light_standard_followup_disables_tools():
    state = WorkflowState(
        messages=[
            {"role": "user", "content": "番茄钟学习法是什么？"},
            {"role": "assistant", "content": "它是一种专注学习法。"},
            {"role": "user", "content": "基于刚才的解释，再给我一个今天就能执行的 25 分钟开始动作。"},
        ],
        context_data={
            "chat_mode": "standard",
            "tools_schema": [{"name": "get_plan_state"}],
        },
    )

    assert _should_disable_tools_for_light_standard_reply(
        state,
        "基于刚才的解释，再给我一个今天就能执行的 25 分钟开始动作。",
    ) is True


def test_deep_analysis_disables_tools_by_default():
    state = WorkflowState(
        messages=[{"role": "user", "content": "请深入分析栈和队列的区别。"}],
        context_data={
            "chat_mode": "deep_analysis",
            "tools_schema": [{"name": "web_search_pro"}],
        },
    )

    assert _should_disable_tools_for_deep_analysis(state) is True


def test_standard_knowledge_question_disables_tools():
    state = WorkflowState(
        messages=[{"role": "user", "content": "番茄钟学习法是什么？"}],
        context_data={
            "chat_mode": "standard",
        },
    )

    assert _should_disable_tools_for_light_standard_reply(state, "番茄钟学习法是什么？") is True


def test_standard_review_request_disables_tools_even_without_explicit_knowledge_keyword():
    state = WorkflowState(
        messages=[{"role": "user", "content": "我想快速复习一下 Python 列表推导式，给我一个 5 分钟版本。"}],
        context_data={
            "chat_mode": "standard",
        },
    )

    assert _should_disable_tools_for_light_standard_reply(
        state,
        "我想快速复习一下 Python 列表推导式，给我一个 5 分钟版本。",
    ) is True


def test_standard_personal_plan_request_keeps_tools_enabled():
    state = WorkflowState(
        messages=[{"role": "user", "content": "结合我的计划和任务，告诉我今天该先做什么。"}],
        context_data={
            "chat_mode": "standard",
        },
    )

    assert _should_disable_tools_for_light_standard_reply(
        state,
        "结合我的计划和任务，告诉我今天该先做什么。",
    ) is False


def test_standard_knowledge_question_uses_slim_context():
    state = WorkflowState(
        messages=[{"role": "user", "content": "请用三条简洁要点告诉我番茄钟学习法是什么。"}],
        context_data={
            "chat_mode": "standard",
        },
    )

    assert _should_use_slim_standard_context(
        state,
        "请用三条简洁要点告诉我番茄钟学习法是什么。",
    ) is True


def test_generic_deep_analysis_uses_slim_context():
    state = WorkflowState(
        messages=[{"role": "user", "content": "请深度分析栈和队列的区别"}],
        context_data={
            "chat_mode": "deep_analysis",
        },
    )

    assert _should_use_slim_deep_analysis_context(state, "请深度分析栈和队列的区别") is True


def test_personalized_deep_analysis_keeps_full_context():
    state = WorkflowState(
        messages=[{"role": "user", "content": "结合我的任务和计划，深度分析我为什么总拖延"}],
        context_data={
            "chat_mode": "deep_analysis",
        },
    )

    assert _should_use_slim_deep_analysis_context(state, "结合我的任务和计划，深度分析我为什么总拖延") is False


@pytest.mark.asyncio
async def test_generation_node_batches_stream_deltas(monkeypatch):
    fake_llm = _ChunkedGenerationLLM()
    get_llm_mock = AsyncMock(return_value=fake_llm)
    stream_callback = AsyncMock()
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
            "stream_callback": stream_callback,
        },
    )

    new_state = await generation_node(state)

    assert stream_callback.await_count == 1
    assert new_state.messages[-1]["content"] == "这是一段被拆成很多碎片的流式输出文本。"


@pytest.mark.asyncio
async def test_generation_node_stops_after_tool_loop_cap(monkeypatch):
    fake_llm = _ToolLoopGenerationLLM()
    get_llm_mock = AsyncMock(return_value=fake_llm)
    get_tier_mock = AsyncMock(return_value=fake_llm)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{"role": "user", "content": "继续处理这个计划"}],
        context_data={
            "chat_mode": "study_plan",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [{"name": "get_plan_state"}],
            "tool_loop_count": 2,
        },
    )

    new_state = await generation_node(state)

    assert new_state.next_step == "__end__"
    assert new_state.context_data.get("tool_calls", []) == []


@pytest.mark.asyncio
async def test_generation_node_disables_tools_for_final_study_plan_synthesis(monkeypatch):
    fake_llm = _ToolCaptureGenerationLLM()
    get_llm_mock = AsyncMock(return_value=fake_llm)
    get_tier_mock = AsyncMock(return_value=fake_llm)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{"role": "user", "content": "结合我现有计划，给我一份 7 天 Python 学习拆解。"}],
        context_data={
            "chat_mode": "study_plan",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [{"name": "get_plan_state"}, {"name": "get_task_summary"}],
            "tool_loop_count": 1,
        },
    )

    new_state = await generation_node(state)

    assert fake_llm.tools_seen == []
    assert new_state.next_step == "__end__"
    assert new_state.messages[-1]["content"] == "这是基于已查询计划整理出的最终执行建议。"


@pytest.mark.asyncio
async def test_generation_node_answers_recent_memory_question_without_llm(monkeypatch):
    get_llm_mock = AsyncMock(return_value=_FailIfCalledLLM())
    get_tier_mock = AsyncMock(return_value=_FailIfCalledLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
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
    get_llm_mock.assert_not_awaited()
    get_tier_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_generation_node_replaces_low_information_reply_with_retrieval_fact(monkeypatch):
    get_llm_mock = AsyncMock(return_value=_LowInfoLLM())
    get_tier_mock = AsyncMock(return_value=_LowInfoLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
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
    get_tier_mock = AsyncMock(return_value=_LowInfoPrivateAgentLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
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


def test_sanitize_community_sendable_response_removes_explanatory_lead_in():
    user_message = (
        "你是Sparkle内置的群聊AI助手，正在协助群聊「高数冲刺群」。\n"
        "用户问题:\n帮我在群里发一条提醒，今晚 8 点前同步复习进度。"
    )

    sanitized = _sanitize_community_sendable_response(
        user_message,
        "你可以这样发：\n“大家今晚 8 点前同步一下各自的复习进度。”",
    )

    assert sanitized == "大家今晚 8 点前同步一下各自的复习进度。"


@pytest.mark.asyncio
async def test_generation_node_sanitizes_group_reply_lead_in(monkeypatch):
    get_llm_mock = AsyncMock(return_value=_LeadInGroupAgentLLM())
    get_tier_mock = AsyncMock(return_value=_LeadInGroupAgentLLM())
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    state = WorkflowState(
        messages=[{
            "role": "user",
            "content": (
                "你是Sparkle内置的群聊AI助手，正在协助群聊「高数冲刺群」。\n"
                "最近对话:\n"
                "小林: 我今天晚上复盘错题。\n\n"
                "用户问题:\n"
                "帮我在群里发一条提醒，今晚 8 点前同步复习进度。"
            ),
        }],
        context_data={
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
        },
    )

    new_state = await generation_node(state)

    assert new_state.messages[-1]["content"] == "大家今晚 8 点前同步一下各自的复习进度。"
