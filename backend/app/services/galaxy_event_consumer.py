"""
Galaxy 事件消费者 - 处理错题创建事件
"""
import asyncio
from datetime import datetime

from loguru import logger

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.services.galaxy_service import GalaxyService


class GalaxyEventConsumer:
    """消费 error.created 事件，更新知识节点掌握度"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "galaxy_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        """启动事件消费循环"""
        await self.event_bus.connect()
        self._running = True

        logger.info(f"GalaxyEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                # 使用 event_bus 的订阅机制
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"galaxy-{datetime.utcnow().timestamp()}",
                    callback=self.handle_event
                )
                break  # subscribe 内部是循环，成功后跳出
            except Exception as e:
                logger.error(f"GalaxyEventConsumer error: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        """处理单个事件"""
        event_type = event.get("event_type")

        if event_type == "error_created":
            await self._handle_error_created(event)

    async def _handle_error_created(self, event: dict):
        """处理错题创建事件 - 降低关联节点掌握度"""
        try:
            user_id = event.get("user_id")
            linked_node_ids = event.get("linked_node_ids", [])

            if not user_id or not linked_node_ids:
                return

            async with AsyncSessionLocal() as db:
                galaxy_service = GalaxyService(db)
                await galaxy_service.handle_error_created(event)

            logger.info(f"Processed error_created for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to handle error_created: {e}")

    def stop(self):
        """停止消费者"""
        self._running = False
