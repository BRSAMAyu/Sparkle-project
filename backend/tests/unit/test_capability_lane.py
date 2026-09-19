"""E-02 能力路由（Fast Semantic / Deliberate Decision）单元测试。

背景（E-01 ROUTING_MAP C1-探针已定位，2026-09-19）：
- 记忆指令/检索问答级消息长期落 plus+balanced 的判据破点 =
  `_should_use_slim_standard_context` 被 retrieval_decision.should_retrieve=True
  一票否决；而记忆类消息会被 retrieval_intent 分类器误判为
  ambiguous("帮我")/knowledge("是什么") → graph_only/targeted_source_rag。
- 保护约束：exam_preparation 工具流（planned_tool_sequence）不得被降级。
"""

from __future__ import annotations

import pytest

from app.agents.standard_workflow import (
    _should_force_balanced_fast_first_touch,
    _should_use_slim_standard_context,
)
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import llm_router
from app.orchestration.capability_lane import (
    ChatCapabilityLane,
    classify_memory_class_message,
    record_capability_lane_decision,
    resolve_capability_lane,
)
from app.orchestration.retrieval_intent import build_retrieval_decision
from app.orchestration.statechart_engine import WorkflowState


def _state(message: str, context_data: dict | None = None) -> WorkflowState:
    return WorkflowState(
        messages=[{"role": "user", "content": message}],
        context_data={"chat_mode": "standard", **(context_data or {})},
    )


# ============================================
# 1. 记忆类消息分类
# ============================================


@pytest.mark.parametrize(
    "message,expected",
    [
        ("请记住：我的期中考试范围是第 1 到第 6 章，第 7 章不考。", "memory_instruction"),
        ("我最喜欢的电影是《星际穿越》，帮我记住这个", "memory_instruction"),
        ("记住我的学号是 20250101", "memory_instruction"),
        ("别忘了周四下午我要开组会", "memory_instruction"),
        ("记一下我 preferred 的复习方式是刷题", "memory_instruction"),
        ("我喜欢的电影是什么？", "memory_retrieval_query"),
        ("我最喜欢的电影是什么来着？", "memory_retrieval_query"),
        ("我说过我周末一般几点起床？", "memory_retrieval_query"),
        ("我的学号是多少？", "memory_retrieval_query"),
    ],
)
def test_memory_class_detection(message, expected):
    assert classify_memory_class_message(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "帮我制定期末考试复习计划",  # planning：planned_tool_sequence 流
        "我为什么总是拖延",  # 自我分析（为什么）→ deliberate
        "详细讲讲我的知识星图",  # deep marker
        "解释一下量子隧穿效应",  # 通用知识问答（非第一人称记忆）
        "你好",  # 问候（属 emotional/social，不属记忆类）
        "帮我建一个复习任务",  # 显式工具动作
        "根据我的计划分析一下进度",  # 个人数据工具意图
    ],
)
def test_non_memory_messages_not_classified(message):
    assert classify_memory_class_message(message) is None


# ============================================
# 2. 检索意图分类器根修：记忆类轮次不做文档/知识星图检索
# ============================================


def test_memory_instruction_no_retrieval():
    decision = build_retrieval_decision(
        message="我最喜欢的电影是《星际穿越》，帮我记住这个", route_intent=None, context={}
    )
    assert decision.should_retrieve is False
    assert decision.reason == "memory_class_turn"


def test_memory_retrieval_query_no_retrieval():
    decision = build_retrieval_decision(message="我喜欢的电影是什么？", route_intent=None, context={})
    assert decision.should_retrieve is False
    assert decision.reason == "memory_class_turn"


def test_memory_instruction_plain_statement_stays_no_retrieval():
    decision = build_retrieval_decision(
        message="请记住：我的期中考试范围是第 1 到第 6 章，第 7 章不考。", route_intent=None, context={}
    )
    assert decision.should_retrieve is False


