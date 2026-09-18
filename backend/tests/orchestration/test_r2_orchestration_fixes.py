"""R2 修复波回归测试 — 编排运行时切片。

对应复审报告 round2/01-r2-engine-orchestration.md：
- R2-01 (P1): 超时/断连取消只杀 task_manager 包装任务，内层 graph 协程继续跑。
    红断言：断连后 inner_finished 必须为 False，且内层必须观测到 CancelledError。
- R2-02: planner 纯超时不进熔断计数，且 fallback 计划会把 on_success 抵消掉。
    红断言：纯超时必须记录 on_failure("timeout...")，且不得触发 on_success。
- R2-03: 会话 FSM 无转移校验（36 对全接受）。
    红断言：终态非法出边（DONE→活跃态、FAILED→DONE）被拒绝；合法生命周期与恢复路径仍放行。
- R2-04: loguru `exc_info=` 无效用法导致堆栈不落日志。
    红断言：orchestration 包源码不得再出现 exc_info。
- R2-05: task_manager 单例跨事件循环 spawn 抛 "PriorityQueue is bound to a different event loop"。
    红断言：同一实例在第二个全新事件循环上 spawn 必须成功。
"""

from __future__ import annotations

import asyncio
import importlib
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.task_manager import BackgroundTaskManager
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.state_manager import (
    STATE_DONE,
    STATE_FAILED,
    STATE_GENERATING,
    STATE_INIT,
    STATE_THINKING,
    STATE_TOOL_CALLING,
    FSMState,
    SessionStateManager,
)
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.schemas import RouteDecision
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _MemoryRedis,
    _install_import_stubs,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)


# ---------------------------------------------------------------------------
# R2-01: 取消必须传播到内层 graph 协程
# ---------------------------------------------------------------------------


class _DisconnectGraph:
    """模拟真实图谱：先产出部分输出，随后需要一段时间才能自然跑完。"""

    def __init__(self, queue: asyncio.Queue) -> None:
        self.queue = queue
        self.inner_finished = False
        self.inner_cancelled = False

    async def invoke(self, state, **kwargs):
        await asyncio.sleep(0.05)
        self.queue.put_nowait(agent_service_pb2.ChatResponse(delta="partial"))
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            self.inner_cancelled = True
            raise
        self.inner_finished = True
        return state


@pytest.mark.asyncio
async def test_r2_01_disconnect_cancel_stops_inner_graph():
    """客户端断连（GeneratorExit → 包装任务 cancel）后内层 graph 不得继续执行。"""
    _install_import_stubs()
    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")

    queue: asyncio.Queue = asyncio.Queue()
    graph = _DisconnectGraph(queue)
    engine_stub = SimpleNamespace(graph=graph, token_tracker=None)

    gen = execution_engine_module.ExecutionEngineMixin._execute_graph(
        engine_stub,
        state=WorkflowState(),
        user_id="user-r2-01",
        queue=queue,
        result_holder={},
    )
    first = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
    assert first.HasField("delta"), "前置条件：应先消费到一条已产出的 delta"

    # 模拟断连：关闭生成器触发 _execute_graph 的 GeneratorExit 出口
    await gen.aclose()

    # 留足时间：若取消未传播，内层将在 0.5s 后自然跑完（旧实现的失败模式）
    await asyncio.sleep(1.0)

    assert graph.inner_finished is False, "断连后内层 graph 协程不得继续跑完（烧 token/写共享状态）"
    assert graph.inner_cancelled is True, "取消必须传播到内层协程"


@pytest.mark.asyncio
async def test_r2_01_task_manager_cancel_propagates_to_inner_coroutine():
    """task_manager 层面：cancel 包装任务必须取消内层协程并等待其退出。"""
    tm = BackgroundTaskManager()
    started = asyncio.Event()
    inner_finished = False
    inner_cancelled = False

    async def inner():
        nonlocal inner_finished, inner_cancelled
        started.set()
        try:
            await asyncio.sleep(0.4)
        except asyncio.CancelledError:
            inner_cancelled = True
            raise
        inner_finished = True

    handle = await tm.spawn(inner(), task_name="r2_01_graph")
    await asyncio.wait_for(started.wait(), timeout=2.0)
    handle.cancel()

    # > 0.4s：旧实现中内层协程会照常跑完
    await asyncio.sleep(1.0)

    assert inner_finished is False, "cancel 包装任务后内层协程不得跑完"
    assert inner_cancelled is True, "内层协程必须收到 CancelledError"


