"""
Core: infra
Phase: execute
Stage: restore-storm guard (engine-restore-storm)

异步安全的 Celery fire-and-forget 投递。

根因（2026-09-18 会话恢复风暴实证）：在 ``async def`` 路径里直接调用
``celery_app.send_task(...)`` 是**同步阻塞**网络 I/O；当 broker/result store
异常时（如 result backend 认证失败），kombu 的重连重试会让调用卡住 ~19s，
期间**整个 asyncio 事件循环被冻结**，引擎所有并发请求排队超时（网关 30s →
503 雪崩、community/ws 代理 19s → 502）。engine_api.log 实证::

    21:26:01.766 [GLMBatch] enqueue node_sector_backfill ...
    21:26:20.942 enqueue failed ... Retry limit exceeded while trying to
    reconnect to the Celery result store backend   ← 事件循环冻结 19.18s

本 helper 三重防护：
1. ``run_in_executor`` 把同步 ``send_task`` 挪出事件循环线程（loop 永不冻结）；
2. ``asyncio.wait_for`` 强制投递超时（默认 3s），超时放弃并记日志；
3. ``ignore_result=True``（fire-and-forget 语义）避免绑定 result store——
   正是风暴中重连风暴的源头。

O-07 追加第四重防护 —— 队列背压（``app/core/queue_backpressure.py``）：
投递前探测目标队列深度，超上限即**丢弃**（返回 False + drops 指标 +
WARNING），队列不再无界堆积（FIX-49 glm_batch 回积的投递面硬顶）。探测
失败放行（有界降级：broker 不可达时 send_task 必然失败，无堆积路径）。

永不抛出：投递失败仅记 WARNING 并返回 False，由调用方决定降级语义。
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.core.celery_app import celery_app

DEFAULT_DISPATCH_TIMEOUT_SECONDS = 3.0


async def dispatch_task_async(
    task_name: str,
    *,
    args: tuple | list | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str | None = None,
    timeout: float = DEFAULT_DISPATCH_TIMEOUT_SECONDS,
    ignore_result: bool = True,
) -> bool:
    """把 Celery 任务投递挪出事件循环并加超时熔断（fire-and-forget）。

    返回 True 表示投递成功；失败/超时/队列背压丢弃返回 False（不抛异常）。
    """
    if timeout <= 0:
        timeout = DEFAULT_DISPATCH_TIMEOUT_SECONDS

    # O-07 · 队列背压硬顶：超限即丢弃（显式 outcome + 指标），不再无界堆积。
    if queue:
        from app.core.queue_backpressure import enforce_queue_backpressure

        try:
            if not await enforce_queue_backpressure(str(queue)):
                return False
        except Exception as exc:  # noqa: BLE001 — 背压面自身故障不得打断投递路径
            logger.warning("[CeleryDispatch] backpressure check errored (allow): {} {!r}", task_name, exc)

    def _send() -> Any:
        return celery_app.send_task(
            task_name,
            args=tuple(args) if args else None,
            kwargs=kwargs,
            queue=queue,
            ignore_result=ignore_result,
        )

    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(None, _send), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        logger.warning(
            "[CeleryDispatch] task {} enqueue timed out after {}s (off-loop, no freeze)",
            task_name,
            timeout,
        )
        return False
    except Exception as exc:  # noqa: BLE001 — 投递是 best-effort，不允许打断请求路径
        logger.warning("[CeleryDispatch] task {} enqueue failed: {}", task_name, exc)
        return False
