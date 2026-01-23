"""
Task 事件消费者 - 处理任务完成/放弃事件，分析行为模式
"""
import asyncio
from uuid import UUID, uuid4
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.services.cognitive_service import CognitiveService
from app.db.session import AsyncSessionLocal


class TaskEventConsumer:
    """消费 task.completed 和 task.abandoned 事件"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "task_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        """启动事件消费循环"""
        await self.event_bus.connect()
        self._running = True

        logger.info(f"TaskEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"task-{datetime.utcnow().timestamp()}",
                    callback=self.handle_event
                )
                break
            except Exception as e:
                logger.error(f"TaskEventConsumer error: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        """处理单个事件"""
        event_type = event.get("event_type")

        if event_type == "task.completed":
            await self._handle_task_completed(event)
        elif event_type == "task.abandoned":
            await self._handle_task_abandoned(event)

    async def _handle_task_completed(self, event: dict):
        """处理任务完成 - 分析时间估算偏差"""
        try:
            user_id = UUID(event["user_id"])
            task_id = UUID(event["task_id"])

            async with AsyncSessionLocal() as db:
                cognitive_service = CognitiveService(db)

                # 检测规划乐观偏差
                estimated = event.get("estimated_minutes", 0)
                actual = event.get("actual_minutes", 0)
                completion_rate = actual / estimated if estimated > 0 else 1.0

                # 如果实际时间明显超过预估，创建分析片段
                if completion_rate > 1.3:  # 超过30%
                    content = (
                        f"任务完成时间偏差: 预估{estimated}分钟, 实际{actual}分钟"
                    )
                    # 生成唯一的事件ID用于幂等性保护
                    source_event_id = f"task_completed:{task_id}"
                    await cognitive_service.create_fragment(
                        user_id=user_id,
                        content=content,
                        source_type="task_completion",
                        context_tags={
                            "task_id": str(task_id),
                            "estimated_minutes": estimated,
                            "actual_minutes": actual,
                            "completion_rate": completion_rate
                        },
                        error_tags=["planning.underestimate"] if completion_rate > 1.5 else None,
                        severity=2 if completion_rate > 1.5 else 1,
                        task_id=task_id,
                        source_event_id=source_event_id  # 幂等性保护
                    )
                    logger.info(f"Created time estimation fragment for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to handle task.completed: {e}")

    async def _handle_task_abandoned(self, event: dict):
        """处理任务放弃 - 分析放弃原因"""
        try:
            user_id = UUID(event["user_id"])
            task_id = UUID(event["task_id"])

            async with AsyncSessionLocal() as db:
                cognitive_service = CognitiveService(db)

                content = f"任务放弃: {event.get('reason', '未指定原因')}"
                # 生成唯一的事件ID用于幂等性保护
                source_event_id = f"task_abandoned:{task_id}"
                await cognitive_service.create_fragment(
                    user_id=user_id,
                    content=content,
                    source_type="task_abandon",
                    context_tags={
                        "task_id": str(task_id),
                        "reason": event.get("reason"),
                        "time_spent": event.get("time_spent")
                    },
                    error_tags=["execution.abandonment"],
                    severity=2,
                    task_id=task_id,
                    source_event_id=source_event_id  # 幂等性保护
                )
                logger.info(f"Created task abandonment fragment for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to handle task.abandoned: {e}")

    def stop(self):
        """停止消费者"""
        self._running = False