@pytest.mark.asyncio
async def test_r2_01_task_manager_spawn_still_returns_results_and_errors():
    """行为保持：正常结果与异常仍通过包装任务返回。"""
    tm = BackgroundTaskManager()

    async def ok():
        return 42

    async def boom():
        raise ValueError("r2-01-boom")

    handle_ok = await tm.spawn(ok(), task_name="ok")
    assert await asyncio.wait_for(handle_ok, timeout=2.0) == 42

    handle_boom = await tm.spawn(boom(), task_name="boom")
    with pytest.raises(ValueError, match="r2-01-boom"):
        await asyncio.wait_for(handle_boom, timeout=2.0)


# ---------------------------------------------------------------------------
# R2-02: planner 纯超时计入熔断
# ---------------------------------------------------------------------------


def _plan_and_validate_kwargs(stream_callback, session_id: str):
    return {
        "user_message": "帮我做复习计划",
        "user_id": str(uuid.uuid4()),
        "session_id": session_id,
        "active_db": None,
        "plan_id": None,
        "conversation_context": None,
        "plan_context": None,
        "stream_callback": stream_callback,
        "user_context_payload": {},
        "orchestration_trace": None,
    }


@pytest.mark.asyncio
async def test_r2_02_planner_pure_timeout_counts_into_breaker(orchestrator_factory, monkeypatch):  # noqa: F811
    """纯超时必须记录熔断失败；fallback 计划不得触发 on_success 抵消失败计数。"""
    _install_import_stubs()
    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    monkeypatch.setattr(execution_engine_module, "_LANGGRAPH_PLANNER_TIMEOUT_SECONDS", 0.05)

    orchestrator, _, _ = orchestrator_factory()
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, None))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.on_success = AsyncMock(return_value=None)
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)

    async def _hanging_plan(*args, **kwargs):
        await asyncio.sleep(30)

    orchestrator.lang_graph_planner.plan = _hanging_plan
    orchestrator.lang_graph_planner.build_fallback_plan = MagicMock(
        return_value=SimpleNamespace(
            plan_id="plan-r2-02",
            tool_calls=[],
            confidence=0.4,
            rationale="Planner timeout, synthesized fallback",
            collaboration_mode="single",
            agents_involved=[],
            risk_flags=[],
        )
    )
    orchestrator.lang_graph_planner.get_plan_summary = MagicMock(return_value="summary")
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(
        return_value=SimpleNamespace(snapshot_id="snap-r2-02")
    )
    orchestrator.version_conflict_service.check_all_conflicts = AsyncMock(
        return_value=SimpleNamespace(has_conflict=False)
    )
    orchestrator.grounding_validator.preflight_check = AsyncMock(
        return_value={"is_ready": True, "blocked_by": []}
    )

    deltas: list[str] = []

    async def stream_callback(response) -> None:
        if response.HasField("delta"):
            deltas.append(response.delta)

    state = WorkflowState()
    decision, plan, _snapshot, should_return = await orchestrator._plan_and_validate(
        route_decision=RouteDecision(execution_mode="langgraph", reason="complex", risk_level="low"),
        state=state,
        **_plan_and_validate_kwargs(stream_callback, "sess-r2-02"),
    )

    assert should_return is False
    assert decision.execution_mode == "langgraph", "纯超时应走 fallback 计划，而非 direct 降级"
    assert plan is not None

    orchestrator.langgraph_breaker.on_failure.assert_awaited_once()
    failure_reason = orchestrator.langgraph_breaker.on_failure.await_args.args[0]
    assert "timeout" in str(failure_reason), "超时必须以 timeout 原因计入熔断失败"
    orchestrator.langgraph_breaker.on_success.assert_not_awaited(), (
        "fallback 计划成功不得抵消 planner 超时失败（否则 6 连超时 failure_count=0）"
    )


