from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import weakref
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# R2-01: 取消内层协程后等待其退出的有界时长，避免内层屏蔽取消时卡死调用方
_INNER_CANCEL_JOIN_TIMEOUT = 5.0


@dataclass
class TaskStats:
    """任务统计信息"""
    task_id: str
    task_name: str
    status: str  # running, completed, failed, cancelled
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    exception_type: str | None = None


class _LoopRuntime:
    """R2-05: 与单个事件循环绑定的运行时资源。

    asyncio.Queue/Semaphore/Task 都只能在其创建的事件循环上使用；
    全局单例若直接持有这些对象，第二个循环上会抛
    "RuntimeError: ... is bound to a different event loop" 或静默死队列。
    """

    __slots__ = ("loop", "queue", "queue_seq", "queue_worker_task", "semaphore", "tasks")

    def __init__(self, loop: asyncio.AbstractEventLoop, max_concurrent_tasks: int) -> None:
        self.loop = loop
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.queue_seq = 0
        self.queue_worker_task: asyncio.Task | None = None
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.tasks: dict[str, asyncio.Task] = {}


class BackgroundTaskManager:
    """
    统一管理后台任务,提供异常追踪、资源限制和监控

    功能:
    - 并发限制 (Semaphore)
    - 异常捕获和日志记录
    - 任务统计和监控
    - 优雅关闭
    - 健康检查
    - R2-01: 取消传播 —— cancel 包装任务会取消内层协程并等待其退出
    - R2-05: 事件循环安全 —— 队列/worker/信号量按循环惰性创建，单例可跨循环复用
    """

    def __init__(self, max_concurrent_tasks: int = 100):
        self._max_concurrent_tasks = max_concurrent_tasks
        self._loop_runtimes: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _LoopRuntime] = (
            weakref.WeakKeyDictionary()
        )
        self._stats: dict[str, TaskStats] = {}  # 任务统计（跨循环共享的纯数据）
        self._logger = logger
        self._total_spawned = 0
        self._total_completed = 0
        self._total_failed = 0
        self._start_time = datetime.now()
        self._shutdown = False
        # task_id -> inner_handle；worker 出队后消费（R2-01 直达内层的取消句柄）
        # 注意：put 与 worker 出队都在同一循环内串行完成，dict 操作无需加锁
        self._pending_inner_handles: dict[str, dict[str, asyncio.Task | None]] = {}

    def _loop_runtime(self) -> _LoopRuntime:
        """获取当前运行循环绑定的运行时资源（不存在则惰性创建）"""
        loop = asyncio.get_running_loop()
        runtime = self._loop_runtimes.get(loop)
        if runtime is None:
            runtime = _LoopRuntime(loop, self._max_concurrent_tasks)
            self._loop_runtimes[loop] = runtime
        return runtime

    def _iter_runtimes(self) -> list[_LoopRuntime]:
        return list(self._loop_runtimes.values())

    async def spawn(
        self,
        coro: Coroutine[Any, Any, Any],
        task_name: str = "unnamed_task",
        user_id: str | None = None,
        priority: int = 0
    ) -> asyncio.Task:
        """
        创建受管理的后台任务

        Args:
            coro: 协程对象
            task_name: 任务名称 (用于监控和日志)
            user_id: 关联的用户ID (用于配额追踪)
            priority: 任务优先级 (未来用于优先级队列)

        Returns:
            asyncio.Task: 创建的任务对象。cancel() 该任务会把取消传播到内层协程
            并等待其退出（R2-01）。
        """
        runtime = self._loop_runtime()
        task_id = f"{task_name}_{int(time.time() * 1000000)}_{self._total_spawned}"

        # 记录统计
        stats = TaskStats(
            task_id=task_id,
            task_name=task_name,
            status="queued",
            created_at=datetime.now()
        )
        self._stats[task_id] = stats
        self._total_spawned += 1

        result_future: asyncio.Future = runtime.loop.create_future()
        self._ensure_queue_worker(runtime)

        # Higher priority value means earlier execution
        runtime.queue_seq += 1
        await runtime.queue.put(
            (-priority, runtime.queue_seq, task_id, task_name, user_id, coro, stats, result_future)
        )

        # R2-01: 内层任务句柄 —— worker 创建受管任务后回填，
        # 包装任务被 cancel 时可直达内层协程，无需等待 worker 轮询
        inner_handle: dict[str, asyncio.Task | None] = {"task": None, "wrapper": None}

        async def _await_result():
            try:
                return await result_future
            except asyncio.CancelledError:
                result_future.cancel()
                inner = inner_handle["task"]
                if inner is not None and not inner.done():
                    inner.cancel()
                    # 等待内层退出（有界），保证取消语义完整、不留烧 token 的孤儿协程
                    with contextlib.suppress(Exception):
                        await asyncio.wait({inner}, timeout=_INNER_CANCEL_JOIN_TIMEOUT)
                    if inner.done():
                        with contextlib.suppress(asyncio.CancelledError):
                            inner.exception()
                raise

        queued_task = asyncio.create_task(_await_result(), name=f"queued_{task_id}")
        runtime.tasks[f"queued_{task_id}"] = queued_task
        queued_task.add_done_callback(
            lambda _t, key=f"queued_{task_id}": runtime.tasks.pop(key, None)
        )
        self._logger.debug(
            f"🚀 Task queued: {task_name} (ID: {task_id}, "
            f"User: {user_id}, Priority: {priority})"
        )
        # worker 拿到同一句柄字典，创建内层任务后回填
        self._pending_inner_handles[task_id] = inner_handle
        inner_handle["wrapper"] = queued_task
        return queued_task

    def _ensure_queue_worker(self, runtime: _LoopRuntime) -> None:
        if runtime.queue_worker_task and not runtime.queue_worker_task.done():
            return
        runtime.queue_worker_task = asyncio.create_task(
            self._queue_worker(runtime), name="task_manager_queue_worker"
        )

    async def _queue_worker(self, runtime: _LoopRuntime) -> None:
        while not self._shutdown:
            try:
                item = await runtime.queue.get()
            except asyncio.CancelledError:
                break

            priority, seq, task_id, task_name, user_id, coro, stats, result_future = item
            caller_gone_waiter: asyncio.Task | None = None
            try:
                # R2-01: 调用方在出队前就放弃（result_future 已取消，或包装任务
                # 尚未启动即被 cancel）——丢弃队列项，不启动内层协程
                inner_handle = self._pending_inner_handles.pop(task_id, None)
                wrapper = inner_handle.get("wrapper") if inner_handle else None
                if result_future.cancelled() or (wrapper is not None and wrapper.cancelled()):
                    coro.close()
                    continue

                task = self._create_managed_task(
                    runtime=runtime,
                    task_id=task_id,
                    task_name=task_name,
                    user_id=user_id,
                    coro=coro,
                    stats=stats
                )
                # R2-01: 回填内层句柄，让包装任务的 cancel() 可直达内层协程
                if inner_handle is not None:
                    inner_handle["task"] = task

                # R2-01: 同时监听“调用方已取消”事件，及时终止内层协程，
                # 而不是在 await task 期间对 result_future.cancelled() 视而不见
                caller_gone = asyncio.Event()
                # 事件必须经默认参数绑定：set_result 的回调由 call_soon 异步触发，
                # 可能晚于 worker 进入下一轮迭代（caller_gone 已被重新赋值）。
                # 直接闭包共享变量会让旧项的回调 set 新项的事件，
                # 误触发 caller-gone 分支、取消健康运行中的内层协程
                result_future.add_done_callback(lambda _f, ev=caller_gone: ev.set())
                caller_gone_waiter = asyncio.ensure_future(caller_gone.wait())

                done, _pending = await asyncio.wait(
                    {task, caller_gone_waiter},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if task in done:
                    try:
                        exc = task.exception()
                        if exc is not None:
                            if not result_future.cancelled():
                                result_future.set_exception(exc)
                        elif not result_future.cancelled():
                            result_future.set_result(task.result())
                    except asyncio.CancelledError:
                        # 任务被外部取消（如 graceful_shutdown），无结果可回填：
                        # 把取消转递给等待方。注意 CancelledError 不是 Exception，
                        # 若在此吞掉或继续 task.result() 会让 worker 整个退出
                        if not result_future.cancelled():
                            result_future.cancel()
                else:
                    # 调用方已放弃：把取消传播到内层协程并等待其真正退出
                    if not task.done():
                        task.cancel()
                    with contextlib.suppress(Exception):
                        await asyncio.wait({task}, timeout=_INNER_CANCEL_JOIN_TIMEOUT)
                    if task.done():
                        with contextlib.suppress(asyncio.CancelledError):
                            task.exception()
                    # 兜底：无论本分支由哪条路径进入，wrapper 的
                    # await result_future 都必须最终解除阻塞
                    if not result_future.done():
                        result_future.cancel()
            except Exception as e:
                if not result_future.cancelled():
                    result_future.set_exception(e)
            finally:
                if caller_gone_waiter is not None:
                    caller_gone_waiter.cancel()
                runtime.queue.task_done()

    def _create_managed_task(
        self,
        *,
        runtime: _LoopRuntime,
        task_id: str,
        task_name: str,
        user_id: str | None,
        coro: Coroutine[Any, Any, Any],
        stats: TaskStats
    ) -> asyncio.Task:
        async def _wrapped():
            async with runtime.semaphore:
                stats.started_at = datetime.now()
                stats.status = "running"
                start_time = time.time()

                try:
                    result = await coro
                    stats.status = "completed"
                    stats.completed_at = datetime.now()
                    stats.duration_ms = (time.time() - start_time) * 1000
                    self._total_completed += 1

                    self._logger.debug(
                        f"✅ Task completed: {task_name} (ID: {task_id}, "
                        f"Duration: {stats.duration_ms:.2f}ms)"
                    )
                    return result

                except asyncio.CancelledError:
                    stats.status = "cancelled"
                    stats.completed_at = datetime.now()
                    stats.duration_ms = (time.time() - start_time) * 1000
                    self._logger.warning(f"⚠️ Task cancelled: {task_name} (ID: {task_id})")
                    raise

                except Exception as e:
                    stats.status = "failed"
                    stats.completed_at = datetime.now()
                    stats.duration_ms = (time.time() - start_time) * 1000
                    stats.error_message = str(e)
                    stats.exception_type = type(e).__name__
                    self._total_failed += 1

                    self._logger.error(
                        f"❌ Task failed: {task_name} (ID: {task_id})\n"
                        f"   Error: {e}\n"
                        f"   Duration: {stats.duration_ms:.2f}ms",
                        exc_info=True  # stdlib logging：exc_info 有效，保留堆栈
                    )

                    # 发送到监控系统 (如果配置)
                    await self._report_to_monitoring(task_id, stats, user_id)

                    # 重新抛出,让调用者可以选择处理
                    raise

        task = asyncio.create_task(_wrapped(), name=task_id)
        runtime.tasks[task_id] = task

        # 任务完成时清理
        def cleanup_callback(t, *, key=task_id, rt=runtime):
            if key in rt.tasks:
                del rt.tasks[key]

        task.add_done_callback(cleanup_callback)
        return task

    async def spawn_with_retry(
        self,
        coro_factory,
        task_name: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> asyncio.Task:
        """
        创建带重试机制的任务

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
        """
        if asyncio.iscoroutine(coro_factory):
            raise ValueError("spawn_with_retry requires a coroutine factory, not a coroutine instance")

        async def _wrapped_with_retry():
            for attempt in range(max_retries + 1):
                try:
                    await coro_factory()
                    return
                except Exception:
                    if attempt == max_retries:
                        raise
                    self._logger.warning(
                        f"Task {task_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避

        return await self.spawn(_wrapped_with_retry(), task_name, **kwargs)

    def get_stats(self) -> dict[str, Any]:
        """获取任务管理器统计信息"""
        running = len([s for s in self._stats.values() if s.status == "running"])
        completed_tasks = [s for s in self._stats.values() if s.status == "completed"]
        [s for s in self._stats.values() if s.status == "failed"]

        avg_duration = 0
        if completed_tasks:
            avg_duration = sum(
                s.duration_ms for s in completed_tasks if s.duration_ms
            ) / len(completed_tasks)

        return {
            "total_spawned": self._total_spawned,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "currently_running": running,
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "average_duration_ms": round(avg_duration, 2),
            "failure_rate": round(self._total_failed / max(self._total_spawned, 1) * 100, 2),
            "concurrency_limit": self._max_concurrent_tasks
        }

    def get_task_details(self, task_id: str) -> dict[str, Any] | None:
        """获取特定任务的详细信息"""
        stats = self._stats.get(task_id)
        if not stats:
            return None

        return {
            "task_id": stats.task_id,
            "task_name": stats.task_name,
            "status": stats.status,
            "created_at": stats.created_at.isoformat(),
            "started_at": stats.started_at.isoformat() if stats.started_at else None,
            "completed_at": stats.completed_at.isoformat() if stats.completed_at else None,
            "duration_ms": stats.duration_ms,
            "error_message": stats.error_message,
            "exception_type": stats.exception_type
        }

    def get_active_tasks(self) -> dict[str, str]:
        """获取当前活跃的任务（跨循环聚合）"""
        active: dict[str, str] = {}
        for runtime in self._iter_runtimes():
            active.update({
                task_id: task.get_name()
                for task_id, task in runtime.tasks.items()
                if not task.done()
                and self._stats.get(task_id, TaskStats("", "", "", datetime.now())).status == "running"
            })
        return active

    async def wait_for_task(self, task_id: str, timeout: float | None = None) -> bool:
        """
        等待特定任务完成

        Returns:
            bool: 是否在超时前完成
        """
        for runtime in self._iter_runtimes():
            task = runtime.tasks.get(task_id)
            if task is None:
                continue
            try:
                await asyncio.wait_for(task, timeout=timeout)
                return True
            except TimeoutError:
                return False
            except asyncio.CancelledError:
                # 目标任务被取消 → 视为未完成；调用方自身被取消 → 必须继续传播
                if task.cancelled():
                    return False
                raise
        return False

    async def graceful_shutdown(self, timeout: int = 30):
        """
        优雅关闭所有任务

        Args:
            timeout: 等待任务完成的最大时间(秒)
        """
        runtime = self._loop_runtime()
        if not runtime.tasks:
            self._logger.info("No background tasks to shutdown")
            if runtime.queue_worker_task:
                runtime.queue_worker_task.cancel()
            return

        self._logger.info(
            f"🛑 Graceful shutdown initiated - "
            f"Waiting for {len(runtime.tasks)} tasks to complete (timeout: {timeout}s)"
        )

        self._shutdown = True
        if runtime.queue_worker_task:
            runtime.queue_worker_task.cancel()

        # 等待所有任务完成
        try:
            await asyncio.wait_for(
                asyncio.gather(*runtime.tasks.values(), return_exceptions=True),
                timeout=timeout
            )
            self._logger.info("✅ All background tasks completed gracefully")
        except TimeoutError:
            self._logger.warning(f"⏰ Shutdown timeout, cancelling {len(runtime.tasks)} remaining tasks")
            # 取消剩余任务
            for task in runtime.tasks.values():
                task.cancel()
            await asyncio.sleep(0.1)  # 让取消生效
        finally:
            while not runtime.queue.empty():
                try:
                    _, _, task_id, _, _, coro, _, result_future = runtime.queue.get_nowait()
                except Exception:
                    break
                # 未启动的协程直接关闭，避免 "coroutine never awaited" 告警；
                # 同步清理 handle 表，防止关停后残留
                with contextlib.suppress(Exception):
                    coro.close()
                self._pending_inner_handles.pop(task_id, None)
                if not result_future.cancelled():
                    result_future.cancel()
                runtime.queue.task_done()

        # 清理统计信息(保留最近1000条)
        if len(self._stats) > 1000:
            self._stats = dict(list(self._stats.items())[-1000:])

    def health_check(self) -> dict[str, Any]:
        """
        健康检查

        Returns:
            Dict: 健康状态
        """
        stats = self.get_stats()

        # 健康标准
        is_healthy = (
            stats["failure_rate"] < 10 and  # 失败率 < 10%
            stats["currently_running"] <= self._max_concurrent_tasks * 0.8  # 未接近上限
        )

        return {
            "healthy": is_healthy,
            "status": "healthy" if is_healthy else "degraded",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    async def _report_to_monitoring(self, task_id: str, stats: TaskStats, user_id: str | None):
        """
        报告任务失败到监控系统

        这里可以集成:
        - Sentry
        - Prometheus metrics
        - Slack/Email alerts
        """
        # 示例: 记录到 Prometheus (如果可用)
        try:
            from app.core.llm_monitoring import TASK_FAILURES
            TASK_FAILURES.labels(
                task_type=stats.task_name,
                error_type=stats.exception_type or "Unknown"
            ).inc()
        except ImportError:
            pass

        # 示例: Sentry (如果配置)
        # try:
        #     import sentry_sdk
        #     sentry_sdk.capture_exception(exception, extra={
        #         "task_id": task_id,
        #         "task_name": task_name,
        #         "user_id": user_id
        #     })
        # except ImportError:
        #     pass


# Global instance
task_manager = BackgroundTaskManager()
