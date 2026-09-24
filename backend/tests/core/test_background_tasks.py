"""FF-CONVERGENCE（wt310）：spawn_tracked helper 单测。

覆盖 wt299 执行建议要求的路径：
- 强引用保活（不被 GC 静默回收）+ 完成后 discard（无泄漏）；
- 异常路径：done-callback 取回异常 → on_error（默认记日志 / 自定义钩子），
  不再走 "Task exception was never retrieved" 静默面；
- cancelled 路径：不触发 on_error；
- 关停 drain：自然收尾 / 超时 cancel 两种语义；空集快路径；
- registry 隔离：所有者自备集合（orchestrator 形态）。
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import background_tasks
from app.core.background_tasks import (
    register_tracked_task,
    shutdown_tracked_tasks,
    spawn_tracked,
    tracked_task_count,
)


async def _noop() -> None:
    await asyncio.sleep(0)


async def test_spawn_tracked_holds_reference_and_discards_on_done():
    before = tracked_task_count()
    task = spawn_tracked(_noop(), name="t.hold_ref")
    assert tracked_task_count() == before + 1  # 强引用已注册（FF 泄漏可见性）
    await task
    await asyncio.sleep(0)  # 让 done-callback 跑完
    assert tracked_task_count() == before  # 完成后 discard，无泄漏


async def test_spawn_tracked_default_name_uses_coro_qualname():
    task = spawn_tracked(_noop())
    try:
        assert task.get_name() == "_noop"
    finally:
        await task


async def test_spawn_tracked_custom_name():
    task = spawn_tracked(_noop(), name="custom.name")
    try:
        assert task.get_name() == "custom.name"
    finally:
        await task


async def test_exception_path_invokes_custom_on_error():
    errors: list[tuple[str, BaseException]] = []

    async def boom() -> None:
        raise RuntimeError("kaboom")

    task = spawn_tracked(boom(), name="t.boom", on_error=lambda t, e: errors.append((t.get_name(), e)))
    with pytest.raises(RuntimeError, match="kaboom"):
        await task
    await asyncio.sleep(0)
    assert len(errors) == 1
    assert errors[0][0] == "t.boom"
    assert isinstance(errors[0][1], RuntimeError)


async def test_exception_path_default_handler_retrieves_exception():
    """默认 handler：异常被取回（task.exception 已消费），registry 已清理。"""
    before = tracked_task_count()

    async def boom() -> None:
        raise ValueError("swallowed-no-more")

    task = spawn_tracked(boom(), name="t.default_err")
    with pytest.raises(ValueError, match="swallowed-no-more"):
        await task
    await asyncio.sleep(0)
    assert task.done() and not task.cancelled()
    assert isinstance(task.exception(), ValueError)
    assert tracked_task_count() == before  # done-callback 已 discard


async def test_cancelled_task_does_not_invoke_on_error():
    errors: list[BaseException] = []

    async def hang() -> None:
        await asyncio.sleep(30)

    task = spawn_tracked(hang(), name="t.cancel", on_error=lambda t, e: errors.append(e))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)
    assert errors == []  # cancel 语义：不算失败


async def test_custom_registry_isolates_from_module_registry():
    owner: set[asyncio.Task] = set()
    before = tracked_task_count()
    task = spawn_tracked(_noop(), name="t.owner", registry=owner)
    assert task in owner
    assert tracked_task_count() == before  # 模块级集合不受影响
    await task
    await asyncio.sleep(0)
    assert owner == set()  # 所有者集合同样被 done-callback 清理


async def test_register_tracked_task_on_precreated_task():
    owner: set[asyncio.Task] = set()
    errors: list[BaseException] = []
    task = asyncio.get_running_loop().create_task(_noop(), name="pre.created")

    returned = register_tracked_task(task, registry=owner, on_error=lambda t, e: errors.append(e))
    assert returned is task
    assert task in owner
    await task
    await asyncio.sleep(0)
    assert owner == set()
    assert errors == []


async def test_shutdown_drains_naturally_finishing_tasks():
    finished = asyncio.Event()

    async def short() -> None:
        await asyncio.sleep(0.05)
        finished.set()

    before = tracked_task_count()
    spawn_tracked(short(), name="t.drain_ok")
    drained = await shutdown_tracked_tasks(timeout=2.0)
    assert drained == 1
    assert finished.is_set()  # 自然收尾，未被 cancel
    await asyncio.sleep(0)
    assert tracked_task_count() == before


async def test_shutdown_cancels_stragglers_after_timeout():
    cancelled_seen = asyncio.Event()
    errors: list[BaseException] = []
    started = asyncio.Event()

    async def hang() -> None:
        started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled_seen.set()
            raise

    spawn_tracked(hang(), name="t.straggler", on_error=lambda t, e: errors.append(e))
    await started.wait()
    drained = await shutdown_tracked_tasks(timeout=0.01)
    assert drained == 1
    await asyncio.wait_for(cancelled_seen.wait(), timeout=1.0)
    assert errors == []  # cancel 不触发 on_error


async def test_shutdown_empty_registry_returns_zero():
    before = tracked_task_count()
    assert await shutdown_tracked_tasks(timeout=0.01) == 0
    assert tracked_task_count() == before


async def test_shutdown_counts_errored_task_as_done_not_pending():
    async def boom() -> None:
        raise RuntimeError("already-dead")

    task = spawn_tracked(boom(), name="t.dead")
    with pytest.raises(RuntimeError):
        await task
    await asyncio.sleep(0)  # 先让 done-callback 跑完，registry 回到稳态
    before = tracked_task_count()
    # 已完成（带异常）的任务不计入 pending，shutdown 不悬挂。
    assert await shutdown_tracked_tasks(timeout=0.01) == 0
    assert tracked_task_count() == before
    assert task.done()


async def test_default_on_error_does_not_raise():
    """_default_on_error 与 loguru 集成不抛（异常面兜底）。"""
    task = asyncio.get_running_loop().create_task(_noop(), name="label.probe")
    try:
        background_tasks._default_on_error(task, RuntimeError("probe"))
    finally:
        await task
