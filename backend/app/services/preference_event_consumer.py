"""
偏好事件消费者 - 订阅 Go 发布的偏好变更事件，使 Python 端缓存失效
"""
import asyncio
import json
import time
from uuid import UUID

from loguru import logger

from app.core.metrics import (
    CACHE_INVALIDATION_LATENCY,
    PREFERENCE_EVENT_CONSUME_LAG,
    PREFERENCE_EVENT_E2E_LATENCY,
    PREFERENCE_EVENT_ERRORS_TOTAL,
    PREFERENCE_EVENT_STREAM_LENGTH,
)
from app.services.user_service import UserService

DLQ_STREAM_SUFFIX = ":dlq"
MAX_RETRIES = 3


class PreferenceEventConsumer:
    """消费 user.preferences.updated 事件"""

    def __init__(self, redis_client, user_service: UserService):
        self.redis = redis_client
        self.user_service = user_service
        self.stream_key = "cqrs:stream:user"
        self.consumer_group = "python_preference_consumer"
        self.consumer_name = "worker-1"
        self._running = False

    def stop(self):
        """Signal the consumer to stop gracefully."""
        self._running = False

    async def start(self):
        """启动事件消费循环"""
        try:
            await self.redis.xgroup_create(
                self.stream_key,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create consumer group: {e}")

        logger.info(f"PreferenceEventConsumer started, listening on {self.stream_key}")
        self._running = True

        while self._running:
            try:
                await self._report_stream_length()

                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=10,
                    block=1000,
                )

                if not messages:
                    continue

                for _stream, entries in messages:
                    for entry_id, data in entries:
                        retry_count = int(data.get("_retry_count", 0)) if isinstance(data, dict) else 0
                        try:
                            await self._handle_event(entry_id, data)
                            await self.redis.xack(self.stream_key, self.consumer_group, entry_id)
                        except Exception as e:
                            await self._handle_failed_message(entry_id, data, e, retry_count)

            except Exception as e:
                logger.error(f"Error consuming events: {e}")
                PREFERENCE_EVENT_ERRORS_TOTAL.labels(
                    error_type=type(e).__name__,
                    consumer_group=self.consumer_group,
                ).inc()
                await asyncio.sleep(1)

    async def _handle_failed_message(
        self, entry_id: str, data: dict, error: Exception, retry_count: int,
    ) -> None:
        if retry_count < MAX_RETRIES:
            await self._requeue_for_retry(entry_id, data, error, retry_count)
        else:
            await self._move_to_dlq(entry_id, data, error, retry_count)

    async def _requeue_for_retry(
        self, entry_id: str, data: dict, error: Exception, retry_count: int,
    ) -> None:
        next_retry = retry_count + 1
        payload = dict(data) if isinstance(data, dict) else {"raw": str(data)}
        payload["_retry_count"] = next_retry
        payload["_last_error"] = str(error)
        payload["_original_message_id"] = entry_id
        await self.redis.xadd(self.stream_key, payload)
        await self.redis.xack(self.stream_key, self.consumer_group, entry_id)
        logger.warning(
            "Requeued failed preference event: entry={} retry={}/{} error={}",
            entry_id, next_retry, MAX_RETRIES, error,
        )

    async def _move_to_dlq(
        self, entry_id: str, data: dict, error: Exception, retry_count: int,
    ) -> None:
        dlq_stream = f"{self.stream_key}{DLQ_STREAM_SUFFIX}"
        dlq_payload = {
            "event": json.dumps(data, ensure_ascii=False, default=str),
            "error": str(error),
            "stream": self.stream_key,
            "group_name": self.consumer_group,
            "message_id": entry_id,
            "retry_count": retry_count,
        }
        await self.redis.xadd(dlq_stream, dlq_payload)
        await self.redis.xack(self.stream_key, self.consumer_group, entry_id)
        PREFERENCE_EVENT_ERRORS_TOTAL.labels(
            error_type="dlq",
            consumer_group=self.consumer_group,
        ).inc()
        logger.error(
            "Moved preference event to DLQ: entry={} retries={} error={}",
            entry_id, retry_count, error,
        )

    async def _report_stream_length(self):
        """报告 Redis Stream 长度"""
        try:
            length = await self.redis.xlen(self.stream_key)
            PREFERENCE_EVENT_STREAM_LENGTH.labels(
                stream_key=self.stream_key,
            ).set(length)
        except Exception:
            pass

    async def _handle_event(self, entry_id: str, data: dict):
        """处理单个事件"""
        consume_start = time.time()
        event_type = self._get_value(data, "type")

        if event_type in ("user.preferences.updated", "user.preferences.inferred"):
            try:
                payload_str = self._get_value(data, "payload") or "{}"
                payload = json.loads(payload_str)
                inner_data = json.loads(payload.get("data", "{}"))

                user_id = UUID(inner_data["user_id"])
                version = inner_data.get("preference_version")
                published_at = inner_data.get("timestamp", time.time())

                # 计算消费延迟
                consume_lag = consume_start - published_at
                PREFERENCE_EVENT_CONSUME_LAG.labels(
                    consumer_group=self.consumer_group,
                ).set(consume_lag)

                logger.info(
                    f"Received preferences update for user {user_id}, "
                    f"version={version}, lag={consume_lag:.3f}s",
                )

                # 测量缓存失效延迟
                invalidate_start = time.time()
                await self.user_service.invalidate_user_cache(user_id)
                invalidate_latency = time.time() - invalidate_start

                CACHE_INVALIDATION_LATENCY.labels(
                    cache_type="user_preferences",
                ).observe(invalidate_latency)

                # 端到端延迟
                e2e_latency = time.time() - published_at
                PREFERENCE_EVENT_E2E_LATENCY.labels(
                    event_type=event_type,
                    source="gateway",
                ).observe(e2e_latency)

            except Exception as e:
                logger.error(f"Failed to handle preferences update event: {e}")
                PREFERENCE_EVENT_ERRORS_TOTAL.labels(
                    error_type="handle_event",
                    consumer_group=self.consumer_group,
                ).inc()
                raise

    @staticmethod
    def _get_value(data: dict, key: str):
        if key in data:
            value = data[key]
            if isinstance(value, bytes):
                return value.decode()
            return value
        key_bytes = key.encode()
        if key_bytes in data:
            value = data[key_bytes]
            if isinstance(value, bytes):
                return value.decode()
            return value
        return ""
