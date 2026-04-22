from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.core.metrics import JOURNEY_EVENT_CONSUMER_ERROR_TOTAL
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class JourneyPayloadSecurityError(RuntimeError):
    """Raised when a journey payload does not match the claimed user scope."""


class JourneyEventConsumerBase:
    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "journey_event_consumer"
    EVENT_TYPE = ""
    CONSUMER_NAME_PREFIX = "journey"
    CONSUMER_LABEL = "journey"

    def __init__(self, event_bus: EventBus, redis_client=None):
        self.event_bus = event_bus
        self.redis = redis_client or cache_service.redis
        self._running = False

    async def start(self) -> None:
        mode = await AuroraStage34KillSwitchService().get_feature_mode("journey_subscribers")
        if mode == "off":
            logger.info("{} skipped because Stage34 journey subscribers are off", self.CONSUMER_LABEL)
            return

        await self.event_bus.connect()
        self._running = True
        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"{self.CONSUMER_NAME_PREFIX}-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error("{} subscription failed: {}", self.CONSUMER_LABEL, exc)
                await asyncio.sleep(1)

    async def handle_event(self, event: dict) -> None:
        if str(event.get("event_type") or "").strip() != self.EVENT_TYPE:
            return

        raw_user_id = event.get("user_id")
        user_id = self._normalize_user_id(raw_user_id)
        if user_id is None:
            JOURNEY_EVENT_CONSUMER_ERROR_TOTAL.labels(
                consumer=self.CONSUMER_LABEL,
                event=self.EVENT_TYPE,
            ).inc()
            logger.warning("{} discarded event without valid user_id: {}", self.CONSUMER_LABEL, event)
            return

        try:
            await self._process_event(event, user_id)
        except JourneyPayloadSecurityError as exc:
            JOURNEY_EVENT_CONSUMER_ERROR_TOTAL.labels(
                consumer=self.CONSUMER_LABEL,
                event=self.EVENT_TYPE,
            ).inc()
            logger.warning("{} rejected suspicious payload for user {}: {}", self.CONSUMER_LABEL, user_id, exc)
        except Exception as exc:
            JOURNEY_EVENT_CONSUMER_ERROR_TOTAL.labels(
                consumer=self.CONSUMER_LABEL,
                event=self.EVENT_TYPE,
            ).inc()
            logger.error("{} failed for user {}: {}", self.CONSUMER_LABEL, user_id, exc)
            await self._emit_failure_update(user_id, exc)

    async def _emit_failure_update(self, user_id: UUID, exc: Exception) -> None:
        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="journey_consumer_error",
                category="system",
                title="系统正在补齐你的旅程数据",
                description=(
                    "有一条初始化/规划事件暂时没有处理成功，系统会保留你的进度并自动重试。"
                ),
                priority="medium",
                metadata={
                    "consumer": self.CONSUMER_LABEL,
                    "event_type": self.EVENT_TYPE,
                    "error": str(exc),
                    "stage": "stage34",
                },
            ),
        )

    @staticmethod
    def _normalize_user_id(value: object) -> UUID | None:
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    async def _process_event(self, event: dict, user_id: UUID) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        self._running = False
