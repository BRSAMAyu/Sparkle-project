"""演示缺陷 ❌#6 · done 尾延迟治理的时序契约测试.

背景（docs/competition/大创市赛/演示路径盘点_2026-09-20.md §❌#6）：
末个内容 delta 与 done 之间实测 120-145s。收尾侧修复（B）：轮末记忆写入
与情绪落库不是最终帧的构成成分——移入 done 之后的 fire-and-forget 后台
任务；最终 STOP 帧在收尾轻量步骤后立即 yield（网关收到 STOP 即发 done）。

时序断言：事件序必须是「last delta → STOP 帧 → 后台收尾（记忆/情绪）」。
旧代码（STOP 帧之前同步写记忆）下本测试必红。
"""

from __future__ import annotations

import contextlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import STATE_DONE
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.schemas import RouteDecision


def _build_orchestrator(events: list[str]) -> ChatOrchestrator:
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
    orchestrator._build_full_context = AsyncMock(return_value=({}, None, False, {}, {"messages": []}, None))
    orchestrator._detect_session_feedback = AsyncMock(return_value=(None, None, None))
    orchestrator._apply_cohort_to_session_feedback_signal = MagicMock(
        side_effect=lambda signal, cohort: signal
    )
    orchestrator._maybe_enqueue_perceptible_insight = AsyncMock(return_value=None)
    orchestrator._maybe_enqueue_understanding_depth = AsyncMock(return_value=None)
    orchestrator._drain_system_updates = AsyncMock(
        return_value=([], [], [], [], None, None, {
            "proactive_opening_message": "",
            "pending_observation": "",
            "post_adaptation_question": "",
        })
    )
    orchestrator._check_sufficiency = AsyncMock(return_value=(False, "chat"))
    orchestrator._check_goal_quality = AsyncMock(return_value=False)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator._prepare_runtime_context = AsyncMock(return_value=(None, lambda *args, **kwargs: None))
    orchestrator._notify_pending_milestone_proposals = AsyncMock(return_value=None)
    orchestrator._apply_context_focus_overlay = AsyncMock(
        side_effect=lambda **kwargs: kwargs["user_context_payload"]
    )
    orchestrator._apply_dual_core_routing = AsyncMock(
        return_value=RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low")
    )
    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (kwargs["route_decision"], None, None, False)
    )
    orchestrator._cache_response = AsyncMock(return_value=True)
    orchestrator._persist_assistant_message = AsyncMock(return_value=None)
    orchestrator._record_decision = AsyncMock(return_value=None)
    orchestrator._cleanup = AsyncMock(return_value=None)

    async def execute_graph(*, result_holder, **kwargs):
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

    # 后台收尾的桩：独立会话 CM + 可观测的记忆/情绪写入
    @contextlib.asynccontextmanager
    async def fake_finalize_session():
        yield MagicMock()

    async def fake_memory(**kwargs):
        events.append("finalize_memory")

    async def fake_mood(**kwargs):
        events.append("finalize_mood")

    orchestrator._create_finalize_db_session = fake_finalize_session
    orchestrator._write_turn_end_episodic_memory = fake_memory
    orchestrator._maybe_upsert_session_mood = fake_mood
    return orchestrator


@pytest.mark.asyncio
async def test_stop_frame_reaches_consumer_before_turn_finalize():
    """done 帧（STOP）必须先于轮末记忆/情绪收尾到达消费者."""
    events: list[str] = []
    with patch("app.services.llm_service.llm_service.chat_stream_with_tools", AsyncMock()), patch(
        "app.services.llm_service.llm_service.chat_json", AsyncMock(return_value={})
    ):
        orchestrator = _build_orchestrator(events)
        request = agent_service_pb2.ChatRequest(
            request_id="tail_req",
            session_id="test_sess",
            user_id=str(uuid.uuid4()),
            message="Hi",
        )

        responses = []
        async for resp in orchestrator.process_stream(request):
            responses.append(resp)
            if resp.finish_reason == agent_service_pb2.STOP:
                events.append("stop_seen")

        # 让后台收尾任务真正跑完（排除当前测试任务，避免自等死锁）
        import asyncio

        for _ in range(50):
            current = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks() if t is not current and not t.done()]
            if not pending:
                break
            await asyncio.wait(pending, timeout=1.0)

    assert any(r.HasField("delta") for r in responses), "应有内容 delta"
    assert any(r.finish_reason == agent_service_pb2.STOP for r in responses), "应有 STOP 终帧"
    assert "delta" in events and "stop_seen" in events
    assert "finalize_memory" in events, "轮末记忆写入应作为后台任务执行"
    # 核心时序断言：记忆/情绪写入发生在 STOP 帧被消费者看到之后
    assert events.index("finalize_memory") > events.index("stop_seen"), f"事件序错误: {events}"
    if "finalize_mood" in events:
        assert events.index("finalize_mood") > events.index("stop_seen"), f"事件序错误: {events}"
    # 收尾不得与 delta 倒挂
    assert events.index("finalize_memory") > events.index("delta")


@pytest.mark.asyncio
async def test_error_path_still_writes_memory_inline():
    """错误路径（无 done 语义）保留同步记忆写入，行为不回退."""
    events: list[str] = []
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.ping.return_value = True

    with patch("app.services.llm_service.llm_service.chat_stream_with_tools", AsyncMock()), patch(
        "app.services.llm_service.llm_service.chat_json", AsyncMock(return_value={})
    ):
        orchestrator = _build_orchestrator(events)
        orchestrator._db = mock_db
        orchestrator._redis = mock_redis
        # 重新挂会走错误路径的桩
        memory_calls: list[dict] = []

        async def fake_memory(**kwargs):
            memory_calls.append(kwargs)

        orchestrator._write_turn_end_episodic_memory = fake_memory

        async def failing_execute_graph(*, result_holder, **kwargs):
            raise RuntimeError("graph exploded")
            yield  # pragma: no cover

        orchestrator._execute_graph = failing_execute_graph

        request = agent_service_pb2.ChatRequest(
            request_id="tail_err",
            session_id="test_err_sess",
            user_id=str(uuid.uuid4()),
            message="Hi",
        )
        responses = [resp async for resp in orchestrator.process_stream(request)]

    assert any(r.finish_reason == agent_service_pb2.ERROR for r in responses)
    assert len(memory_calls) == 1, "错误路径应同步写一次轮末记忆"


def _unused_settings_guard():
    # 确认 settings 含 ❌#6 的部署开关（A2），供配置面回归
    assert hasattr(settings, "ENABLE_GENERATION_REVIEW")
    assert STATE_DONE is not None