def test_planning_message_keeps_graph_retrieval():
    """规划类消息（graph_only）必须保持检索——不得被记忆类误伤。"""
    decision = build_retrieval_decision(message="帮我制定考研复习计划", route_intent=None, context={})
    assert decision.should_retrieve is True
    assert decision.retrieval_mode == "graph_only"


def test_knowledge_question_keeps_rag():
    decision = build_retrieval_decision(message="解释一下量子隧穿效应", route_intent=None, context={})
    assert decision.should_retrieve is True
    assert decision.retrieval_mode == "targeted_source_rag"


def test_document_request_with_memory_words_not_hijacked():
    """记忆词 + 明确文档诉求 → 不得被记忆类早退劫持（能力保留优先）。"""
    message = "记住这份资料里第三章的结论"
    assert classify_memory_class_message(message) is None
    decision = build_retrieval_decision(message=message, route_intent=None, context={})
    assert decision.reason != "memory_class_turn"


# ============================================
# 2.5 R2-F1：方法建议问法不得劫持进记忆车道（基线行为保持）
# 「怎么/如何记住…」「有什么记住…的方法」是学习产品核心高频问法，
# 语义是求方法（文档接地/deliberate），不是写记忆。
# ============================================


@pytest.mark.parametrize(
    "message",
    [
        "怎么记住英语单词更有效率？",
        "如何记住复杂的化学公式？",
        "有什么记住历史年代的好方法",
        "我记住了老师讲的重点，接下来该做什么",
    ],
)
def test_method_advice_questions_not_memory_class(message):
    assert classify_memory_class_message(message) is None


def test_method_advice_question_keeps_document_grounding():
    """R2-F1 红测：基线（HEAD）对「怎么记住…」走 targeted_source_rag 文档接地，
    不得被 memory_class_turn 劫持为 no_retrieval + 误导 receipt + 快答档。"""
    decision = build_retrieval_decision(message="怎么记住英语单词更有效率？", route_intent=None, context={})
    assert decision.should_retrieve is True
    assert decision.retrieval_mode == "targeted_source_rag"
    assert decision.reason != "memory_class_turn"


def test_method_advice_question_lands_deliberate_lane():
    lane = resolve_capability_lane(
        user_message="怎么记住英语单词更有效率？",
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": True, "retrieval_mode": "targeted_source_rag"},
    )
    assert lane.lane is ChatCapabilityLane.DELIBERATE
    assert lane.memory_class is None


def test_past_tense_statement_not_memory_instruction():
    """「我记住了…」完成时陈述（非写入指令）不得触发记忆写入 receipt。"""
    message = "我记住了老师讲的重点，接下来该做什么"
    assert classify_memory_class_message(message) is None
    decision = build_retrieval_decision(message=message, route_intent=None, context={})
    assert decision.reason != "memory_class_turn"


# ============================================
# 2.6 R2-F1b：第三方事实疑问不得进记忆检索车道
# 「我们…」（团体事实）与「老师问我…」（转述问答）记忆系统无此数据，
# 误判会造成答案质量降级。
# ============================================


@pytest.mark.parametrize(
    "message",
    [
        "我们小组定的汇报主题是什么来着",
        "老师问我这道题的答案是什么",
    ],
)
def test_third_party_facts_not_memory_query(message):
    assert classify_memory_class_message(message) is None


# ============================================
# 3. slim 判据：graph_only 不再一票否决记忆类；文档/规划仍否决
# ============================================


def _graph_only_decision() -> dict:
    return {"should_retrieve": True, "retrieval_mode": "graph_only", "reason": "ambiguous_query_graph_only"}


def _targeted_rag_decision() -> dict:
    return {
        "should_retrieve": True,
        "retrieval_mode": "targeted_source_rag",
        "reason": "knowledge_query_targeted_rag",
    }


