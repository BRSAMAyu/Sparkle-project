"""BP-3B: 含规划词汇的纠正请求不得被规划澄清快速通道劫持。

P1-3 调查证据（v3-output/P1-3-REPLAY）：「你说错了，偶数度不一定连通，
纠正一下——我要复习这块」这类含 复习/总结 规划词汇的纠正消息，在
``ValidationEngineMixin._check_sufficiency`` 被规划澄清快速通道短路成
单帧澄清（「先判断对错还是安排复习？」），纠正内容完全未送达；而
纯知识问法下纠正可完整送达——劫持是措辞/意图依赖的。

三类消息契约（LLM 用确定性桩，其余走真实判定链）：
1. 纯知识纠正   → 不短路，走知识应答路径；
2. 含规划词纠正 → 不短路（用户明示纠正/指错优先于规划词汇触发）；
3. 纯规划请求   → 仍短路并返回规划澄清（快速通道既有价值不回退）。
"""

from __future__ import annotations

import asyncio
import importlib
import uuid
from typing import Any

import pytest

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration import planning_intent
from app.orchestration.statechart_engine import WorkflowState
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _install_import_stubs,
    _make_request,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)

# P1-3 证据中的三档原始消息（字面复刻，不做语义改写）
PURE_KNOWLEDGE_CORRECTION = "你说错了，偶数度不一定连通，纠正一下"
CORRECTION_WITH_PLANNING_VOCAB = "你说错了，偶数度不一定连通，纠正一下——我要复习这块"
PURE_PLANNING_REQUEST = "帮我制定一个期末复习计划"

# 生产形状的最小会话上下文：situation_brief 已由 _attach_situation_brief 构建
# （decision_context 全新无 phase A 残留标记），避免测试触碰 DB/LLM 构建路径。
FRESH_SESSION_PAYLOAD: dict[str, Any] = {
    "user_strategy_state": {},
    "situation_brief": {
        "decision_context": {},
    },
}


@pytest.fixture
async def sufficiency_probe(orchestrator_factory, monkeypatch):  # noqa: F811
    """真实 _check_sufficiency 判定链 + 确定性 LLM 桩。

    异步 fixture：ChatOrchestrator 构造期会 asyncio.create_task，必须在
    running loop 内完成。
    """
    _install_import_stubs()
    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    sufficiency_checker_module = importlib.import_module("app.orchestration.sufficiency_checker")

    # 快响文案走兜底（确定性，不经 LLM）
    monkeypatch.setattr(settings, "FAST_INTERACTION_COPY_ENABLED", False, raising=False)
    # 意图影子预测走启发式（确定性，不经模型）
    monkeypatch.setenv("SHADOW_PREDICTION_MODE", "heuristic")

    # sufficiency 的 LLM 精化/澄清生成 → 确定性桩：判定「信息不足」并产出固定澄清句
    async def _stub_json_call(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"specific": False}

    async def _stub_call(*args: Any, **kwargs: Any) -> str:
        return "你是想先判断这个结论对不对，还是要把这块安排进复习时间？"

    monkeypatch.setattr(sufficiency_checker_module.sufficiency_llm, "json_call", _stub_json_call)
    monkeypatch.setattr(sufficiency_checker_module.sufficiency_llm, "call", _stub_call)

    orchestrator, redis_client, _state_updates = orchestrator_factory()

    async def _probe(
        message: str,
        *,
        user_context_payload: dict[str, Any] | None = None,
    ) -> tuple[bool, str, list[agent_service_pb2.ChatResponse]]:
        frames: list[agent_service_pb2.ChatResponse] = []

        async def stream_callback(response: agent_service_pb2.ChatResponse) -> None:
            frames.append(response)

        real_check = orchestrator_module.ChatOrchestrator._check_sufficiency
        short_circuited, intent_type = await real_check(
            orchestrator,
            request=_make_request(message=message),
            user_message=message,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            session_id=f"session-{uuid.uuid4()}",
            conversation_context={
                "session_id": f"session-{uuid.uuid4()}",
                "messages": [],
            },
            user_context_payload=(
                user_context_payload if user_context_payload is not None else dict(FRESH_SESSION_PAYLOAD)
            ),
            plan_context=None,
            state=WorkflowState(),
            active_db=None,
            session_feedback_signal=None,
            stream_callback=stream_callback,
            queue=asyncio.Queue(),
        )
        return short_circuited, intent_type, frames

    return _probe


def _full_text_frames(frames: list[agent_service_pb2.ChatResponse]) -> list[str]:
    return [frame.full_text for frame in frames if frame.full_text]


# ---------------------------------------------------------------------------
# 红线面 1：三类消息的路径契约
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pure_knowledge_correction_reaches_answer_path(sufficiency_probe):
    """纯知识纠正不被任何快速通道吞掉（对照基线，P1-3 followup-probe P1 同型）。"""
    short_circuited, intent_type, frames = await sufficiency_probe(PURE_KNOWLEDGE_CORRECTION)

    assert short_circuited is False, "纯知识纠正必须继续走知识应答路径"
    assert intent_type not in {"create_plan", "time_planning"}
    assert _full_text_frames(frames) == [], "不得发出澄清单帧"


