"""EI-01 回归守卫：`tasks.policy.process_due_policies` 必须能在 Celery 同步任务体内完整跑通。

历史根因：任务把 `with get_db_context()` 写在 async 函数体内，而 `get_db_context.__exit__`
依赖 `asyncio.run()` —— 在 `_run_async` 的持久事件循环上被调用时抛出
`RuntimeError: asyncio.run() cannot be called from a running event loop`，导致 beat 每 30s
的调度 100% 失败并形成重试风暴。

修复后任务采用与 `app/core/celery_tasks.py` 一致的模式：整个协程（含 DB 会话生命周期）
由 `_run_async` 一次性驱动，会话从创建到 commit/close 始终处于同一事件循环。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.tasks import policy_tasks


class FakeSession:
    """最小 AsyncSession 替身：记录 commit/close 是否在协程链内发生。"""

    def __init__(self) -> None:
        self.committed = False
        self.closed = False

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        self.closed = True

    async def commit(self) -> None:
        self.committed = True


class FakePolicySchedulerService:
    sessions_used: list[FakeSession] = []
    result: dict[str, int] = {"due_count": 2, "triggered_count": 1}

    def __init__(self, db: FakeSession) -> None:
        self._db = db

    async def process_due_policies(self) -> dict[str, int]:
        type(self).sessions_used.append(self._db)
        return type(self).result


@pytest.fixture()
def fake_policy_env(monkeypatch: pytest.MonkeyPatch) -> list[FakeSession]:
    FakePolicySchedulerService.sessions_used = []
    sessions: list[FakeSession] = []

    def _factory() -> FakeSession:
        session = FakeSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(policy_tasks, "AsyncSessionLocal", _factory, raising=False)
    monkeypatch.setattr(policy_tasks, "PolicySchedulerService", FakePolicySchedulerService)
    return sessions


def test_process_due_policies_completes_without_loop_error(
    fake_policy_env: list[FakeSession],
) -> None:
    """任务跑通且不再触发跨事件循环 RuntimeError。"""
    result = policy_tasks.process_due_policies()

    assert result == {"due_count": 2, "triggered_count": 1}
    assert len(fake_policy_env) == 1
    assert fake_policy_env[0].committed is True
    assert fake_policy_env[0].closed is True


def test_process_due_policies_survives_repeated_invocations(
    fake_policy_env: list[FakeSession],
) -> None:
    """beat 每 30s 连续调度：复用持久事件循环多次执行不抛 RuntimeError。"""
    first = policy_tasks.process_due_policies()
    second = policy_tasks.process_due_policies()

    assert first == second == {"due_count": 2, "triggered_count": 1}
    assert len(fake_policy_env) == 2
    assert all(s.closed for s in fake_policy_env)
