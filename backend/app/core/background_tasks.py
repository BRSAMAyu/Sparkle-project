"""Tracked fire-and-forget background task spawning (FF 收敛批，wt310).

收敛仓库里裸 ``asyncio.create_task(...)`` / ``loop.create_task(...)`` 调用点
（wt294 P1-3 清单 / wt299 执行建议）到统一 helper：

* 模块级强引用集合——asyncio 只持弱引用，裸 spawn 的任务可能在飞行中被 GC
  静默回收（结果丢失、异常被吞至 "Task exception was never retrieved"）；
* done-callback 先取回异常再 discard——异常必被日志记录（带任务上下文），
  不再静默；
* ``shutdown_tracked_tasks``——给 main.py 优雅关停链一个明确的
  drain-then-cancel 衔接面：先给短尾任务（审计写、信号采集、after-commit
  发布）自然完成的宽限期，再取消残留者并等待。

参考实现：``app.services.task_feedback_service.spawn_followup_task``
（P1-C 形态，测试 monkeypatch 挂点，保持不动）；本模块是其共享化版本。
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, Callable

from loguru import logger

# 强引用集合：保活 pending 的 fire-and-forget 任务（asyncio GC quirk）。
_TRACKED_TASKS: set[asyncio.Task[Any]] = set()

# on_error 钩子签名：收到任务与其异常；默认实现记 error 日志。
ErrorLogger = Callable[[asyncio.Task[Any], BaseException], None]


def _task_label(task: asyncio.Task[Any]) -> str:
    """Human-readable label: coroutine qualname (fallback task name) + task name."""
    coro = task.get_coro()
    coro_label = getattr(coro, "__qualname__", None) or getattr(coro, "__name__", None)
    if coro_label:
        return f"{coro_label}[{task.get_name()}]"
    return task.get_name()


def _default_on_error(task: asyncio.Task[Any], exc: BaseException) -> None:
    logger.opt(exception=exc).error("Tracked background task failed: task={} error={!r}", _task_label(task), exc)


def register_tracked_task(
    task: asyncio.Task[Any],
    *,
    registry: set[asyncio.Task[Any]] | None = None,
    on_error: ErrorLogger | None = None,
) -> asyncio.Task[Any]:
    """Attach strong-ref keepalive + exception-visibility tracking to a task.

    已创建的任务（如所有者自己 create_task 的长驻 worker）可用本函数纳入统一
    追踪；``registry`` 传所有者自己的集合（如 ChatOrchestrator._bg_tasks）时，
    关停取消语义仍归所有者，本模块只补强引用与异常日志。
    """
    reg = _TRACKED_TASKS if registry is None else registry
    reg.add(task)

    def _on_done(t: asyncio.Task[Any]) -> None:
        reg.discard(t)
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            (on_error or _default_on_error)(t, exc)

    task.add_done_callback(_on_done)
    return task


def spawn_tracked(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str | None = None,
    on_error: ErrorLogger | None = None,
    registry: set[asyncio.Task[Any]] | None = None,
) -> asyncio.Task[Any]:
    """Spawn a fire-and-forget coroutine as a tracked task (P1-C pattern).

    - 强引用保活：任务不会被 GC 静默回收；
    - 异常可见：done-callback 取回异常并记日志（loguru，带任务上下文），
      可用 ``on_error`` 覆盖（传 no-op 即显式静音）；
    - ``name``：任务名（缺省用协程 qualname），进日志与 asyncio 任务名；
    - ``registry``：缺省进模块级集合（由 ``shutdown_tracked_tasks`` 收口）；
      传所有者集合则由所有者负责关停取消。
    """
    task_name = name or getattr(coro, "__qualname__", None) or "tracked-background-task"
    task = asyncio.get_running_loop().create_task(coro, name=task_name)
    return register_tracked_task(task, registry=registry, on_error=on_error)


def tracked_task_count() -> int:
    """Currently tracked (not yet discarded) tasks — ops probe / test hook."""
    return len(_TRACKED_TASKS)


async def shutdown_tracked_tasks(*, timeout: float = 5.0) -> int:
    """Graceful-shutdown seam for tracked fire-and-forget tasks.

    语义：**先 drain 后 cancel**。进入时未完成任务有 ``timeout`` 秒自然收尾
    （均为短尾 followup：审计写、信号采集、after-commit 发布）；超时残留者
    cancel 并等待落地。返回进入时的 pending 数。cancelled 路径不触发异常
    日志（与 done-callback 的 ``t.cancelled()`` 分支一致）。
    """
    pending = [t for t in _TRACKED_TASKS if not t.done()]
    if not pending:
        return 0
    _, unfinished = await asyncio.wait(pending, timeout=timeout)
    stragglers = [t for t in unfinished if not t.done()]
    for t in stragglers:
        t.cancel()
    if stragglers:
        await asyncio.gather(*stragglers, return_exceptions=True)
    return len(pending)
