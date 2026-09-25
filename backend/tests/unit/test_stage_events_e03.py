"""E-03 实时 Stage Events 与首反馈体验——红绿契约测试.

卡片目标：用真实阶段事件替代深路径「20s 无反馈」，且不暴露 chain-of-thought。

验收锚点（与卡片 acceptance 一一对应）：
1. 深路径 500ms 内有真实阶段反馈（服务可知后立即下发首个 stage event，
   不等首个 token，也不等重上下文构建完成）——test_first_stage_frame_beats_slow_context_build
2. stage 与 trace 匹配（每个下发 stage 帧携带 ledger_event_id，可回查
   RunLedger 事件且 workflow_stage 与 stage 词表 1:1）——
   test_deep_path_stage_sequence_matches_ledger / test_stage_events_module_contract
3. 不显示 reasoning_content 原文——test_reasoning_chunks_never_leak_into_frames
4. context/retrieval/decision/tool/waiting stage 事件定义——
   test_stage_events_module_contract / test_dag_observer_emits_tool_stage_and_confirmation_waiting
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.run_ledger import RunLedgerRecorder
from app.orchestration.schemas import RouteDecision

# ---------------------------------------------------------------------------
# process_stream 全链路 harness（复用 test_done_tail_latency.py 的成熟桩面）
# ---------------------------------------------------------------------------


def _build_orchestrator(events: list[str], *, slow_context_seconds: float = 0.0) -> ChatOrchestrator:
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
    orchestrator._hydrate_companion_runtime_context = AsyncMock(return_value={})
    orchestrator._validate_request = AsyncMock(return_value=None)
    orchestrator._check_idempotency_response = AsyncMock(return_value=None)
    orchestrator._acquire_session_lock = AsyncMock(return_value=True)
    orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))

    async def slow_build_full_context(**kwargs: Any) -> tuple:
        if slow_context_seconds > 0:
            await asyncio.sleep(slow_context_seconds)
        events.append("context_build_finished")
        return ({}, None, False, {}, {"messages": []}, None)

    orchestrator._build_full_context = slow_build_full_context
    orchestrator._detect_session_feedback = AsyncMock(return_value=(None, None, None))
    orchestrator._apply_cohort_to_session_feedback_signal = MagicMock(side_effect=lambda signal, cohort: signal)
    orchestrator._maybe_enqueue_perceptible_insight = AsyncMock(return_value=None)
    orchestrator._maybe_enqueue_understanding_depth = AsyncMock(return_value=None)
    orchestrator._drain_system_updates = AsyncMock(
        return_value=(
            [],
            [],
            [],
            [],
            None,
            None,
            {
                "proactive_opening_message": "",
                "pending_observation": "",
                "post_adaptation_question": "",
            },
        )
    )
    orchestrator._check_sufficiency = AsyncMock(return_value=(False, "chat"))
    orchestrator._check_goal_quality = AsyncMock(return_value=False)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator._prepare_runtime_context = AsyncMock(return_value=(None, lambda *args, **kwargs: None))
    orchestrator._notify_pending_milestone_proposals = AsyncMock(return_value=None)
    orchestrator._apply_context_focus_overlay = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
    orchestrator._apply_dual_core_routing = AsyncMock(
        return_value=RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low")
    )
    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )

    async def hydrate_documents(**kwargs: Any) -> dict:
        events.append("document_retrieval_started")
        return kwargs.get("user_context_payload") or {}

    orchestrator._hydrate_document_context = hydrate_documents
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (kwargs["route_decision"], None, None, False)
    )
    orchestrator._cache_response = AsyncMock(return_value=True)
    orchestrator._persist_assistant_message = AsyncMock(return_value=None)
    orchestrator._record_decision = AsyncMock(return_value=None)
    orchestrator._cleanup = AsyncMock(return_value=None)

    async def execute_graph(*, queue, result_holder, **kwargs):
        # 镜像真实 _execute_graph 语义：先排空 queue（生产中 stage 帧经
        # stream_callback 入队、由图执行循环出队下发），再出内容帧。
        while not queue.empty():
            yield await queue.get()
            queue.task_done()
        yield agent_service_pb2.ChatResponse(delta="Hello, I am Sparkle AI.")
        events.append("delta")
        result_holder["final_state"] = MagicMock()

    orchestrator._execute_graph = execute_graph

    orchestrator._build_final_response = AsyncMock(
        return_value=(
            agent_service_pb2.ChatResponse(
                session_id="test_sess",
                full_text="Hello, I am Sparkle AI.",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "Hello, I am Sparkle AI."},
        )
    )

    @contextlib.asynccontextmanager
    async def fake_finalize_session():
        yield MagicMock()

    orchestrator._create_finalize_db_session = fake_finalize_session
    orchestrator._write_turn_end_episodic_memory = AsyncMock(return_value=None)
    orchestrator._maybe_upsert_session_mood = AsyncMock(return_value=None)
    return orchestrator


def _spy_run_ledger(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """捕获本轮全部 RunLedger 事件（record_event 返回值即事件字典）。"""
    recorded: list[dict[str, Any]] = []
    original = RunLedgerRecorder.record_event

    async def spy(self: RunLedgerRecorder, **kwargs: Any) -> dict[str, Any]:
        event = await original(self, **kwargs)
        recorded.append(event)
        return event

    monkeypatch.setattr(RunLedgerRecorder, "record_event", spy)
    return recorded


def _extract_stage_frames(responses: list[Any]) -> list[dict[str, Any]]:
    """抽出流内全部携带 ux_progress 的 status_update 帧的 ux_progress 载荷。"""
    stages: list[dict[str, Any]] = []
    for resp in responses:
        if resp.WhichOneof("content") != "status_update":
            continue
        raw = resp.metadata.get("ux_progress")
        if not raw:
            continue
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("stage"):
            stages.append(payload)
    return stages


async def _drive(orchestrator: ChatOrchestrator, *, request_id: str = "e03_req") -> list[Any]:
    request = agent_service_pb2.ChatRequest(
        request_id=request_id,
        session_id="test_sess",
        user_id=str(uuid.uuid4()),
        message="帮我深度分析一下这个学期该怎么复习",
    )
    responses: list[Any] = []
    async for resp in orchestrator.process_stream(request):
        responses.append(resp)
        if resp.finish_reason == agent_service_pb2.STOP:
            break
    # 排空后台收尾任务，避免泄漏到其它用例
    for _ in range(50):
        current = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks() if t is not current and not t.done()]
        if not pending:
            break
        await asyncio.wait(pending, timeout=1.0)
    return responses


# ---------------------------------------------------------------------------
# 1. stage 事件契约（词表 / 帧型 / trace 关联字段）
# ---------------------------------------------------------------------------


def test_stage_events_module_contract() -> None:
    """stage_events 模块：canonical 词表 + ledger/AgentStatus 映射 + 帧型契约。"""
    from app.orchestration.stage_events import (  # noqa: PLC0415
        CANONICAL_STAGES,
        STAGE_TO_AGENT_STATE,
        STAGE_TO_LEDGER_STAGE,
        build_stage_frame,
    )

    assert {"context", "retrieval", "decision", "tool", "waiting"} <= set(CANONICAL_STAGES)
    assert set(STAGE_TO_LEDGER_STAGE) == set(CANONICAL_STAGES)
    assert set(STAGE_TO_AGENT_STATE) == set(CANONICAL_STAGES)

    # 词表 → trace（run_ledger workflow_stage）1:1 映射，验收「stage 与 trace 匹配」的静态面
    assert STAGE_TO_LEDGER_STAGE["intake"] == "orchestration"
    assert STAGE_TO_LEDGER_STAGE["handoff"] == "orchestration"
    assert STAGE_TO_LEDGER_STAGE["context"] == "context"
    assert STAGE_TO_LEDGER_STAGE["retrieval"] == "retrieval"
    assert STAGE_TO_LEDGER_STAGE["decision"] == "routing"
    assert STAGE_TO_LEDGER_STAGE["tool"] == "tool"
    assert STAGE_TO_LEDGER_STAGE["waiting"] == "waiting"

    # 词表 → 既有 proto AgentStatus.State 对齐（不新增 proto 枚举）
    assert STAGE_TO_AGENT_STATE["retrieval"] == agent_service_pb2.AgentStatus.SEARCHING
    assert STAGE_TO_AGENT_STATE["tool"] == agent_service_pb2.AgentStatus.EXECUTING_TOOL
    assert STAGE_TO_AGENT_STATE["waiting"] == agent_service_pb2.AgentStatus.IDLE
    assert (
        STAGE_TO_AGENT_STATE["intake"]
        == STAGE_TO_AGENT_STATE["context"]
        == STAGE_TO_AGENT_STATE["decision"]
        == agent_service_pb2.AgentStatus.THINKING
    )

    frame = build_stage_frame(
        "retrieval",
        headline="正在检索资料",
        detail="document+memory",
        trace_id="trace-1",
        ledger_event_id="evt-1",
    )
    assert frame.WhichOneof("content") == "status_update"
    ux = json.loads(frame.metadata["ux_progress"])
    assert ux["stage"] == "retrieval"
    assert ux["headline"] == "正在检索资料"
    assert ux["detail"] == "document+memory"
    assert ux["is_blocked"] is False
    assert ux["ledger_event_id"] == "evt-1"
    assert ux["trace_id"] == "trace-1"
    # waiting 阶段必须带 is_blocked=True（等待用户侧动作）
    waiting = build_stage_frame(
        "waiting",
        headline="等待确认",
        detail="",
        trace_id="trace-1",
        ledger_event_id="evt-2",
    )
    assert json.loads(waiting.metadata["ux_progress"])["is_blocked"] is True


# ---------------------------------------------------------------------------
# 2. 深路径 500ms 首反馈：首个 stage 帧必须早于重上下文构建到达
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_stage_frame_beats_slow_context_build() -> None:
    """服务可知（校验+锁+会话态就绪）后，首个 stage 帧须 <500ms 到达，
    且早于重上下文构建（0.8s 慢桩模拟深路径 DB/画像/RAG 前置段）。"""
    events: list[str] = []
    orchestrator = _build_orchestrator(events, slow_context_seconds=0.8)

    first_frame_seen_at: list[float] = []

    async def timed_drive() -> list[Any]:
        request = agent_service_pb2.ChatRequest(
            request_id="e03_500ms",
            session_id="test_sess",
            user_id=str(uuid.uuid4()),
            message="帮我深度分析一下这个学期该怎么复习",
        )
        responses: list[Any] = []
        started = time.perf_counter()
        async for resp in orchestrator.process_stream(request):
            if not first_frame_seen_at:
                first_frame_seen_at.append(time.perf_counter() - started)
                events.append("first_frame")
            responses.append(resp)
            if resp.finish_reason == agent_service_pb2.STOP:
                break
        # 排空后台收尾任务
        for _ in range(50):
            current = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks() if t is not current and not t.done()]
            if not pending:
                break
            await asyncio.wait(pending, timeout=1.0)
        return responses

    with (
        patch("app.services.llm_service.llm_service.chat_stream_with_tools", AsyncMock()),
        patch("app.services.llm_service.llm_service.chat_json", AsyncMock(return_value={})),
    ):
        responses = await timed_drive()

    assert first_frame_seen_at, "流必须有首帧"
    elapsed = first_frame_seen_at[0]
    assert elapsed < 0.5, f"首帧应在服务可知后 500ms 内到达，实际 {elapsed:.3f}s"

    first = responses[0]
    assert first.WhichOneof("content") == "status_update", "首帧应是 stage 状态帧，而非等首个 token"
    ux = json.loads(first.metadata.get("ux_progress") or "{}")
    assert ux.get("stage") in {"intake", "handoff"}, f"首帧 stage 应为 intake/handoff，实际 {ux}"

    # 首帧必须早于重上下文构建完成（不等深路径前置段）
    assert events.index("first_frame") < events.index(
        "context_build_finished"
    ), f"首帧应先于上下文构建完成，事件序错误: {events}"


# ---------------------------------------------------------------------------
# 3. 深路径 stage 序列 + trace 匹配
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_path_stage_sequence_matches_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    """深路径下发 stage 序列须为 intake→context→decision→retrieval，
    且每帧 ledger_event_id 都能回查到 workflow_stage 匹配的 RunLedger 事件。"""
    from app.orchestration.stage_events import STAGE_TO_LEDGER_STAGE  # noqa: PLC0415

    events: list[str] = []
    orchestrator = _build_orchestrator(events)
    recorded = _spy_run_ledger(monkeypatch)

    with (
        patch("app.services.llm_service.llm_service.chat_stream_with_tools", AsyncMock()),
        patch("app.services.llm_service.llm_service.chat_json", AsyncMock(return_value={})),
    ):
        responses = await _drive(orchestrator, request_id="e03_seq")

    stage_payloads = _extract_stage_frames(responses)
    stage_names = [p["stage"] for p in stage_payloads]

    # 深路径阶段序列（卡片 work#1 的五个阶段里，orchestrator 面负责前四个）
    expected_prefix = ["intake", "context", "decision", "retrieval"]
    assert stage_names[: len(expected_prefix)] == expected_prefix, f"stage 序列应以前四阶段开头，实际 {stage_names}"

    # trace 匹配：每个带 ledger_event_id 的 stage 帧都能回查到同 id 事件，
    # 且其 workflow_stage 与词表映射 1:1
    events_by_id = {e.get("event_id"): e for e in recorded}
    correlated = [p for p in stage_payloads if p.get("ledger_event_id")]
    assert correlated, "stage 帧应携带 ledger_event_id 用于 trace 关联"
    for payload in correlated:
        ledger_event = events_by_id.get(payload["ledger_event_id"])
        assert (
            ledger_event is not None
        ), f"stage={payload['stage']} 的 ledger_event_id={payload['ledger_event_id']} 无对应 RunLedger 事件"
        expected_stage = STAGE_TO_LEDGER_STAGE[payload["stage"]]
        assert ledger_event.get("workflow_stage") == expected_stage, (
            f"stage={payload['stage']} 应映射 workflow_stage={expected_stage}，"
            f"实际 {ledger_event.get('workflow_stage')}"
        )

    # retrieval 阶段真实发生在文档检索前（不是事后补发）
    assert "document_retrieval_started" in events
    assert any(p["stage"] == "retrieval" for p in stage_payloads)


@pytest.mark.asyncio
async def test_early_ack_frame_is_ledger_correlated(monkeypatch: pytest.MonkeyPatch) -> None:
    """早期 ack 帧升级为 stage 帧：携带 ledger_event_id（关联 run_started）。"""
    events: list[str] = []
    orchestrator = _build_orchestrator(events)
    recorded = _spy_run_ledger(monkeypatch)

    with (
        patch("app.services.llm_service.llm_service.chat_stream_with_tools", AsyncMock()),
        patch("app.services.llm_service.llm_service.chat_json", AsyncMock(return_value={})),
    ):
        responses = await _drive(orchestrator, request_id="e03_ack")

    early = [
        r
        for r in responses
        if r.WhichOneof("content") == "status_update"
        and json.loads(r.metadata.get("ux_progress") or "{}").get("stage") in {"intake", "handoff"}
    ]
    frame_dump = [
        (
            r.WhichOneof("content"),
            json.loads(r.metadata.get("ux_progress") or "{}").get("stage"),
        )
        for r in responses
    ]
    assert early, f"应存在 intake/handoff 早期确认帧，实际帧序列: {frame_dump}"
    ux = json.loads(early[0].metadata["ux_progress"])
    assert ux.get("ledger_event_id"), "早期确认帧应携带 ledger_event_id"
    assert ux.get("trace_id"), "早期确认帧应携带 trace_id"
    matched = [e for e in recorded if e.get("event_id") == ux["ledger_event_id"]]
    assert matched, "ledger_event_id 应能回查到 RunLedger 事件"


# ---------------------------------------------------------------------------
# 4. reasoning_content 原文绝不外泄（负向守卫）
# ---------------------------------------------------------------------------

_COT_MARKER = "SECRET_CHAIN_OF_THOUGHT_DO_NOT_SHOW"


@pytest.mark.asyncio
async def test_reasoning_chunks_never_leak_into_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    """模型流先吐 reasoning 块（含 CoT 标记原文）时，任何下发帧（delta/
    status/details/metadata 序列化）都不得包含该原文。"""
    from types import SimpleNamespace

    from app.agents.standard_workflow import generation_node
    from app.orchestration.statechart_engine import WorkflowState

    captured: list[agent_service_pb2.ChatResponse] = []

    async def stream_callback(resp: agent_service_pb2.ChatResponse) -> None:
        captured.append(resp)

    class _ReasoningFakeLLM:
        agent_role = "generation"

        def is_thinking_mode(self):  # noqa: ANN201
            return True

        def get_current_selection(self):  # noqa: ANN201
            return SimpleNamespace(
                model_key="fake_thinking",
                is_fallback=False,
                estimated_cost_per_1k=0.0001,
                config=SimpleNamespace(
                    model_name="fake-thinking-model",
                    provider=SimpleNamespace(value="dashscope"),
                    tier=SimpleNamespace(value="max"),
                ),
            )

        async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
            yield SimpleNamespace(
                type="reasoning",
                content=None,
                reasoning_content=f"{_COT_MARKER} 用户其实想要一份复习计划，我应该先……",
            )
            yield SimpleNamespace(type="reasoning", content=None, reasoning_content=f"{_COT_MARKER} 续")
            yield SimpleNamespace(type="text", content="这是给你的复习建议。")

        async def chat(self, messages, temperature=0.35):
            return "这是给你的复习建议。"

    fake_llm = _ReasoningFakeLLM()
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service_for_tier",
        AsyncMock(return_value=fake_llm),
    )
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service",
        AsyncMock(return_value=fake_llm),
    )
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *a, **k: "SYSTEM")

    state = WorkflowState(
        messages=[{"role": "user", "content": "帮我深度分析一下这个学期该怎么复习"}],
        context_data={
            "chat_mode": "standard",
            "reasoning_mode": "balanced",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
            "stream_callback": stream_callback,
        },
    )

    new_state = await generation_node(state)

    debug_dump = [
        (r.WhichOneof("content"), (r.delta if r.WhichOneof("content") == "delta" else r.status_update.details))
        for r in captured
    ]
    assert captured, (
        "思考模型流应至少产生状态/进度帧；"
        f"next_step={getattr(new_state, 'next_step', None)}, captured={debug_dump}, "
        f"context_keys={sorted(new_state.context_data.keys())}"
    )
    for resp in captured:
        serialized = str(resp).replace("\\n", " ")
        assert (
            _COT_MARKER not in serialized
        ), "reasoning_content 原文不得出现在任何下发帧（delta/status/details/metadata）"
    # 正常文本照常下发（守卫不得误伤主链）：首 flush 帧是 delta+status 合并帧
    # （proto oneof 保 status），正文最终落在 state.messages 与后续帧/终帧。
    assistant_messages = [m for m in new_state.messages if m.get("role") == "assistant"]
    assert assistant_messages and "复习建议" in (
        assistant_messages[-1].get("content") or ""
    ), "正常文本应照常进入回复主链（state.messages），守卫不得误伤"


# ---------------------------------------------------------------------------
# 5. tool / waiting 阶段（DAG 执行观察者 + 确认门）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dag_observer_emits_tool_stage_and_confirmation_waiting() -> None:
    """DAG layer_start 帧 = tool stage（带 ledger 关联）；确认门状态 = waiting
    stage（is_blocked=true）。"""
    from app.agents.standard_workflow import (  # noqa: PLC0415
        build_dag_execution_observer,
        emit_tool_step_status,
    )
    from app.orchestration.run_ledger import RunLedgerRecorder
    from app.orchestration.stage_events import STAGE_TO_LEDGER_STAGE  # noqa: F401

    captured: list[agent_service_pb2.ChatResponse] = []

    async def stream_callback(resp: agent_service_pb2.ChatResponse) -> None:
        captured.append(resp)

    ledger = RunLedgerRecorder(
        trace_id="trace-dag",
        session_id="sess-dag",
        redis_client=None,
        stream_callback=stream_callback,
    )

    observer = build_dag_execution_observer(stream_callback=stream_callback, run_ledger=ledger)
    await observer(
        {
            "event": "layer_start",
            "layer_number": 1,
            "total_layers": 2,
            "tool_names": ["create_task", "search_notes"],
        }
    )

    tool_frames = [
        r
        for r in captured
        if r.WhichOneof("content") == "status_update"
        and json.loads(r.metadata.get("ux_progress") or "{}").get("stage") == "tool"
    ]
    assert tool_frames, "DAG layer_start 应产生 tool stage 帧"
    ux = json.loads(tool_frames[0].metadata["ux_progress"])
    assert ux.get("ledger_event_id"), "tool stage 帧应携带 ledger_event_id"
    assert tool_frames[0].status_update.state == agent_service_pb2.AgentStatus.EXECUTING_TOOL

    # 确认门步骤 → waiting stage（不是「执行失败」）
    captured.clear()
    await emit_tool_step_status(
        stream_callback=stream_callback,
        run_ledger=ledger,
        tool_name="delete_plan",
        success=False,
        error_type="ConfirmationRequired",
    )
    waiting_frames = [
        r
        for r in captured
        if r.WhichOneof("content") == "status_update"
        and json.loads(r.metadata.get("ux_progress") or "{}").get("stage") == "waiting"
    ]
    assert waiting_frames, "确认门步骤应产生 waiting stage 帧"
    waiting_ux = json.loads(waiting_frames[0].metadata["ux_progress"])
    assert waiting_ux.get("is_blocked") is True
    assert waiting_frames[0].status_update.state == agent_service_pb2.AgentStatus.IDLE
    assert waiting_ux.get("ledger_event_id"), "waiting stage 帧应携带 ledger_event_id"

    # 非 waiting 的常规步骤状态保持既有行为（成功 → IDLE + 文案，不携带 stage 词表）
    captured.clear()
    await emit_tool_step_status(
        stream_callback=stream_callback,
        run_ledger=ledger,
        tool_name="create_task",
        success=True,
        error_type=None,
    )
    assert captured, "常规步骤应照常产生状态帧"
    assert captured[0].status_update.state == agent_service_pb2.AgentStatus.IDLE
