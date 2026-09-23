"""PROD-LOG #9 契约测试：执行调度 tick 的 due/dispatched 必须真实可见.

背景（v3-output/PROD-LOG/REPORT.md ②-9）：
- ``run_execution_schedule_tick`` 曾用 stdlib logging 的 ``%s`` 逗号参数风格调
  loguru；loguru 只认 ``{}``/f-string，两个参数被静默丢弃，调度吞吐永远不可见
  （日志里是字面量 ``due=%s dispatched=%s``）。
- 契约：完成日志必须携带真实数值，且不得再出现字面量 ``%s``。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from loguru import logger

from app.services.scheduler_service import SchedulerService


class _AsyncSessionContext:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeExecutionScheduleService:
    instances: list[_FakeExecutionScheduleService] = []

    def __init__(self, db) -> None:
        self.db = db
        _FakeExecutionScheduleService.instances.append(self)

    async def tick_due_schedules(self) -> dict:
        return {"due_count": 3, "dispatched_count": 2}


@pytest.fixture
def tick_records():
    records: list = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    yield records
    logger.remove(sink_id)


@pytest.mark.asyncio
async def test_execution_tick_log_shows_due_and_dispatched(
    monkeypatch: pytest.MonkeyPatch, tick_records: list
):
    _FakeExecutionScheduleService.instances = []
    fake_session = SimpleNamespace()
    monkeypatch.setattr(
        "app.services.scheduler_service.AsyncSessionLocal",
        lambda: _AsyncSessionContext(fake_session),
    )
    monkeypatch.setattr(
        "app.services.scheduler_service.ExecutionScheduleService",
        _FakeExecutionScheduleService,
    )

    service = SchedulerService()
    await service.run_execution_schedule_tick()

    assert _FakeExecutionScheduleService.instances, "tick 应构造 ExecutionScheduleService"
    completed = [
        r["message"]
        for r in tick_records
        if r["level"].name == "INFO" and "Execution schedule tick completed" in r["message"]
    ]
    assert completed, "缺少 tick 完成日志"
    msg = completed[-1]
    assert "due=3" in msg, f"due 数值不可见: {msg!r}"
    assert "dispatched=2" in msg, f"dispatched 数值不可见: {msg!r}"
    assert "%s" not in msg, f"loguru 日志不得残留 %s 形制: {msg!r}"