def test_memory_instruction_with_graph_only_decision_uses_slim():
    """E-01 W-1 破点红测：live 管线给记忆指令挂 graph_only 决策后 slim 必须放行。"""
    state = _state(
        "我最喜欢的电影是《星际穿越》，帮我记住这个",
        {"retrieval_decision": _graph_only_decision(), "document_retrieval_decision": _graph_only_decision()},
    )
    assert _should_use_slim_standard_context(state, "我最喜欢的电影是《星际穿越》，帮我记住这个") is True


def test_memory_query_with_graph_only_decision_uses_slim():
    message = "我喜欢的电影是什么？"
    state = _state(
        message,
        {"retrieval_decision": _graph_only_decision(), "document_retrieval_decision": _graph_only_decision()},
    )
    assert _should_use_slim_standard_context(state, message) is True


def test_targeted_rag_still_vetoes_slim():
    """文档级检索（targeted_source_rag）仍然否决 slim——文档接地需要完整上下文。"""
    message = "我喜欢的电影是什么？"
    state = _state(
        message,
        {"retrieval_decision": _targeted_rag_decision(), "document_retrieval_decision": _targeted_rag_decision()},
    )
    assert _should_use_slim_standard_context(state, message) is False


def test_non_memory_graph_only_still_vetoes_slim():
    """非记忆类 graph_only（规划/模糊）仍否决 slim。"""
    message = "帮我规划一下这学期的高数复习"
    state = _state(
        message,
        {"retrieval_decision": _graph_only_decision(), "document_retrieval_decision": _graph_only_decision()},
    )
    assert _should_use_slim_standard_context(state, message) is False


def test_memory_instruction_with_planned_tool_sequence_stays_full():
    """exam_preparation 保护：工具序列在场 → 永不走 slim/fast。"""
    message = "请记住我的考试范围，然后帮我制定冲刺计划"
    state = _state(
        message,
        {
            "retrieval_decision": _graph_only_decision(),
            "planned_tool_sequence": [{"tool": "get_plan_state"}],
        },
    )
    assert _should_use_slim_standard_context(state, message) is False


def test_memory_instruction_forces_balanced_fast_tier():
    """slim 放行后，balanced fast path 判据必须命中（FAST 层强制）。"""
    message = "我最喜欢的电影是《星际穿越》，帮我记住这个"
    state = _state(
        message,
        {
            "retrieval_decision": _graph_only_decision(),
            "document_retrieval_decision": _graph_only_decision(),
        },
    )
    assert (
        _should_force_balanced_fast_first_touch(
            state,
            explicit_runtime=None,
            task_type=TaskType.STANDARD_RESPONSE,
            user_message=message,
            use_slim_standard_context=_should_use_slim_standard_context(state, message),
        )
        is True
    )


# ============================================
# 4. 能力 lane 判定（capability_lane 模块）
# ============================================


def test_lane_fast_for_memory_instruction():
    decision = resolve_capability_lane(
        user_message="我最喜欢的电影是《星际穿越》，帮我记住这个",
        context_data={"chat_mode": "standard"},
        retrieval_decision=_graph_only_decision(),
    )
    assert decision.lane is ChatCapabilityLane.FAST
    assert decision.memory_class == "memory_instruction"
    assert "memory_instruction_fast_lane" in decision.reasons
    assert decision.tool_flow_protected is False


def test_lane_deliberate_for_exam_tool_flow():
    """exam_preparation 工具流保护：即使文本命中记忆类，工具序列优先。"""
    decision = resolve_capability_lane(
        user_message="请记住我的考试范围，然后帮我制定冲刺计划",
        context_data={
            "chat_mode": "standard",
            "planned_tool_sequence": [{"tool": "create_plan"}],
        },
        retrieval_decision=_graph_only_decision(),
    )
    assert decision.lane is ChatCapabilityLane.DELIBERATE
    assert decision.tool_flow_protected is True
    assert "tool_flow_protected" in decision.reasons


