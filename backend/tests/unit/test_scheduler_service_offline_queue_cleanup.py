from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.scheduler_service import SchedulerService


class _DummyScheduler:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []
        self.started = False

    def add_job(self, func, trigger, *args, **kwargs):
        self.jobs.append((func, trigger, args, kwargs))

    def start(self):
        self.started = True


class _AsyncSessionContext:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_scheduler_registers_offline_queue_cleanup_job():
    service = SchedulerService()
    dummy_scheduler = _DummyScheduler()
    service.scheduler = dummy_scheduler

    service.start()

    registered = {job[0].__name__: (job[1], job[3]) for job in dummy_scheduler.jobs}
    assert "run_offline_queue_cleanup" in registered
    trigger, kwargs = registered["run_offline_queue_cleanup"]
    assert trigger == "interval"
    assert kwargs["hours"] == 1
    assert dummy_scheduler.started is True


@pytest.mark.asyncio
async def test_run_offline_queue_cleanup_marks_expired_and_commits(monkeypatch):
    service = SchedulerService()
    fake_session = SimpleNamespace(commit=AsyncMock())
    cleanup_expired = AsyncMock(return_value=3)

    monkeypatch.setattr(
        "app.services.scheduler_service.AsyncSessionLocal",
        lambda: _AsyncSessionContext(fake_session),
    )
    monkeypatch.setattr(
        "app.services.scheduler_service.OfflineQueueService.cleanup_expired",
        cleanup_expired,
    )

    await service.run_offline_queue_cleanup()

    cleanup_expired.assert_awaited_once_with(fake_session)
    fake_session.commit.assert_awaited_once()
