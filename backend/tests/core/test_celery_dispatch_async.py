"""
Core: infra
Phase: execute
Stage: restore-storm guard

dispatch_task_async 最小单测：同步 send_task 阻塞（模拟 broker/result store
故障重连）时，事件循环保持响应；超时后返回 False 且不抛异常。
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.celery_dispatch import dispatch_task_async


@pytest.mark.asyncio
async def test_event_loop_stays_responsive_while_send_task_blocks(monkeypatch):
    """send_task 同步卡 5s（模拟 result store 重连风暴）：心跳不被冻结，3s 超时熔断。"""

    def _blocking_send_task(*args, **kwargs):  # 模拟同步 kombu 重连阻塞
        time.sleep(5.0)
        return object()

    import app.core.celery_app as celery_app_module

    monkeypatch.setattr(celery_app_module.celery_app, "send_task", _blocking_send_task)

    heartbeats = 0

    async def heartbeat():
        nonlocal heartbeats
        while True:
            heartbeats += 1
            await asyncio.sleep(0.01)

    hb_task = asyncio.create_task(heartbeat())
    start = time.monotonic()
    ok = await dispatch_task_async("some_task", args=(1,), timeout=0.3)
    elapsed = time.monotonic() - start
    hb_task.cancel()

    assert ok is False, "阻塞投递超时应返回 False"
    assert elapsed < 1.0, f"dispatch 应在超时后熔断返回，实际耗时 {elapsed:.2f}s"
    assert heartbeats >= 10, (
        f"事件循环在 send_task 阻塞期间被冻结（心跳仅 {heartbeats} 次）——"
        "这正是恢复风暴雪崩的根因，不允许回归"
    )


@pytest.mark.asyncio
async def test_dispatch_success_returns_true(monkeypatch):
    def _fast_send_task(*args, **kwargs):
        assert kwargs.get("ignore_result") is True, "fire-and-forget 投递不得绑定 result store"
        return object()

    import app.core.celery_app as celery_app_module

    monkeypatch.setattr(celery_app_module.celery_app, "send_task", _fast_send_task)
    ok = await dispatch_task_async("some_task", args=(1, 2), queue="default")
    assert ok is True


@pytest.mark.asyncio
async def test_dispatch_failure_does_not_raise(monkeypatch):
    def _exploding_send_task(*args, **kwargs):
        raise ConnectionError("Retry limit exceeded (result store)")

    import app.core.celery_app as celery_app_module

    monkeypatch.setattr(celery_app_module.celery_app, "send_task", _exploding_send_task)
    ok = await dispatch_task_async("some_task")
    assert ok is False, "投递失败必须吞掉异常返回 False（best-effort 语义）"