def test_lane_deliberate_for_document_retrieval():
    decision = resolve_capability_lane(
        user_message="根据我上传的资料总结第三章",
        context_data={"chat_mode": "standard"},
        retrieval_decision=_targeted_rag_decision(),
    )
    assert decision.lane is ChatCapabilityLane.DELIBERATE
    assert "document_retrieval" in decision.reasons


def test_lane_deliberate_for_deep_analysis_mode():
    decision = resolve_capability_lane(
        user_message="深入分析我的学习模式",
        context_data={"chat_mode": "deep_analysis"},
        retrieval_decision=None,
    )
    assert decision.lane is ChatCapabilityLane.DELIBERATE


def test_lane_fast_for_plain_light_reply():
    decision = resolve_capability_lane(
        user_message="什么是番茄钟学习法",
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": False, "retrieval_mode": "no_retrieval"},
    )
    assert decision.lane is ChatCapabilityLane.FAST


def test_lane_deliberate_for_deep_marker_text_without_retrieval():
    """深度词消息（无检索需求、短文本）实际 tier 走默认链——balanced fast path 被
    deep 标记否决，lane 必须如实报 deliberate，否则遥测把 deliberate 轮误计为 fast。"""
    decision = resolve_capability_lane(
        user_message="深入分析我的学习模式",
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": False, "retrieval_mode": "no_retrieval"},
    )
    assert decision.lane is ChatCapabilityLane.DELIBERATE
    assert decision.trigger == "deep_marker_text"
    # 交叉验证：实际 tier 判据（balanced fast path）同样因深度词否决
    state = _state(
        "深入分析我的学习模式",
        {"retrieval_decision": {"should_retrieve": False, "retrieval_mode": "no_retrieval"}},
    )
    assert (
        _should_force_balanced_fast_first_touch(
            state,
            explicit_runtime=None,
            task_type=TaskType.STANDARD_RESPONSE,
            user_message="深入分析我的学习模式",
            use_slim_standard_context=True,
        )
        is False
    )


# ============================================
# 4.5 R2-F2：lane=fast 虚高两形态（与实际 tier 判据同源闭合）
# ============================================


def test_lane_deliberate_for_overlength_memory_instruction():
    """R2-F2A：121–200 字记忆指令——classify（≤200）仍是记忆类（根修 no_retrieval
    保留），但 balanced fast path 上限 120 字 → 实际默认链，lane 必须报 deliberate。"""
    long_instruction = (
        "请记住：我的 MBTI 测出来是 INTJ，家乡在浙江温州，高中最喜欢的科目是物理，"
        "现在用的笔记本电脑是十四寸的，宿舍晚上十一点断电，我习惯早上七点二十起床，"
        "午饭经常在二食堂解决，最爱吃的菜是糖醋排骨，对芒果和虾过敏，体育课选了羽毛球，"
        "周末喜欢睡到自然醒"
    )
    assert 120 < len(long_instruction) <= 200
    assert classify_memory_class_message(long_instruction) == "memory_instruction"
    decision = build_retrieval_decision(message=long_instruction, route_intent=None, context={})
    assert decision.reason == "memory_class_turn"  # 根修行为不受 lane 收紧影响
    lane = resolve_capability_lane(
        user_message=long_instruction,
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": False, "retrieval_mode": "no_retrieval"},
    )
    assert lane.lane is ChatCapabilityLane.DELIBERATE
    # 交叉验证：实际 tier 判据同样因 >120 字不进 balanced fast path
    state = _state(
        long_instruction,
        {"retrieval_decision": {"should_retrieve": False, "retrieval_mode": "no_retrieval"}},
    )
    assert (
        _should_force_balanced_fast_first_touch(
            state,
            explicit_runtime=None,
            task_type=TaskType.STANDARD_RESPONSE,
            user_message=long_instruction,
            use_slim_standard_context=True,
        )
        is False
    )


