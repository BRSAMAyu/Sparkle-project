import asyncio
from typing import Set, Coroutine, Optional, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class TaskStats:
    """任务统计信息"""
    task_id: str
    task_name: str
    status: str  # running, completed, failed, cancelled
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    exception_type: Optional[str] = None


class BackgroundTaskManager:
    """
    统一管理后台任务,提供异常追踪、资源限制和监控

    功能:
    - 并发限制 (Semaphore)
    - 异常捕获和日志记录
    - 任务统计和监控
    - 优雅关闭
    - 健康检查
    """

    def __init__(self, max_concurrent_tasks: int = 100):
        self._tasks: Dict[str, asyncio.Task] = {}  # 改为字典,便于追踪
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._stats: Dict[str, TaskStats] = {}  # 任务统计
        self._logger = logger
        self._total_spawned = 0
        self._total_completed = 0
        self._total_failed = 0
        self._start_time = datetime.now()

    async def spawn(
        self,
        coro: Coroutine[Any, Any, Any],
        task_name: str = "unnamed_task",
        user_id: Optional[str] = None,
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
            asyncio.Task: 创建的任务对象
        """
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

        async def _wrapped():
            async with self._semaphore:
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
                        exc_info=True
                    )

                    # 发送到监控系统 (如果配置)
                    await self._report_to_monitoring(task_id, stats, user_id)

                    # 重新抛出,让调用者可以选择处理
                    raise

        task = asyncio.create_task(_wrapped(), name=task_id)
        self._tasks[task_id] = task

        # 任务完成时清理
        def cleanup_callback(t):
            if task_id in self._tasks:
                del self._tasks[task_id]

        task.add_done_callback(cleanup_callback)

        self._logger.debug(
            f"🚀 Task spawned: {task_name} (ID: {task_id}, "
            f"User: {user_id}, Priority: {priority})"
        )

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
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    self._logger.warning(
                        f"Task {task_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避

        return await self.spawn(_wrapped_with_retry(), task_name, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """获取任务管理器统计信息"""
        running = len([s for s in self._stats.values() if s.status == "running"])
        completed_tasks = [s for s in self._stats.values() if s.status == "completed"]
        failed_tasks = [s for s in self._stats.values() if s.status == "failed"]

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
            "concurrency_limit": self._semaphore._value if hasattr(self._semaphore, '_value') else "N/A"
        }

    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
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

    def get_active_tasks(self) -> Dict[str, str]:
        """获取当前活跃的任务"""
        return {
            task_id: task.get_name()
            for task_id, task in self._tasks.items()
            if not task.done() and self._stats.get(task_id, TaskStats("", "", "", datetime.now())).status == "running"
        }

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> bool:
        """
        等待特定任务完成

        Returns:
            bool: 是否在超时前完成
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        try:
            await asyncio.wait_for(task, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def graceful_shutdown(self, timeout: int = 30):
        """
        优雅关闭所有任务

        Args:
            timeout: 等待任务完成的最大时间(秒)
        """
        if not self._tasks:
            self._logger.info("No background tasks to shutdown")
            return

        self._logger.info(
            f"🛑 Graceful shutdown initiated - "
            f"Waiting for {len(self._tasks)} tasks to complete (timeout: {timeout}s)"
        )

        # 等待所有任务完成
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._tasks.values(), return_exceptions=True),
                timeout=timeout
            )
            self._logger.info("✅ All background tasks completed gracefully")
        except asyncio.TimeoutError:
            self._logger.warning(f"⏰ Shutdown timeout, cancelling {len(self._tasks)} remaining tasks")
            # 取消剩余任务
            for task in self._tasks.values():
                task.cancel()
            await asyncio.sleep(0.1)  # 让取消生效

        # 清理统计信息(保留最近1000条)
        if len(self._stats) > 1000:
            self._stats = dict(list(self._stats.items())[-1000:])

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict: 健康状态
        """
        stats = self.get_stats()

        # 健康标准
        is_healthy = (
            stats["failure_rate"] < 10 and  # 失败率 < 10%
            stats["currently_running"] <= self._semaphore._value * 0.8  # 未接近上限
        )

        return {
            "healthy": is_healthy,
            "status": "healthy" if is_healthy else "degraded",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    async def _report_to_monitoring(self, task_id: str, stats: TaskStats, user_id: Optional[str]):
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
        #         "task_name": stats.task_name,
        #         "user_id": user_id
        #     })
        # except ImportError:
        #     pass


# Global instance
task_manager = BackgroundTaskManager()
