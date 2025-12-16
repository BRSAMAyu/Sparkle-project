"""
知识拓展后台任务处理器
定期处理 NodeExpansionQueue 中的待处理任务
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.galaxy import NodeExpansionQueue
from app.services.expansion_service import ExpansionService

logger = logging.getLogger(__name__)


class ExpansionWorker:
    """
    知识拓展后台 Worker

    定期扫描 expansion_queue 表，处理 pending 状态的任务
    """

    def __init__(self, poll_interval: int = 30):
        """
        Args:
            poll_interval: 轮询间隔 (秒)
        """
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        """启动 Worker"""
        self.running = True
        logger.info("ExpansionWorker started")

        while self.running:
            try:
                await self._process_pending_tasks()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in ExpansionWorker: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """停止 Worker"""
        self.running = False
        logger.info("ExpansionWorker stopped")

    async def _process_pending_tasks(self):
        """处理所有待处理的任务"""
        async with async_session_maker() as db:
            # 查询待处理任务
            query = select(NodeExpansionQueue).where(
                NodeExpansionQueue.status == 'pending'
            ).order_by(NodeExpansionQueue.created_at.asc()).limit(10)  # 每次最多处理 10 个

            result = await db.execute(query)
            tasks = result.scalars().all()

            if not tasks:
                return

            logger.info(f"Found {len(tasks)} pending expansion tasks")

            # 逐个处理
            for task in tasks:
                try:
                    await self._process_single_task(task, db)
                except Exception as e:
                    logger.error(
                        f"Failed to process expansion task {task.id}: {e}",
                        exc_info=True
                    )
                    # 标记为失败
                    task.status = 'failed'
                    task.error_message = str(e)
                    await db.commit()

    async def _process_single_task(self, task: NodeExpansionQueue, db: AsyncSession):
        """处理单个拓展任务"""
        logger.info(f"Processing expansion task {task.id} for node {task.trigger_node_id}")

        expansion_service = ExpansionService(db)

        # 调用拓展服务
        new_nodes = await expansion_service.process_expansion(task.id)

        logger.info(
            f"Expansion task {task.id} completed: created {len(new_nodes)} new nodes"
        )

        # 如果需要，这里可以通过 SSE 或 WebSocket 通知前端
        # await self._notify_frontend(task.user_id, new_nodes)

    async def _notify_frontend(self, user_id, new_nodes):
        """
        通知前端新节点已创建 (可选实现)

        可以使用 SSE (Server-Sent Events) 或 WebSocket
        """
        # TODO: 实现实时通知
        pass


# 全局 Worker 实例
expansion_worker: Optional[ExpansionWorker] = None


async def start_expansion_worker():
    """启动拓展 Worker"""
    global expansion_worker
    expansion_worker = ExpansionWorker(poll_interval=30)
    asyncio.create_task(expansion_worker.start())


async def stop_expansion_worker():
    """停止拓展 Worker"""
    global expansion_worker
    if expansion_worker:
        await expansion_worker.stop()