@pytest.mark.parametrize(
    "message",
    [
        "聊聊我的进度吧",
        "看看我的知识星图",
        "根据我的情况给点建议",
        "查一下我的错题",
        "我的画像准不准",
    ],
)
def test_lane_deliberate_for_personal_data_intents(message):
    """R2-F2B：个人数据/工具意图词轮次——slim 被 light-reply 判据否决 → 实际
    默认链，lane 必须报 deliberate（否则 D-06 L1 占比被系统性高估）。"""
    lane = resolve_capability_lane(
        user_message=message,
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": False, "retrieval_mode": "no_retrieval"},
    )
    assert lane.lane is ChatCapabilityLane.DELIBERATE
    assert lane.trigger == "personal_data_or_tool_intent"
    # 交叉验证：与实际 tier 判据同源（slim 被个人数据词否决）
    state = _state(
        message,
        {"retrieval_decision": {"should_retrieve": False, "retrieval_mode": "no_retrieval"}},
    )
    assert _should_use_slim_standard_context(state, message) is False


def test_lane_deliberate_for_memory_instruction_with_personal_data():
    """R2-F2B（记忆分支闭合）：记忆指令含个人数据词（"记住我的进度"）——根修
    no_retrieval 保留（写记忆无需 RAG），但 slim 被个人数据词否决 → 实际默认链，
    lane 如实报 deliberate。"""
    message = "记住我的进度"
    decision = build_retrieval_decision(message=message, route_intent=None, context={})
    assert decision.reason == "memory_class_turn"
    lane = resolve_capability_lane(
        user_message=message,
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": False, "retrieval_mode": "no_retrieval"},
    )
    assert lane.lane is ChatCapabilityLane.DELIBERATE
    assert lane.memory_class == "memory_instruction"
    assert lane.trigger == "personal_data_or_tool_intent"


def test_lane_decision_observability_payload():
    decision = resolve_capability_lane(
        user_message="我喜欢的电影是什么？",
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": True, "retrieval_mode": "graph_only"},
    )
    payload = decision.to_dict()
    assert payload["lane"] == "fast"
    assert payload["memory_class"] == "memory_retrieval_query"
    assert isinstance(payload["reasons"], list) and payload["reasons"]


def test_record_capability_lane_decision_writes_context_and_metric():
    from prometheus_client import REGISTRY

    context_data: dict = {}
    decision = resolve_capability_lane(
        user_message="我喜欢的电影是什么？",
        context_data={"chat_mode": "standard"},
        retrieval_decision={"should_retrieve": True, "retrieval_mode": "graph_only"},
    )
    before = REGISTRY.get_sample_value(
        "sparkle_chat_capability_lane_total",
        {
            "lane": "fast",
            "memory_class": "memory_retrieval_query",
            "retrieval_mode": "graph_only",
            "trigger": "memory_query_fast_lane",
        },
    )
    record_capability_lane_decision(decision, context_data=context_data)
    after = REGISTRY.get_sample_value(
        "sparkle_chat_capability_lane_total",
        {
            "lane": "fast",
            "memory_class": "memory_retrieval_query",
            "retrieval_mode": "graph_only",
            "trigger": "memory_query_fast_lane",
        },
    )
    assert (after or 0) == (before or 0) + 1
    assert context_data["capability_lane"]["lane"] == "fast"


# ============================================
# 5. 候选链可观测一致性（resolve_candidate_models 顺序修复）
# ============================================


def test_candidate_chain_matches_actual_selection_balanced():
    """可观测面（describe_agent_routing.candidate_models）首位必须等于实际选择。"""
    selection = llm_router.select_model(
        AgentRole.GENERATION,
        task_type=TaskType.STANDARD_RESPONSE,
        reasoning_mode="balanced",
    )
    candidates = llm_router.resolve_candidate_models(
        AgentRole.GENERATION,
        task_type=TaskType.STANDARD_RESPONSE,
        reasoning_mode="balanced",
    )
    assert candidates, "candidate chain must not be empty"
    assert candidates[0] == selection.model_key