@pytest.mark.asyncio
async def test_correction_with_planning_vocabulary_reaches_answer_path(sufficiency_probe):
    """含规划词的纠正不被规划澄清快速通道劫持（BP-3B 核心红测试）。

    P1-3 事故消息：复习词面使影子预测归为 time_planning，被
    _check_sufficiency 短路成单帧澄清，纠正内容未送达。
    """
    short_circuited, intent_type, frames = await sufficiency_probe(CORRECTION_WITH_PLANNING_VOCAB)

    assert short_circuited is False, "含规划词的纠正请求不得被规划澄清快速通道短路——纠正信号优先于规划词汇"
    assert intent_type == "knowledge_query", "纠正信号应把规划词面意图归一化为知识查询"
    assert _full_text_frames(frames) == [], "不得发出澄清单帧（纠正内容必须送达）"


@pytest.mark.asyncio
async def test_pure_planning_request_still_triggers_planning_clarification(sufficiency_probe):
    """纯规划请求仍触发规划澄清——快速通道既有价值不回退（红线）。"""
    short_circuited, intent_type, frames = await sufficiency_probe(PURE_PLANNING_REQUEST)

    assert short_circuited is True, "纯规划请求仍应走规划澄清快速通道"
    assert intent_type in {"create_plan", "time_planning"}
    assert any("复习" in text or "计划" in text for text in _full_text_frames(frames)), "必须发出规划澄清文案"


@pytest.mark.asyncio
async def test_phase_a_hard_stop_still_fires_for_genuine_planning_turn(sufficiency_probe):
    """Phase A 硬停（ask-before-plan 护栏）对真规划回合保持原样——红线。

    残留 decision_context 带 planning_readiness_action=ask 的活跃规划会话里，
    结构性规划信号照常触发澄清；纠正优先序只压制「词汇级」规划误判。
    """
    planning_session_payload = {
        "user_strategy_state": {},
        "situation_brief": {
            "decision_context": {
                "planning_readiness_action": "ask",
                "strategic_clarification_questions": ["你现在最缺的关键信息是什么？"],
            },
        },
    }
    short_circuited, intent_type, frames = await sufficiency_probe(
        PURE_PLANNING_REQUEST,
        user_context_payload=planning_session_payload,
    )

    assert short_circuited is True, "Phase A ask-before-plan 硬停必须照常触发"
    clarification_texts = _full_text_frames(frames)
    assert any(
        "最缺的关键信息" in text for text in clarification_texts
    ), f"必须发出 Phase A 澄清文案，实际帧：{clarification_texts!r}"


# ---------------------------------------------------------------------------
# 红线面 2：纠正信号原语与判定序（单元级）
# ---------------------------------------------------------------------------


def test_has_correction_signal_marker_coverage():
    has_correction_signal = planning_intent.has_correction_signal

    for message in (
        "你说错了，偶数度不一定连通",
        "不对，欧拉回路还要求连通",
        "这里需要纠正一下",
        "其实是个充分不必要条件",
        "你搞错了，是哈密顿路径",
        "更正：我上一条总结写反了",
    ):
        assert has_correction_signal(message), f"应为纠正信号：{message}"

    for message in (
        "帮我制定一个期末复习计划",
        "偶数度是不是一定连通？对不对？",
        "帮我安排下周的复习时间",
        "",
        None,
    ):
        assert not has_correction_signal(message), f"不应误判为纠正信号：{message}"


def test_detect_planning_like_turn_correction_beats_message_vocabulary():
    detect = planning_intent.detect_planning_like_turn

    # 词面含「复习计划」，但用户在指错 → 消息级规划回退被纠正信号压制
    planning_like, source = detect(
        normalized_intent=None,
        route_intent=None,
        user_message="你说错了，我复习计划里那条总结不对，纠正一下",
        decision_context=None,
    )
    assert planning_like is False
    assert source == "none"

    # 纯规划词面消息 → 消息级回退照常生效（既有价值不回退）
    planning_like, source = detect(
        normalized_intent=None,
        route_intent=None,
        user_message="帮我做个期末复习计划",
        decision_context=None,
    )
    assert planning_like is True
    assert source == "message_fallback"

    # 结构性信号（分类器意图）不被纠正信号改写——降级发生在归一化层
    planning_like, source = detect(
        normalized_intent="create_plan",
        route_intent=None,
        user_message="你说错了，纠正一下",
        decision_context=None,
    )
    assert planning_like is True
    assert source == "normalized_intent"


def test_normalize_sufficiency_intent_correction_priority():
    import importlib as _importlib

    orchestrator_module = _importlib.import_module("app.orchestration.orchestrator")
    normalize = orchestrator_module.ChatOrchestrator._normalize_sufficiency_intent_type

    # 规划词面 + 明示纠正 → 降级为知识查询（纠正优先）
    assert (
        normalize(
            intent_type="time_planning",
            user_message=CORRECTION_WITH_PLANNING_VOCAB,
        )
        == "knowledge_query"
    )
    assert (
        normalize(
            intent_type="create_plan",
            user_message="你说错了，偶数度推不出连通，纠正一下",
        )
        == "knowledge_query"
    )

    # 明确的规划动作请求不被纠正词面误伤（既有规划体验不回退）
    assert (
        normalize(
            intent_type="time_planning",
            user_message="你说得不对，我周六才有空，帮我重新制定复习计划",
        )
        == "time_planning"
    )

    # 无纠正信号的规划意图维持原判
    assert (
        normalize(
            intent_type="time_planning",
            user_message=PURE_PLANNING_REQUEST,
        )
        == "time_planning"
    )

    # 既有咨询性降级（advisory markers）不受影响
    assert (
        normalize(
            intent_type="time_planning",
            user_message="这两个方向我该怎么选？先学哪个比较好",
        )
        == "knowledge_query"
    )