# ---------------------------------------------------------------------------
# R2-03: 会话 FSM 转移校验
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2_03_invalid_terminal_transitions_rejected():
    """终态非法出边必须被拒绝且状态保持不变。"""
    sm = SessionStateManager(redis_client=_MemoryRedis())

    done_sid = "sess-r2-03-done"
    assert await sm.update_state(done_sid, STATE_DONE) is True  # 新会话创建不校验
    assert await sm.update_state(done_sid, STATE_THINKING) is False, "DONE→THINKING 必须拒绝"
    assert (await sm.load_state(done_sid)).state == STATE_DONE
    assert await sm.update_state(done_sid, STATE_GENERATING) is False, "DONE→GENERATING 必须拒绝"
    assert await sm.update_state(done_sid, STATE_TOOL_CALLING) is False, "DONE→TOOL_CALLING 必须拒绝"

    failed_sid = "sess-r2-03-failed"
    assert await sm.update_state(failed_sid, STATE_FAILED) is True
    assert await sm.update_state(failed_sid, STATE_DONE) is False, "FAILED→DONE 必须拒绝（掩盖失败）"
    assert (await sm.load_state(failed_sid)).state == STATE_FAILED


@pytest.mark.asyncio
async def test_r2_03_valid_lifecycle_and_recovery_transitions_accepted():
    """合法生命周期、新回合重置与失败重试路径仍必须放行。"""
    sm = SessionStateManager(redis_client=_MemoryRedis())
    sid = "sess-r2-03-lifecycle"
    for next_state in [STATE_INIT, STATE_THINKING, STATE_TOOL_CALLING, STATE_THINKING, STATE_GENERATING, STATE_DONE]:
        assert await sm.update_state(sid, next_state) is True, f"{next_state} 合法转移被误拒"
        assert (await sm.load_state(sid)).state == next_state

    # 新回合：DONE → INIT（生产路径先写 INIT 再推进）
    assert await sm.update_state(sid, STATE_INIT) is True
    assert await sm.update_state(sid, STATE_DONE) is True

    # 失败重试：FAILED → 活跃态合法
    failed_sid = "sess-r2-03-retry"
    assert await sm.update_state(failed_sid, STATE_INIT) is True
    assert await sm.update_state(failed_sid, STATE_FAILED) is True
    assert await sm.update_state(failed_sid, STATE_THINKING) is True
    assert await sm.update_state(failed_sid, STATE_FAILED) is True
    # 同态幂等重写合法
    assert await sm.update_state(failed_sid, STATE_FAILED) is True
    # 异常出口：INIT → FAILED 合法（超时/通用异常出口）
    assert await sm.update_state(failed_sid, STATE_INIT) is True
    assert await sm.update_state(failed_sid, STATE_FAILED) is True


# ---------------------------------------------------------------------------
# R2-04: loguru exc_info 无效用法清零
# ---------------------------------------------------------------------------