def test_candidate_chain_matches_actual_selection_fast_quick_query():
    selection = llm_router.select_model(
        AgentRole.GENERATION,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="fast",
    )
    candidates = llm_router.resolve_candidate_models(
        AgentRole.GENERATION,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="fast",
    )
    assert candidates[0] == selection.model_key
    assert llm_router._available_models[candidates[0]].tier in (ModelTier.FAST, ModelTier.STANDARD)


# ============================================
# 6. fallback 能力兼容（require_tools 不降到无工具能力层）
# ============================================


def test_fallback_candidates_keep_capability_tiers_when_tools_required():
    from app.core.llm_router import LLMSelection
    from app.services.llm.fallback import LLMModelFallbackManager

    manager = LLMModelFallbackManager()
    failed = LLMSelection(
        model_key="dashscope_chat",
        config=llm_router._available_models["dashscope_chat"],
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="test",
    )
    with_tools = manager._get_fallback_candidates(failed, set(), require_tools=True)
    assert with_tools, "tool-bearing fallback must keep candidates"
    capability_ranks = {
        ModelTier.TOP: 0,
        ModelTier.MAX: 1,
        ModelTier.PRO: 2,
        ModelTier.PLUS: 3,
        ModelTier.STANDARD: 4,
        ModelTier.FAST: 5,
    }
    for candidate in with_tools:
        assert (
            candidate.config.tier in capability_ranks
        ), f"tool-bearing fallback leaked non-capability tier: {candidate.model_key} ({candidate.config.tier})"


def test_fallback_candidates_unfiltered_without_tools_flag():
    from app.core.llm_router import LLMSelection
    from app.services.llm.fallback import LLMModelFallbackManager

    manager = LLMModelFallbackManager()
    failed = LLMSelection(
        model_key="dashscope_chat",
        config=llm_router._available_models["dashscope_chat"],
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="test",
    )
    without_flag = manager._get_fallback_candidates(failed, set())
    assert without_flag, "default fallback chain must remain non-empty (backward compat)"


# ============================================
# 7. 端到端落点：generation_node 层的 fast/deliberate A/B
# （零 LLM：FakeLLM + monkeypatch 选型助手；判据 = 选型助手调用形态）
# ============================================


class _FakeGenerationLLM:
    def __init__(self):
        self.agent_role = "generation"

    def is_thinking_mode(self):
        return False

    def get_current_selection(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            model_key="dashscope_fast",
            is_fallback=False,
            estimated_cost_per_1k=0.0001,
            config=SimpleNamespace(
                model_name="qwen3.8-flash",
                provider=SimpleNamespace(value="dashscope"),
                tier=SimpleNamespace(value="fast"),
            ),
        )

    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        from types import SimpleNamespace

        yield SimpleNamespace(type="text", content="已记住。")

    async def chat(self, messages, temperature=0.35):
        return "已记住。"


@pytest.mark.asyncio
async def test_generation_node_memory_instruction_lands_fast_lane(monkeypatch):
    """E-02 验收（A 面）：记忆指令经 generation_node 落 FAST tier + QUICK_QUERY（L1），
    且 capability_lane 判定进入 context_data（可观测）。回放 54/54 实证场景：上游
    仍给 graph_only 检索决策（旧数据/旁路写入）时第二道防线必须放行 slim。"""
    from unittest.mock import AsyncMock

    from app.agents.standard_workflow import generation_node

    fake_llm = _FakeGenerationLLM()
    get_tier_mock = AsyncMock(return_value=fake_llm)
    get_llm_mock = AsyncMock(side_effect=AssertionError("memory instruction must take balanced fast path (FAST tier)"))
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *a, **k: "SYSTEM")

    message = "我最喜欢的电影是《星际穿越》，帮我记住这个"
    graph_only = _graph_only_decision()  # 旧管线对"帮我…"的实际输出（ambiguous→graph_only）
    state = WorkflowState(
        messages=[{"role": "user", "content": message}],
        context_data={
            "chat_mode": "standard",
            "reasoning_mode": "balanced",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
            "retrieval_decision": graph_only,
            "document_retrieval_decision": graph_only,
        },
    )

    new_state = await generation_node(state)

    get_tier_mock.assert_awaited_once_with(
        "generation",
        ModelTier.FAST,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="balanced",
    )
    assert new_state.context_data["first_touch_model_tier"] == ModelTier.FAST.value
    assert new_state.context_data["first_touch_profile"] == "balanced_fast_path"
    lane = new_state.context_data["capability_lane"]
    assert lane["lane"] == "fast"
    assert lane["memory_class"] == "memory_instruction"
    assert "memory_instruction_fast_lane" in lane["reasons"]


