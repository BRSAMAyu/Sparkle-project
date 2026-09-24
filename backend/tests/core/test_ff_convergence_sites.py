"""FF-CONVERGENCE（wt310）：抽样点位回归——迁移后语义保持 + FF 泄漏可见性。

点位来源：wt294 P1-3 清单 / wt299 执行建议（migration 后的抽样回归）：
- auth_audit_service.schedule_log（审计写，最高优先级）
- aurora.privacy._resolve_mode_safe（隐私模式刷新，最高优先级）
- llm_monitoring.monitor_llm_call（ACTIVE_TASKS gauge 漂移）
- graph_sync_worker.stop（关停 cancel/drain 语义，wt294 P1-4）
- community_service._record_community_signal（信号采集）
- tool_history / achievement after-commit 钩子（事件发布）

全部离线：async stub / fake session，零网络零 DB。
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.background_tasks import tracked_task_count


async def _settle() -> None:
    """让已完成任务的 done-callback 跑完（call_soon 一拍）。"""
    for _ in range(3):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# auth_audit_service.schedule_log
# ---------------------------------------------------------------------------


async def test_auth_audit_schedule_log_runs_tracked_and_drains():
    from app.core.auth_audit_service import AuthAuditService

    calls: list[dict[str, Any]] = []
    service = AuthAuditService()

    async def fake_log_event(**kwargs: Any) -> None:
        calls.append(kwargs)

    before = tracked_task_count()
    original = service.log_event
    service.log_event = fake_log_event  # type: ignore[method-assign]
    try:
        service.schedule_log(action="login_failed", user_id="u1", metadata={"x": 1})
        await _settle()
    finally:
        service.log_event = original  # type: ignore[method-assign]

    assert len(calls) == 1  # FF 任务真的执行了（不是被 GC 丢掉）
    assert calls[0]["action"] == "login_failed"
    assert calls[0]["user_id"] == "u1"
    await _settle()
    assert tracked_task_count() == before  # 执行完即从追踪集 discard


# ---------------------------------------------------------------------------
# aurora.privacy._resolve_mode_safe
# ---------------------------------------------------------------------------


async def test_privacy_mode_refresh_schedules_tracked_task(monkeypatch):
    import app.aurora.privacy as privacy

    refreshed = asyncio.Event()
    monkeypatch.setattr(privacy, "_MODE_CACHE", {"value": None, "expires_at": 0.0, "settings_seed": None})

    async def fake_refresh() -> None:
        refreshed.set()

    monkeypatch.setattr(privacy, "_refresh_mode_cache_async", fake_refresh)

    before = tracked_task_count()
    mode = privacy._resolve_mode_safe()  # running loop 分支：调度后台刷新、立即返回
    assert mode == privacy._resolve_settings_mode()  # 冷启动回退 settings 值，不阻塞
    await asyncio.wait_for(refreshed.wait(), timeout=1.0)  # 刷新任务真的跑（不被 GC）
    await _settle()
    assert tracked_task_count() == before


# ---------------------------------------------------------------------------
# llm_monitoring.monitor_llm_call（ACTIVE_TASKS gauge 漂移）
# ---------------------------------------------------------------------------


async def test_llm_monitor_active_tasks_gauge_returns_to_baseline_success():
    from app.core.llm_monitoring import ACTIVE_TASKS, LLMMonitor

    @LLMMonitor.monitor_llm_call(model="test-model", endpoint="chat")
    async def call() -> dict[str, Any]:
        return {"ok": True}

    baseline = ACTIVE_TASKS._value.get()
    await call()
    await asyncio.sleep(0.05)  # 递减协程含真实 1ms timer，需真实时间推进
    assert ACTIVE_TASKS._value.get() == baseline  # 递减任务必达：无 gauge 漂移


async def test_llm_monitor_active_tasks_gauge_returns_to_baseline_error():
    from app.core.llm_monitoring import ACTIVE_TASKS, LLMMonitor

    @LLMMonitor.monitor_llm_call(model="test-model", endpoint="chat")
    async def call() -> dict[str, Any]:
        raise RuntimeError("llm down")

    baseline = ACTIVE_TASKS._value.get()
    with pytest.raises(RuntimeError, match="llm down"):
        await call()
    await asyncio.sleep(0.05)  # 递减协程含真实 1ms timer
    assert ACTIVE_TASKS._value.get() == baseline  # 异常路径同样不漂移


# ---------------------------------------------------------------------------
# graph_sync_worker：关停 cancel/drain 语义（wt294 P1-4）
# ---------------------------------------------------------------------------


async def test_graph_sync_worker_stop_cancels_consume_task():
    from app.workers.graph_sync_worker import GraphSyncWorker

    worker = GraphSyncWorker.__new__(GraphSyncWorker)  # 与既有测试同款：跳过 __init__
    worker.running = True
    started = asyncio.Event()

    async def dummy_consume() -> None:
        started.set()
        await asyncio.sleep(30)

    from app.core.background_tasks import spawn_tracked

    worker._consume_task = spawn_tracked(dummy_consume(), name="graph_sync_worker.consume")
    consume_task = worker._consume_task
    await started.wait()
    await worker.stop()
    assert worker.running is False
    assert worker._consume_task is None
    assert consume_task is not None and consume_task.cancelled()  # 关停真正 cancel，不再只翻 flag


async def test_graph_sync_worker_stop_is_noop_without_task():
    from app.workers.graph_sync_worker import GraphSyncWorker

    worker = GraphSyncWorker.__new__(GraphSyncWorker)
    worker.running = True
    worker._consume_task = None
    await worker.stop()  # 无任务也不抛
    assert worker.running is False


# ---------------------------------------------------------------------------
# community_service._record_community_signal
# ---------------------------------------------------------------------------


async def test_community_signal_record_runs_tracked(monkeypatch):
    import app.services.community_service as community

    calls: list[dict[str, Any]] = []

    class FakeCollector:
        def __init__(self, redis: Any) -> None:
            self.redis = redis

        async def record_interaction(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(community, "CommunitySignalCollector", FakeCollector)

    before = tracked_task_count()
    community._record_community_signal(user_id=community.UUID(int=1), action="post_create", context="test")
    await _settle()
    assert len(calls) == 1
    assert calls[0]["action"] == "post_create"
    await _settle()
    assert tracked_task_count() == before


# ---------------------------------------------------------------------------
# after-commit 钩子：tool_history / achievement
# ---------------------------------------------------------------------------


class _FakeSyncSessionInfo(dict[str, Any]):
    pass


class _FakeSession:
    def __init__(self) -> None:
        self.info: _FakeSyncSessionInfo = _FakeSyncSessionInfo()


async def test_tool_history_after_commit_hook_spawns_tracked():
    import app.services.tool_history_service as tool_history

    ran = asyncio.Event()
    session = _FakeSession()

    async def publish() -> None:
        ran.set()

    session.info[tool_history._AFTER_COMMIT_TASKS_KEY] = [publish]
    assert tool_history._AFTER_COMMIT_TASKS_KEY in session.info

    tool_history._run_tool_history_after_commit_tasks(session)
    await asyncio.wait_for(ran.wait(), timeout=1.0)  # 回调真的执行
    assert tool_history._AFTER_COMMIT_TASKS_KEY not in session.info  # pop 语义保持


def _run_hook_without_loop(module: Any, session: _FakeSession) -> None:
    """同步线程内（无 running loop）调用 after-commit 钩子：应 warning 跳过。"""
    module._run_tool_history_after_commit_tasks(session)


def _run_achievement_hook_without_loop(module: Any, session: _FakeSession) -> None:
    module._run_achievement_after_commit_tasks(session)


async def test_tool_history_after_commit_hook_no_loop_is_skipped():
    import concurrent.futures

    import app.services.tool_history_service as tool_history

    session = _FakeSession()
    session.info[tool_history._AFTER_COMMIT_TASKS_KEY] = [lambda: None]
    before = tracked_task_count()

    # 同步线程内无 running loop：钩子 warning 跳过——回调 list 已按原语义 pop
    # （该分支丢弃回调并告警，先于本卡即如此），且绝不 spawn 任务。
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_hook_without_loop, tool_history, session).result(timeout=5.0)
    assert tool_history._AFTER_COMMIT_TASKS_KEY not in session.info
    assert tracked_task_count() == before


async def test_achievement_after_commit_hook_spawns_tracked():
    import app.services.achievement_engine as achievement

    ran = asyncio.Event()
    session = _FakeSession()

    async def emit() -> None:
        ran.set()

    session.info[achievement._AFTER_COMMIT_TASKS_KEY] = [emit]

    achievement._run_achievement_after_commit_tasks(session)
    await asyncio.wait_for(ran.wait(), timeout=1.0)
    assert achievement._AFTER_COMMIT_TASKS_KEY not in session.info


async def test_achievement_after_commit_hook_no_loop_is_skipped():
    import concurrent.futures

    import app.services.achievement_engine as achievement

    session = _FakeSession()
    session.info[achievement._AFTER_COMMIT_TASKS_KEY] = [lambda: None]
    before = tracked_task_count()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_achievement_hook_without_loop, achievement, session).result(timeout=5.0)
    assert achievement._AFTER_COMMIT_TASKS_KEY not in session.info  # 已按原语义 pop
    assert tracked_task_count() == before  # 未 spawn
