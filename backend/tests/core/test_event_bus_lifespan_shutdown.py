"""EI-04 守卫：event_bus 的内部消费循环必须纳入 lifespan 关停管理。

历史问题：`event_bus.subscribe()` 用 `asyncio.create_task` 把 `_consume_loop` 挂在 bus
内部后立即返回；main.py lifespan 里保存并 cancel 的 `*_consumer_task` 全是**已完成的
句柄**（cancel 空转），而唯一会取消这些内部任务的 `event_bus.close()` 在关机流程中从未
被调用 —— 关机不排空、在途消息靠 pending 重投兜底、关机窗口内死掉的 loop 还会被
`_restart_consume_loop` 复活（`_running` 仍为 True）。

契约：
1. `begin_shutdown()` 置 `_running=False`，此后死亡的消费循环不再被自动复活；
2. `close()` 取消并排空全部内部消费任务（既有 tests/test_event_bus_shutdown.py 已覆盖）；
3. main.py 的 lifespan 关停段必须先 `begin_shutdown()`、后 `await event_bus.close()`，
   且都发生在 `await cache_service.close()` 之前（事件总线关停需要 Redis 仍可用）。
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

import pytest

from app.core.event_bus import EventBus


async def _run_to_completion_with_exception(task: asyncio.Task) -> BaseException | None:
    results = await asyncio.gather(task, return_exceptions=True)
    return results[0] if results else None


@pytest.mark.asyncio
async def test_begin_shutdown_prevents_consume_loop_restart() -> None:
    bus = EventBus()
    bus._running = True

    async def failing_loop() -> None:
        raise RuntimeError("consume loop crashed")

    dead_task = asyncio.create_task(failing_loop())
    await _run_to_completion_with_exception(dead_task)

    # 正常运行期（现状行为，F3 修复）：死掉的 loop 会被自动重启。
    bus._restart_consume_loop(dead_task, "stream", "group", "consumer", _noop_callback)
    assert len(bus._consumer_tasks) == 1, "运行期消费循环死亡应被自动重启"
    restarted = bus._consumer_tasks[0]

    bus.begin_shutdown()
    assert bus._running is False

    # 等待重启出来的循环感知 _running=False 并自行退出。
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(restarted, timeout=5)
    bus._consumer_tasks.clear()

    # 关机窗口内：死亡的 loop 不再复活。
    dead_task_after_shutdown = asyncio.create_task(failing_loop())
    await _run_to_completion_with_exception(dead_task_after_shutdown)
    bus._restart_consume_loop(
        dead_task_after_shutdown, "stream", "group", "consumer", _noop_callback
    )
    assert bus._consumer_tasks == [], "begin_shutdown 后不应再复活消费循环"


async def _noop_callback(payload: dict) -> None:  # pragma: no cover - 测试占位
    return None


def test_main_lifespan_shuts_down_event_bus() -> None:
    """源码守卫：lifespan 关停段必须接入 event_bus 的排空逻辑（防回归）。"""
    import app.main as main_module

    source = Path(main_module.__file__).read_text(encoding="utf-8")

    shutdown_marker = "# ==================== 关闭时 ===================="
    shutdown_idx = source.index(shutdown_marker)
    begin_idx = source.index("event_bus.begin_shutdown()", shutdown_idx)
    close_idx = source.index("await event_bus.close()", shutdown_idx)
    cache_close_idx = source.index("await cache_service.close()", shutdown_idx)

    assert begin_idx < close_idx, "必须先 begin_shutdown() 阻止 loop 复活，再 close() 排空"
    assert close_idx < cache_close_idx, "event_bus.close() 必须发生在 cache_service.close() 之前"


@pytest.mark.asyncio
async def test_close_after_begin_shutdown_is_idempotent_enough() -> None:
    """close() 可安全地接入关停流程：无 redis、无任务时不抛错。"""
    bus = EventBus()
    bus.begin_shutdown()

    await bus.close()

    assert bus._running is False
    assert bus._consumer_tasks == []