@pytest.mark.asyncio
async def test_generation_node_memory_query_rootfix_output_lands_fast(monkeypatch):
    """根修输出（memory_class_turn→no_retrieval）同样落 FAST：两道防线殊途同归。"""
    from unittest.mock import AsyncMock

    from app.agents.standard_workflow import generation_node

    fake_llm = _FakeGenerationLLM()
    get_tier_mock = AsyncMock(return_value=fake_llm)
    get_llm_mock = AsyncMock(side_effect=AssertionError("memory query must take balanced fast path"))
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *a, **k: "SYSTEM")

    message = "我喜欢的电影是什么？"
    rootfix = {
        "should_retrieve": False,
        "retrieval_mode": "no_retrieval",
        "reason": "memory_class_turn",
    }
    state = WorkflowState(
        messages=[{"role": "user", "content": message}],
        context_data={
            "chat_mode": "standard",
            "reasoning_mode": "balanced",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
            "retrieval_decision": rootfix,
            "document_retrieval_decision": rootfix,
        },
    )

    new_state = await generation_node(state)

    get_tier_mock.assert_awaited_once_with(
        "generation",
        ModelTier.FAST,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="balanced",
    )
    assert new_state.context_data["capability_lane"]["lane"] == "fast"
    assert new_state.context_data["capability_lane"]["memory_class"] == "memory_retrieval_query"


@pytest.mark.asyncio
async def test_generation_node_exam_tool_flow_keeps_deliberate(monkeypatch):
    """E-02 验收（保护面）：exam_preparation 工具流（planned_tool_sequence）即使
    文本命中记忆词，也不得走 FAST tier 助手——保持默认链（deliberate + 真实工具执行）。"""
    from unittest.mock import AsyncMock

    from app.agents.standard_workflow import generation_node

    fake_llm = _FakeGenerationLLM()
    get_tier_mock = AsyncMock(side_effect=AssertionError("exam tool flow must NOT be forced to FAST tier"))
    get_llm_mock = AsyncMock(return_value=fake_llm)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service_for_tier", get_tier_mock)
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", get_llm_mock)
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *a, **k: "SYSTEM")

    message = "请记住我的考试范围，然后帮我制定冲刺计划"
    graph_only = _graph_only_decision()
    state = WorkflowState(
        messages=[{"role": "user", "content": message}],
        context_data={
            "chat_mode": "standard",
            "reasoning_mode": "balanced",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
            "retrieval_decision": graph_only,
            "planned_tool_sequence": [{"tool": "get_plan_state"}],
        },
    )

    new_state = await generation_node(state)

    get_llm_mock.assert_awaited_once()
    lane = new_state.context_data["capability_lane"]
    assert lane["lane"] == "deliberate"
    assert lane["tool_flow_protected"] is True
    assert "tool_flow_protected" in lane["reasons"]
    assert "first_touch_model_tier" not in new_state.context_data


# ============================================
# 8. 合成负载 A/B（验收证据）：简单 intent 全量落 L1，复杂流保持 L2/L3
# ============================================

