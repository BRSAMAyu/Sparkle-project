from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import app.services.scheduler_service as scheduler_module
from app.services.scheduler_service import SchedulerService


@pytest.fixture
def svc() -> SchedulerService:
    return SchedulerService()


def _patch_mode(monkeypatch, mode: str) -> None:
    kill_switch = SimpleNamespaceLike()
    kill_switch.get_feature_mode = AsyncMock(return_value=mode)
    monkeypatch.setattr(
        scheduler_module,
        "AuroraStage38KillSwitchService",
        lambda: kill_switch,
        raising=False,
    )
    # run_smart_push_cycle 内部为局部 import，需同时替换真实模块属性
    from app.services.aurora_stage38_kill_switch_service import (
        AuroraStage38KillSwitchService as RealSwitch,
    )

    monkeypatch.setattr(RealSwitch, "get_feature_mode", AsyncMock(return_value=mode))


class SimpleNamespaceLike:
    pass


@pytest.mark.asyncio
async def test_smart_push_cycle_skips_when_mode_off(monkeypatch):
    _patch_mode(monkeypatch, "off")
    push_spy = AsyncMock()
    monkeypatch.setattr(scheduler_module, "PushService", push_spy)
    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", _FakeSession(), raising=False)

    await SchedulerService().run_smart_push_cycle()

    push_spy.assert_not_called()


@pytest.mark.asyncio
async def test_smart_push_cycle_passes_shadow_mode_through(monkeypatch):
    _patch_mode(monkeypatch, "shadow")
    instance = SimpleNamespaceLike()
    instance.process_all_users = AsyncMock(return_value={})
    monkeypatch.setattr(scheduler_module, "PushService", lambda db: instance)
    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", _FakeSession())
    # 回收队列分支静默失败即可（non-fatal）
    monkeypatch.setattr(scheduler_module, "logger", _SilentLogger())

    await SchedulerService().run_smart_push_cycle()

    instance.process_all_users.assert_awaited_once_with(delivery_mode="shadow")


@pytest.mark.asyncio
async def test_smart_push_cycle_passes_live_mode_through(monkeypatch):
    _patch_mode(monkeypatch, "live")
    instance = SimpleNamespaceLike()
    instance.process_all_users = AsyncMock(return_value={})
    monkeypatch.setattr(scheduler_module, "PushService", lambda db: instance)
    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", _FakeSession())
    monkeypatch.setattr(scheduler_module, "logger", _SilentLogger())

    await SchedulerService().run_smart_push_cycle()

    instance.process_all_users.assert_awaited_once_with(delivery_mode="live")


class _FakeSession:
    """AsyncSessionLocal replacement: factory returning an async context."""

    def __call__(self):
        return self

    async def __aenter__(self):
        return object()

    async def __aexit__(self, *exc):
        return False


class _SilentLogger:
    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass
