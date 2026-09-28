"""V4-I09 真正零模型的确定性快路与快慢分层。

背景（B06 全链探针 t3 实证）：问候语轮现行仍进 generation_node → 真实上游
流式调用（dashscope 400）→ rescue 非流式二次调用 → 合成估算记账 44 tok。
本卡交付：纯规则零模型快路（问候/确认/无信息量轮）+ lane=deterministic/model
快慢分层可观测 + 记账面零合成估算污染。行为开关默认关。

验收锚点（卡面）：
- L0 token=0 且无隐含模型 attempt（含路由层 embedding）；
- 有效首内容不以 stage/ack/模板鸡汤抵扣（快路只吃零信息量形态）；
- 路由与降级不损工具/授权合同（工具流/文档/专家/提案确认全部回落慢路）。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.graph.nodes.review_nodes import _should_skip_review
from app.agents.standard_workflow import generation_node, router_node
from app.config import settings
from app.config.settings import settings as settings_module
from app.core.llm_secure_io import secure_messages
from app.orchestration.deterministic_lane import (
    CHAT_LANE_DETERMINISTIC,
    CHAT_LANE_MODEL,
    DeterministicLaneKind,
    record_deterministic_lane_decision,
    resolve_deterministic_lane,
)
from app.orchestration.response_builder import ResponseBuilderMixin
from app.orchestration.statechart_engine import WorkflowState


def _state(message: str, context_data: dict | None = None) -> WorkflowState:
    return WorkflowState(
        messages=[{"role": "user", "content": message}],
        context_data={"chat_mode": "standard", **(context_data or {})},
    )


# ============================================
# 1. 形态判定：命中（问候/确认/告别）
# ============================================


@pytest.mark.parametrize(
    "message,expected_kind",
    [
        ("你好", DeterministicLaneKind.GREETING),
        ("您好！", DeterministicLaneKind.GREETING),
        ("hello", DeterministicLaneKind.GREETING),
        ("在吗", DeterministicLaneKind.GREETING),
        ("你好呀！！", DeterministicLaneKind.GREETING),
        ("嗯嗯", DeterministicLaneKind.ACKNOWLEDGMENT),
        ("好的", DeterministicLaneKind.ACKNOWLEDGMENT),
        ("收到，谢谢", DeterministicLaneKind.ACKNOWLEDGMENT),
        ("谢谢啦", DeterministicLaneKind.ACKNOWLEDGMENT),
        ("OK", DeterministicLaneKind.ACKNOWLEDGMENT),
        ("明白了", DeterministicLaneKind.ACKNOWLEDGMENT),
        ("拜拜", DeterministicLaneKind.FAREWELL),
        ("晚安", DeterministicLaneKind.FAREWELL),
    ],
)
def test_deterministic_shapes_hit(message, expected_kind):
    decision = resolve_deterministic_lane(message, {"chat_mode": "standard"})
    assert decision is not None
    assert decision.kind is expected_kind
    assert decision.reply.strip()
    assert decision.template_version == "v1"


# ============================================
# 2. 形态判定：不命中（回落真模型慢路）
# ============================================


@pytest.mark.parametrize(
    "message",
    [
        "你好，帮我制定期末复习计划",  # 问候 + 实质请求
        "这个知识点是什么？",  # 真问题
        "你是谁",  # 身份问题（慢路应答）
        "hi5",  # 剥词后残留实质字符
        "this",  # 英文普通词
        "对的",  # 提案应允（上下文依赖，有意排除）
        "继续",  # 指续写上文（有意排除）
        "好的，那继续讲第二个考点",  # 剥词后残留实质
        "深入讲讲记忆曲线的原理",  # 深度词
        "帮我把这个添加到我的日历",  # 工具动作意图
        "查一下我的计划进度",  # 个人数据意图
        "你好你好你好你好你好你好你好你好你好你好你好你好你好你好你好你好",  # 超长保护
    ],
)
def test_substantive_messages_fall_back_to_model(message):
    assert resolve_deterministic_lane(message, {"chat_mode": "standard"}) is None


# ============================================
# 3. 上下文守卫：deliberate 事实在场永不快路（工具/授权合同不损）
# ============================================


@pytest.mark.parametrize(
    "context_data",
    [
        {"chat_mode": "deep_analysis"},
        {"planned_tool_sequence": ["get_plan_state"]},
        {"reasoning_mode": "deep"},
        {"file_ids": ["f-1"]},
        {"selected_experts": ["deep_analyst"]},
        {"agent_role": "study_buddy"},
        {"document_retrieval_decision": {"should_retrieve": True, "retrieval_mode": "targeted_source_rag"}},
    ],
)
def test_context_guards_block_fast_lane(context_data):
    context = {"chat_mode": "standard", **context_data}
    assert resolve_deterministic_lane("你好", context) is None


def test_document_mode_blocked_via_retrieval_decision_alias():
    context = {
        "chat_mode": "standard",
        "retrieval_decision": {"should_retrieve": True, "retrieval_mode": "deep_source_synthesis"},
    }
    assert resolve_deterministic_lane("好的", context) is None


# ============================================
# 4. 待提案守卫：助手上一条以问句/提案收尾时确认类让位
# ============================================


def _context_with_last_assistant(content: str) -> dict:
    return {
        "chat_mode": "standard",
        "conversation_context": {
            "messages": [
                {"role": "user", "content": "帮我复习"},
                {"role": "assistant", "content": content},
            ]
        },
    }


def test_ack_after_assistant_question_falls_back():
    context = _context_with_last_assistant("需要我把这些考点整理成一张卡片吗？")
    assert resolve_deterministic_lane("好的", context) is None


def test_ack_after_plain_statement_still_hits():
    context = _context_with_last_assistant("已经把番茄钟法整理成上面的步骤了。")
    decision = resolve_deterministic_lane("好的", context)
    assert decision is not None
    assert decision.kind is DeterministicLaneKind.ACKNOWLEDGMENT


def test_greeting_not_subject_to_proposal_guard():
    context = _context_with_last_assistant("需要我把这些考点整理成一张卡片吗？")
    decision = resolve_deterministic_lane("你好", context)
    assert decision is not None
    assert decision.kind is DeterministicLaneKind.GREETING


# ============================================
# 5. 行为开关：默认关（release_flags 同族模式）
# ============================================


def test_flag_defaults_off():
    assert settings.ENABLE_DETERMINISTIC_FAST_LANE is False


def test_record_writes_lane_context():
    decision = resolve_deterministic_lane("你好", {"chat_mode": "standard"})
    assert decision is not None
    context_data: dict = {}
    record_deterministic_lane_decision(decision, context_data=context_data)
    assert context_data["chat_lane"] == CHAT_LANE_DETERMINISTIC
    assert context_data["deterministic_lane"]["kind"] == "greeting"
    assert context_data["deterministic_lane"]["lane"] == "deterministic"


# ============================================
# 6. generation_node 集成：零模型断言 + lane 标记在场
# ============================================


class _Frames:
    def __init__(self):
        self.frames: list = []

    async def __call__(self, frame) -> None:
        self.frames.append(frame)


def _fail_if_model_configured(message: str = "generation model must not be configured on deterministic lane"):
    return AsyncMock(side_effect=AssertionError(message))


@pytest.mark.asyncio
async def test_generation_node_greeting_zero_model_with_lane_marker(monkeypatch):
    monkeypatch.setattr(settings_module, "ENABLE_DETERMINISTIC_FAST_LANE", True)
    # 任何模型选择/提示词组装 = 隐含模型 attempt，命中即 fail。
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service",
        _fail_if_model_configured("get_configured_llm_service"),
    )
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service_for_tier",
        _fail_if_model_configured("get_configured_llm_service_for_tier"),
    )
    monkeypatch.setattr(
        "app.agents.standard_workflow.build_system_prompt",
        _fail_if_model_configured("build_system_prompt"),
    )

    frames = _Frames()
    state = _state(
        "你好",
        {"stream_callback": frames, "user_context": {}, "conversation_context": {"messages": []}},
    )

    new_state = await generation_node(state)

    # 零模型：assistant 直出模板，终态 __end__。
    assert new_state.messages[-1]["role"] == "assistant"
    assert new_state.messages[-1]["content"].strip()
    assert new_state.next_step == "__end__"
    assert new_state.context_data["chat_lane"] == CHAT_LANE_DETERMINISTIC
    assert new_state.context_data["deterministic_lane"]["kind"] == "greeting"

    # lane 标记在场：status 帧 metadata + delta 帧（模板应答文本必达）。
    assert frames.frames, "stream frames must be emitted"
    metadata_frames = [f for f in frames.frames if getattr(f, "metadata", None)]
    assert any(md.get("chat_lane") == "deterministic" for f in metadata_frames for md in [f.metadata])
    delta_texts = [f.delta for f in frames.frames if getattr(f, "delta", "")]
    assert any(text == new_state.messages[-1]["content"] for text in delta_texts)
    # 零 usage 帧（无隐含模型 attempt 的客户端可见面）。
    assert not [f for f in frames.frames if f.HasField("usage")]


@pytest.mark.asyncio
async def test_generation_node_slow_path_regression_with_flag_off(monkeypatch):
    """开关默认关：同一问候走既有真模型链路（回归不受影响），lane=model。"""
    monkeypatch.setattr(settings_module, "ENABLE_DETERMINISTIC_FAST_LANE", False)

    class _FakeLLM:
        agent_role = "generation"

        def __init__(self):
            self.calls = 0

        def is_thinking_mode(self):
            return False

        def get_current_selection(self):
            return SimpleNamespace(
                model_key="dashscope_fast",
                is_fallback=False,
                estimated_cost_per_1k=0.0001,
                config=SimpleNamespace(
                    model_name="qwen-flash",
                    provider=SimpleNamespace(value="dashscope"),
                    tier=SimpleNamespace(value="fast"),
                ),
            )

        async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
            self.calls += 1
            yield SimpleNamespace(type="text", content="你好！今天想学点什么？")

    fake_llm = _FakeLLM()
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service_for_tier", AsyncMock(return_value=fake_llm)
    )
    monkeypatch.setattr("app.agents.standard_workflow.get_configured_llm_service", AsyncMock(return_value=fake_llm))
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    frames = _Frames()
    state = _state(
        "你好",
        {"stream_callback": frames, "user_context": {}, "conversation_context": {"messages": []}},
    )

    new_state = await generation_node(state)

    assert fake_llm.calls == 1
    assert new_state.messages[-1]["content"] == "你好！今天想学点什么？"
    assert new_state.context_data["chat_lane"] == CHAT_LANE_MODEL
    assert "deterministic_lane" not in new_state.context_data
    assert not any(
        getattr(f, "metadata", None) and f.metadata.get("chat_lane") == "deterministic" for f in frames.frames
    )


# ============================================
# 7. router_node：快路免路由（零 embedding 隐含模型 attempt）
# ============================================


@pytest.mark.asyncio
async def test_router_node_skips_router_on_deterministic_turn(monkeypatch):
    monkeypatch.setattr(settings_module, "ENABLE_DETERMINISTIC_FAST_LANE", True)

    class _RouterMustNotRun:
        def __init__(self, *args, **kwargs):
            raise AssertionError("RouterNode (embedding attempts) must be skipped on deterministic lane")

    monkeypatch.setattr("app.routing.router_node.RouterNode", _RouterMustNotRun)

    state = _state("你好")
    new_state = await router_node(state)
    assert new_state.context_data["router_decision"] == "generation"
    assert new_state.context_data["router_confidence"] == 1.0


@pytest.mark.asyncio
async def test_router_node_still_routes_substantive_turn(monkeypatch):
    """非快路形态：路由行为保持既有（RouterNode 正常构建）。"""
    monkeypatch.setattr(settings_module, "ENABLE_DETERMINISTIC_FAST_LANE", True)

    constructed: list[int] = []

    class _FakeRouterNode:
        def __init__(self, *args, **kwargs):
            constructed.append(1)

        async def __call__(self, state):
            state.context_data["router_decision"] = "generation"
            state.context_data["router_confidence"] = 0.5
            return state

    monkeypatch.setattr("app.routing.router_node.RouterNode", _FakeRouterNode)

    state = _state("帮我制定期末复习计划")
    new_state = await router_node(state)
    assert constructed == [1]
    assert new_state.context_data["router_decision"] == "generation"


# ============================================
# 8. 审查层：确定性快路显式跳过 review/reflection
# ============================================


def test_review_skipped_for_deterministic_lane():
    state = WorkflowState(
        messages=[
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！我是 Sparkle，你的学习成长伙伴。"},
        ],
        context_data={"chat_mode": "standard", "chat_lane": CHAT_LANE_DETERMINISTIC},
    )
    assert _should_skip_review(state) is True


def test_review_not_skipped_for_model_lane_long_content():
    state = WorkflowState(
        messages=[
            {"role": "user", "content": "讲解一下记忆曲线"},
            {"role": "assistant", "content": "记忆曲线揭示了遗忘在学习后立即开始，且初期速度最快。" * 5},
        ],
        context_data={"chat_mode": "standard", "chat_lane": CHAT_LANE_MODEL},
    )
    assert _should_skip_review(state) is False


# ============================================
# 9. 记账面：快路零合成估算；慢路保持既有估算
# ============================================


def _cleanup_harness(token_tracker) -> ResponseBuilderMixin:
    harness = ResponseBuilderMixin()
    harness.token_tracker = token_tracker
    harness.state_manager = SimpleNamespace(stop_lock_renewal=AsyncMock())
    return harness


def _final_state(chat_lane: str | None, assistant_text: str = "你好！我是 Sparkle。") -> WorkflowState:
    context_data: dict = {"chat_mode": "standard"}
    if chat_lane:
        context_data["chat_lane"] = chat_lane
    return WorkflowState(
        messages=[
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": assistant_text},
        ],
        context_data=context_data,
    )


@pytest.mark.asyncio
async def test_cleanup_zero_model_lane_records_no_synthetic_tokens(monkeypatch):
    """快路（chat_lane=deterministic）不注入合成估算 token；账面 0+0。"""
    token_tracker = SimpleNamespace(
        estimate_cost=AsyncMock(return_value=0.0),
        record_usage=AsyncMock(),
    )
    harness = _cleanup_harness(token_tracker)

    captured: dict = {}

    async def _fake_spawn(coro, **kwargs):
        captured["coro"] = coro

    from app.core import task_manager as task_manager_module

    monkeypatch.setattr(task_manager_module.task_manager, "spawn", _fake_spawn)

    await harness._cleanup(
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="s-1",
        request_id="r-1",
        start_time=0.0,
        user_id="u-1",
        total_prompt_tokens=0,
        total_completion_tokens=0,
        final_state=_final_state(CHAT_LANE_DETERMINISTIC),
    )

    assert captured["coro"] is not None
    await captured["coro"]
    # 0+0 真实用量直达记账（no_generation_model 桶），合成估算未污染。
    assert token_tracker.estimate_cost.await_args.kwargs.get("prompt_tokens", 0) == 0
    assert token_tracker.estimate_cost.await_args.kwargs.get("completion_tokens", 0) == 0
    assert token_tracker.record_usage.await_args.kwargs["prompt_tokens"] == 0
    assert token_tracker.record_usage.await_args.kwargs["completion_tokens"] == 0


@pytest.mark.asyncio
async def test_cleanup_model_lane_keeps_synthetic_estimation(monkeypatch):
    """真模型慢路（无 usage 帧）保持既有合成估算行为（I10 计量卡再收敛）。"""
    token_tracker = SimpleNamespace(
        estimate_cost=AsyncMock(return_value=0.001),
        record_usage=AsyncMock(),
    )
    harness = _cleanup_harness(token_tracker)

    captured: dict = {}

    async def _fake_spawn(coro, **kwargs):
        captured["coro"] = coro

    from app.core import task_manager as task_manager_module

    monkeypatch.setattr(task_manager_module.task_manager, "spawn", _fake_spawn)

    await harness._cleanup(
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="s-1",
        request_id="r-1",
        start_time=0.0,
        user_id="u-1",
        total_prompt_tokens=0,
        total_completion_tokens=0,
        final_state=_final_state(CHAT_LANE_MODEL),
    )

    assert captured["coro"] is not None
    await captured["coro"]
    recorded = token_tracker.record_usage.await_args.kwargs
    assert recorded["prompt_tokens"] > 0
    assert recorded["completion_tokens"] > 0


# ============================================
# 10. 组装点角色归一化（B06 线索顺手修：dashscope 400 防御）
# ============================================


def test_secure_messages_normalizes_uppercase_roles():
    secured = secure_messages(
        [
            {"role": "USER", "content": "你好"},
            {"role": "Assistant", "content": "你好！"},
            {"role": "TOOL", "content": "result"},
            {"role": "SUPPORT", "content": "x"},
        ]
    )
    assert [m["role"] for m in secured] == ["user", "assistant", "tool", "user"]


def test_secure_messages_keeps_lowercase_roles():
    secured = secure_messages(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u"},
        ]
    )
    assert [m["role"] for m in secured] == ["system", "user"]