def test_r2_04_orchestration_source_has_no_exc_info():
    """loguru 的 logger 不支持 exc_info=（kwarg 被当 extra 吞掉，堆栈不落日志）。

    orchestration 包内不得再出现 exc_info；需要堆栈时使用 logger.opt(exception=...).
    """
    import app.orchestration as orchestration_pkg

    pkg_dir = Path(orchestration_pkg.__file__).parent
    offenders: list[str] = []
    for path in sorted(pkg_dir.glob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "exc_info" in line:
                offenders.append(f"{path.name}:{lineno}")
    assert offenders == [], (
        "loguru 不支持 exc_info=，堆栈会静默丢失；请改用 logger.opt(exception=...).error(...)"
        f"，位置：{offenders}"
    )


# ---------------------------------------------------------------------------
# R2-05: task_manager 跨事件循环 spawn
# ---------------------------------------------------------------------------


def test_r2_05_task_manager_spawn_survives_fresh_event_loop():
    """同一 BackgroundTaskManager 实例在第二个全新事件循环上必须继续可用。

    旧实现：单例的 PriorityQueue/worker 绑定首个事件循环，第二个循环上
    worker 抛 RuntimeError("... is bound to a different event loop") 崩溃
    （asyncio/mixins.py:20），异常只在 GC 时以 unretrieved 形式浮现。
    """
    tm = BackgroundTaskManager()

    async def scenario(value: int) -> int:
        async def payload() -> int:
            return value

        handle = await tm.spawn(payload(), task_name=f"r2_05_loop_{value}")
        result = await asyncio.wait_for(handle, timeout=3.0)
        # 让 worker 有机会进入空队列等待：旧实现的队列绑定了首个循环，
        # 新循环上的 worker 在此处抛 RuntimeError 并死亡
        await asyncio.sleep(0.05)
        worker = getattr(tm, "_queue_worker_task", None)
        if worker is None:  # 新实现：worker 挂在 per-loop runtime 上
            worker = tm._loop_runtime().queue_worker_task
        if worker is not None and worker.done():
            exc = worker.exception()  # 主动取回，避免 GC 告警
            if exc is not None:
                raise RuntimeError(f"queue worker crashed on loop {value}: {exc!r}") from exc
        return result

    assert asyncio.run(scenario(1)) == 1
    assert asyncio.run(scenario(2)) == 2, "第二个事件循环上 spawn 不得失败、worker 不得崩溃"


# ---------------------------------------------------------------------------
# 重构边界加固：worker 对"内层任务被外部取消"的韧性
# （graceful_shutdown 会 cancel runtime.tasks 里的内层任务，而 worker 仍在
#  await asyncio.wait —— 若该路径把 CancelledError 漏出 except Exception，
#  worker 会整个死亡，后续 spawn 全部挂起）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2_05_worker_survives_inner_task_external_cancel():
    """内层任务被外部取消（如 graceful_shutdown）时 worker 必须存活并继续服务。"""
    tm = BackgroundTaskManager()

    async def hang():
        await asyncio.sleep(30)

    handle1 = await tm.spawn(hang(), task_name="r2_05_worker_resilience")
    # 让 worker 完成出队并创建内层任务
    await asyncio.sleep(0.15)
    runtime = tm._loop_runtime()
    inner_tasks = [
        t for key, t in runtime.tasks.items()
        if key.startswith("r2_05_worker_resilience") and not key.startswith("queued_")
    ]
    assert len(inner_tasks) == 1, "前置条件：内层受管任务应已创建"
    inner_tasks[0].cancel()

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(handle1, timeout=3.0)

    # worker 必须仍然活着：后续 spawn 正常出结果
    async def payload() -> str:
        return "still-alive"

    handle2 = await tm.spawn(payload(), task_name="r2_05_worker_resilience_after")
    assert await asyncio.wait_for(handle2, timeout=3.0) == "still-alive"
    worker = runtime.queue_worker_task
    assert worker is not None and not worker.done(), "queue worker 不得因内层任务取消而退出"


@pytest.mark.asyncio
async def test_r2_01_worker_done_callback_binding_no_spurious_cancel():
    """result_future 回调经 call_soon 异步触发，闭包不得共享每轮重新赋值的变量。

    旧实现：worker 用 `lambda _f: caller_gone.set()` 注册回调——lambda 捕获的是
    每轮迭代被重新赋值的同一变量单元格。第 N 项 set_result 的回调延迟触发时，
    worker 已进入第 N+1 轮迭代，旧回调 set 的是新项的事件 → caller-gone 分支
    误取消健康运行中的内层协程，且不回填 result_future → wrapper 永久挂起，
    gather 死等（并发 >=2 时 100% 复现：0→1、2→3、4→5 …交错取消）。
    """
    tm = BackgroundTaskManager()

    async def slow():
        await asyncio.sleep(0.05)
        return "done"

    handles = [await tm.spawn(slow(), task_name=f"r2_01_stale_cb_{i}") for i in range(6)]
    results = await asyncio.wait_for(asyncio.gather(*handles), timeout=5.0)
    assert results == ["done"] * 6, "并发 spawn 不得出现误取消或 wrapper 挂起"
