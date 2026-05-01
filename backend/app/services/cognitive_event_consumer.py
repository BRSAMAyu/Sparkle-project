from uuid import UUID

from loguru import logger
from redis.asyncio import Redis

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.services.cognitive_service import CognitiveService

class CognitiveEventConsumer:
    """Consumer for cognitive events, like fragment creation."""

    def __init__(self, event_bus: EventBus, redis_client: Redis):
        self.event_bus = event_bus
        self.redis = redis_client
        self.group_name = "cognitive_consumer_group"
        self.consumer_name = "cognitive_worker_1"
        self.max_analysis_per_5m = 3
        self._is_running = False

    async def start(self):
        """Start listening for events."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("Starting CognitiveEventConsumer...")

        # Subscribe to fragment creation
        await self.event_bus.subscribe(
            stream="sparkle_events",
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            callback=self._handle_event
        )

    async def _handle_event(self, event_data: dict) -> None:
        """Process incoming events."""
        event_type = event_data.get("event_type")
        if event_type == "cognitive.fragment.created":
            await self._handle_fragment_created(event_data)

    async def _handle_fragment_created(self, event_data: dict) -> None:
        """Handle new fragment creation event and trigger analysis."""
        user_id_str = event_data.get("user_id")
        fragment_id_str = event_data.get("fragment_id")

        if not user_id_str or not fragment_id_str:
            logger.error(f"Missing required fields in cognitive.fragment.created event: {event_data}")
            return

        try:
            user_id = UUID(user_id_str)
            fragment_id = UUID(fragment_id_str)
        except ValueError as e:
            logger.error(f"Invalid UUID in cognitive.fragment.created event: {e}")
            return

        # Rate limiting: Same user max 3 fragments per 5 minutes
        rate_key = f"rate_limit:cognitive_analysis:{user_id}"
        current_count = await self.redis.get(rate_key)

        if current_count and int(current_count) >= self.max_analysis_per_5m:
            logger.warning(f"Rate limit exceeded for user {user_id} cognitive analysis. Skipping fragment {fragment_id}.")
            return

        # Increment and set TTL if new
        pipe = self.redis.pipeline()
        pipe.incr(rate_key)
        if not current_count:
            pipe.expire(rate_key, 300) # 5 minutes
        await pipe.execute()

        # Trigger analysis
        try:
            async with AsyncSessionLocal() as db:
                cognitive_service = CognitiveService(db)
                result = await cognitive_service.analyze_behavior(user_id, fragment_id)
                if result and "error" in result:
                     logger.error(f"Analysis failed for fragment {fragment_id}: {result['error']}")
        except Exception as e:
            logger.exception(f"Error during fragment analysis for {fragment_id}: {e}")
            # The DLQ mechanism of EventBus will handle failures if the callback raises
            raise
