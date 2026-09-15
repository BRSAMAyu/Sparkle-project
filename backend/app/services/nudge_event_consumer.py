
from loguru import logger

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.services.nudge_service import NudgeService


class NudgeEventConsumer:
    """监听 nudge.triggered，调用 NudgeService 投递通知"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.group_name = "nudge_consumer_group"
        self.consumer_name = "nudge_worker_1"
        self._is_running = False

    async def start(self):
        """Start listening for events."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("Starting NudgeEventConsumer...")

        # Subscribe to nudge triggered event
        await self.event_bus.subscribe(
            stream="sparkle_events",
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            callback=self._handle_event
        )

    def stop(self):
        self._is_running = False

    async def _handle_event(self, event_data: dict) -> None:
        """Process incoming events."""
        event_type = event_data.get("event_type")
        if event_type == "nudge.triggered":
            await self._handle_nudge_triggered(event_data)

    async def _handle_nudge_triggered(self, event_data: dict) -> None:
        try:
            async with AsyncSessionLocal() as db:
                service = NudgeService(db)
                await service.handle_nudge_triggered(event_data)
        except Exception as e:
            logger.exception(f"Error handling nudge.triggered event: {e}")
            raise
