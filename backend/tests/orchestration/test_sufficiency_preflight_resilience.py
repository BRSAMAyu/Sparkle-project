"""ORCH-DEBT: BP-3B 施工中申报的两个编排层缺陷（P2/P3）修复验证。

P2 · preflight contradiction_map=None 崩溃静默杀死 sufficiency 检查：
  ``situation_brief.insight_state`` 为 dict 但缺省/显式 None 的
  ``contradiction_map``（生产形状：situation_brief.py profile-missing 回退
  分支构建的 insight_state 无该键）使 ``_check_phase_a_planning_preflight``
  的列表推导抛 TypeError，被 ``_check_sufficiency`` 兜底 except 吞掉 →
  整个 sufficiency 检查（含澄清）无声跳过，用户无感知失去充分性校验。
  契约：None = 无矛盾数据 → 跳过 contradiction 比对，sufficiency 链照常。

P3 · 会话态残留 ask 硬停 Phase A 路径：
  残留 decision_context 携带上一回合已问出（surfaced）的
  ``planning_readiness_action=ask``；硬停早退不回写会话态 → 用户回答的
  下一回合再次被同一问题硬停，会话死锁。契约：ask 一次性消费——
  已 surfaced 的残留 ask 必须清理并放行（恢复）；未 surfaced 的新鲜 ask
  硬停不回退（BP-3B 红线），且硬停时必须落 surfaced 标记阻断死循环。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import uuid
from typing import Any

import pytest

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.statechart_engine import WorkflowState
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _install_import_stubs,
    _make_request,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)

PURE_PLANNING_REQUEST = "帮我制定一个期末复习计划"
# 用户对已问出 ask 的回答（无规划词 → unknown 意图，sufficiency 直接放行）
PURE_ANSWER_MESSAGE = "我周六全天有空，重点想补数学和英语"
# 回答里带规划词（真实事故形状：卡死后用户怎么答都会被再问一遍）
ANSWER_WITH_PLANNING_VOCAB = "周六下午和晚上都行，就按你说的帮我安排复习"


def _residual_payload(decision_context: dict[str, Any], insight_state: dict[str, Any]) -> dict[str, Any]:
    """残留会话态形状：上一回合 situation_brief 经响应元数据回传。"""
    return {
        "user_strategy_state": {},
        "situation_brief": {
            "decision_context": decision_context,
            "insight_state": insight_state,
        },
    }


@pytest.fixture
async def preflight_probe(orchestrator_factory, monkeypatch):  # noqa: F811
    """真实 _check_sufficiency 判定链 + 确定性 LLM 桩（跟随 BP-3B 测试模式）。

    返回 probe：入参 (message, user_context_payload)，出参
    (short_circuited, intent_type, frames, payload)——payload 原样返回，
    供断言残留清理是否落盘。
    """
    _install_import_stubs()
    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    sufficiency_checker_module = importlib.import_module("app.orchestration.sufficiency_checker")

    # 说明：上游 test_orchestrator_process_stream_integration 的假
    # shadow_prediction_service 注入已改为 monkeypatch 作用域（自动回收），
    # 本文件原先的「钉回真实模块」防御随之移除（TEST-HYGIENE 治理）。

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

    orchestrator, _redis_client, _state_updates = orchestrator_factory()

    async def _probe(
        message: str,
        *,
        user_context_payload: dict[str, Any],
    ) -> tuple[bool, str, list[agent_service_pb2.ChatResponse], dict[str, Any]]:
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
            user_context_payload=user_context_payload,
            plan_context=None,
            state=WorkflowState(),
            active_db=None,
            session_feedback_signal=None,
            stream_callback=stream_callback,
            queue=asyncio.Queue(),
        )
        return short_circuited, intent_type, frames, user_context_payload

    return _probe


def _full_text_frames(frames: list[agent_service_pb2.ChatResponse]) -> list[str]:
    return [frame.full_text for frame in frames if frame.full_text]


def _phase_a_clarification_frames(frames: list[agent_service_pb2.ChatResponse]) -> list[agent_service_pb2.ChatResponse]:
    """带 clarification_source=phase_a 元数据的状态帧（Phase A 硬停指纹）。"""
    return [frame for frame in frames if frame.metadata.get("clarification_source") == "phase_a"]


# ---------------------------------------------------------------------------
# P2 · preflight contradiction_map=None 崩溃静默杀死 sufficiency 检查
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "insight_state",
    [
        # 生产形状：profile-missing 回退分支构建的 insight_state 无 contradiction_map 键
        ({"readiness_level": "low", "recommended_action": "provisional"}),
        # 防御形状：显式 None（序列化/历史残留）
        ({"readiness_level": "low", "contradiction_map": None}),
    ],
    ids=["missing_key", "explicit_none"],
)
async def test_unset_contradiction_map_degrades_and_sufficiency_survives(preflight_probe, insight_state):
    """contradiction_map 缺省/None = 无矛盾数据：preflight 安全降级，sufficiency 照常。

    红症状：TypeError 被 _check_sufficiency 兜底 except 吞掉 → 规划澄清
    无声消失（short_circuited=False 且零帧）——充分性校验无感知失效。
    """
    payload = _residual_payload(decision_context={}, insight_state=insight_state)
    short_circuited, intent_type, frames, _ = await preflight_probe(
        PURE_PLANNING_REQUEST,
        user_context_payload=payload,
    )

    assert (
        short_circuited is True
    ), "contradiction_map=None 必须按无矛盾数据降级，sufficiency 检查（规划澄清）必须照常执行"
    assert intent_type in {"create_plan", "time_planning"}
    clarification_texts = _full_text_frames(frames)
    assert any(
        ("复习" in text or "计划" in text) for text in clarification_texts
    ), f"必须发出 sufficiency 澄清文案，实际帧：{clarification_texts!r}"


# ---------------------------------------------------------------------------
# P3 · 会话态残留 ask 硬停 Phase A 路径
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_residual_surfaced_ask_releases_instead_of_hard_stop(preflight_probe):
    """已问出（surfaced）的残留 ask：用户回答的下一回合必须恢复而非再次硬停。"""
    surfaced_at = "2026-09-22T08:00:00+00:00"
    payload = _residual_payload(
        decision_context={
            "planning_readiness_action": "ask",
            "phase_a_guardrail": "ask_before_plan",
            "phase_a_ask_surfaced": "true",
            "phase_a_ask_surfaced_at": surfaced_at,
            "strategic_clarification_questions": ["你现在最缺的关键信息是什么？"],
        },
        insight_state={},
    )
    short_circuited, _intent_type, frames, payload = await preflight_probe(
        PURE_ANSWER_MESSAGE,
        user_context_payload=payload,
    )

    assert short_circuited is False, "已问出的残留 ask 必须放行（用户回答必须送达下游），不得再次硬停"
    assert _phase_a_clarification_frames(frames) == [], "不得再次发出 Phase A 澄清帧（ask 一次性消费）"
    assert _full_text_frames(frames) == []

    decision_context = payload["situation_brief"]["decision_context"]
    assert decision_context.get("planning_readiness_action") == "", "残留 pending ask 必须被清理"
    assert decision_context.get("phase_a_guardrail") == "", "残留 ask_before_plan 护栏标记必须被清理"

    evaluation = payload.get("phase_a_evaluation") or {}
    assert evaluation.get("ask_residual_consumed") == "true", "消费事件必须落盘供可观测"


@pytest.mark.asyncio
async def test_answer_with_planning_vocab_in_residual_ask_session_not_hard_stopped(preflight_probe):
    """残留 ask 会话中带规划词的回答不得被 Phase A 硬停（事故主形状）。

    后续通道（常规 sufficiency 澄清等）不受此约束——只禁 Phase A 硬停帧。
    """
    payload = _residual_payload(
        decision_context={
            "planning_readiness_action": "ask",
            "phase_a_guardrail": "ask_before_plan",
            "phase_a_ask_surfaced": "true",
            "phase_a_ask_surfaced_at": "2026-09-22T08:00:00+00:00",
            "strategic_clarification_questions": ["你现在最缺的关键信息是什么？"],
        },
        insight_state={},
    )
    short_circuited, _intent_type, frames, _ = await preflight_probe(
        ANSWER_WITH_PLANNING_VOCAB,
        user_context_payload=payload,
    )

    assert _phase_a_clarification_frames(frames) == [], "带规划词的回答不得被 Phase A ask 硬停劫持"


@pytest.mark.asyncio
async def test_fresh_unsurfaced_ask_still_hard_stops_and_marks_surfaced(preflight_probe):
    """红线：未问出的新鲜 ask 硬停不回退（BP-3B）；且硬停必须落 surfaced 标记
    并把清理后的 brief 随快响帧元数据回传——阻断下一回合死循环。"""
    payload = _residual_payload(
        decision_context={
            "planning_readiness_action": "ask",
            "strategic_clarification_questions": ["你现在最缺的关键信息是什么？"],
        },
        insight_state={},
    )
    short_circuited, _intent_type, frames, payload = await preflight_probe(
        PURE_PLANNING_REQUEST,
        user_context_payload=payload,
    )

    assert short_circuited is True, "新鲜 ask 的 ask-before-plan 硬停必须照常触发"
    assert _phase_a_clarification_frames(frames), "必须发出 Phase A 澄清帧"

    decision_context = payload["situation_brief"]["decision_context"]
    assert decision_context.get("phase_a_ask_surfaced") == "true", "硬停必须落 surfaced 标记"
    assert decision_context.get("phase_a_ask_surfaced_at"), "surfaced 标记必须带时间戳"
    assert decision_context.get("planning_readiness_action") == "", "问出后 pending ask 必须消费清零"

    metadata_frames = [frame for frame in frames if frame.metadata.get("situation_brief")]
    assert metadata_frames, "快响帧元数据必须回传清理后的 situation_brief（残留态修复通道）"
    carried = json.loads(metadata_frames[0].metadata["situation_brief"])
    carried_decision = carried.get("decision_context") or {}
    assert carried_decision.get("phase_a_ask_surfaced") == "true"
    assert carried_decision.get("planning_readiness_action") == ""
