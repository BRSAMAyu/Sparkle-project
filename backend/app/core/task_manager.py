import asyncio
from typing import Set, Coroutine, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """
    统一管理后台任务，提供异常追踪和资源限制
    """

    def __init__(self, max_concurrent_tasks: int = 100):
        self._tasks: Set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._logger = logger

    async def spawn(self, coro: Coroutine[Any, Any, Any], task_name: str = "unnamed_task") -> asyncio.Task:
        """
        创建受管理的后台任务
        """
        async def _wrapped():
            async with self._semaphore:
                try:
                    await coro
                except Exception as e:
                    self._logger.error(f"Task '{task_name}' failed: {e}", exc_info=e)
                    # TODO: 发送到 Sentry/监控系统

        task = asyncio.create_task(_wrapped(), name=task_name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def shutdown(self):
        """
        优雅关闭所有任务
        """
        if not self._tasks:
            return
            
        self._logger.info(f"Waiting for {len(self._tasks)} background tasks to complete...")
        
        # 取消所有任务
        for task in self._tasks:
            task.cancel()
            
        # 等待任务结束
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._logger.info("All background tasks shut down.")

# Global instance
task_manager = BackgroundTaskManager()