_SIMPLE_INTENT_BATCH = [
    # 记忆指令（写入确认）——V3-FIX-12 主流量（54/54 实证中的记忆指令类）
    "我最喜欢的电影是《星际穿越》，帮我记住这个",
    "记住我的学号是 20250101",
    "别忘了周四下午我要开组会",
    "记一下我 preferred 的复习方式是刷题",
    "请记住：我的期中考试范围是第 1 到第 6 章，第 7 章不考。",
    "帮我记住我导师姓陈",
    # 记忆检索问答
    "我喜欢的电影是什么？",
    "我的学号是多少？",
    "我说过我周末一般几点起床？",
    "我的导师叫什么来着？",
    # 轻量标准问答（无检索需求、短消息、无深度词）
    "谢谢，明白了",
]

_DELIBERATE_INTENT_BATCH = [
    # exam_preparation / 规划工具流
    "帮我制定期末考试复习计划",
    "帮我把考研复习拆解成每周任务",
    "创建一个刷题打卡任务",
    # 文档接地
    "根据我上传的资料总结第三章",
    "这份课件里关于贝叶斯定理的推导详细讲讲",
    # 深度分析
    "深入分析我的学习模式并给出系统性改进方案",
    "为什么我线代错题反复出现？请诊断并给出严谨的归因",
]


def test_synthetic_batch_simple_intents_all_land_fast_lane():
    """合成负载 A 面（确定性、零 LLM）：全部简单 intent → lane=fast 且
    balanced fast path 命中（FAST tier + QUICK_QUERY）——无一条落入 deliberate 默认链。"""
    for message in _SIMPLE_INTENT_BATCH:
        decision = build_retrieval_decision(message=message, route_intent=None, context={})
        state = _state(
            message,
            {
                "retrieval_decision": decision.to_dict(),
                "document_retrieval_decision": decision.to_dict(),
            },
        )
        lane = resolve_capability_lane(
            user_message=message,
            context_data=state.context_data,
        )
        slim = _should_use_slim_standard_context(state, message)
        balanced_fast = _should_force_balanced_fast_first_touch(
            state,
            explicit_runtime=None,
            task_type=TaskType.STANDARD_RESPONSE,
            user_message=message,
            use_slim_standard_context=slim,
        )
        assert lane.lane is ChatCapabilityLane.FAST, f"simple intent must be FAST lane: {message}"
        assert balanced_fast is True, f"simple intent must hit balanced fast path: {message}"
        assert decision.should_retrieve is False, f"simple intent must not trigger retrieval: {message}"


def test_synthetic_batch_complex_intents_all_land_deliberate():
    """合成负载 B 面：工具流/文档接地/深度分析全部保持 deliberate（能力不被降级）。"""
    for message in _DELIBERATE_INTENT_BATCH:
        decision = build_retrieval_decision(message=message, route_intent=None, context={})
        context_data = {"chat_mode": "standard", "retrieval_decision": decision.to_dict()}
        if "制定" in message or "拆解" in message or "创建" in message:
            # exam/task/skill 工具流消息在真实管线由 tool_planning_node 落 planned_tool_sequence
            context_data["planned_tool_sequence"] = [{"tool": "create_plan"}]
        if "资料" in message or "课件" in message:
            # 文档接地轮次在真实管线携带 file_ids（document_grounded）
            context_data["file_ids"] = ["doc-1"]
        state = WorkflowState(
            messages=[{"role": "user", "content": message}],
            context_data=context_data,
        )
        lane = resolve_capability_lane(user_message=message, context_data=state.context_data)
        assert lane.lane is ChatCapabilityLane.DELIBERATE, f"complex intent must stay deliberate: {message}"
        if "制定" in message or "拆解" in message or "创建" in message or "资料" in message or "课件" in message:
            # 工具流与文档接地：完整上下文是能力的一部分，slim 必须否决。
            slim = _should_use_slim_standard_context(state, message)
            assert slim is False, f"tool/doc intent must not use slim context: {message}"
        # 深度词消息：slim（上下文瘦身）与 tier（默认链 deliberate）正交——
        # 能力保障在 lane/tier 层，slim 语义是 HEAD 既有行为，不在本卡回归面。
