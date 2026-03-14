import asyncio
import json
import os
from contextlib import suppress
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from loguru import logger
from redis.exceptions import ResponseError

from app.config import settings
from app.core.redis_utils import format_redis_url_for_log, resolve_redis_password


class Event(ABC):
    """Event base class"""
    @abstractmethod
    def to_dict(self) -> dict:
        pass

class KnowledgeNodeUpdated(Event):
    def __init__(self, user_id: str, node_id: str, new_mastery: int):
        self.user_id = user_id
        self.node_id = node_id
        self.new_mastery = new_mastery
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "knowledge_node_updated",
            "user_id": self.user_id,
            "node_id": self.node_id,
            "new_mastery": self.new_mastery,
            "timestamp": self.timestamp.isoformat()
        }

class NodeMasteryUpdatedEvent(Event):
    def __init__(self, user_id: str, node_id: str, old_mastery: int, new_mastery: int, reason: str):
        self.user_id = user_id
        self.node_id = node_id
        self.old_mastery = old_mastery
        self.new_mastery = new_mastery
        self.reason = reason
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "node_mastery_updated",
            "user_id": self.user_id,
            "node_id": self.node_id,
            "old_mastery": self.old_mastery,
            "new_mastery": self.new_mastery,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }

class ErrorCreated(Event):
    def __init__(self, user_id: str, error_id: str, linked_node_ids: list[str] = None):
        self.user_id = user_id
        self.error_id = error_id
        self.linked_node_ids = linked_node_ids or []
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "error_created",
            "user_id": self.user_id,
            "error_id": self.error_id,
            "linked_node_ids": self.linked_node_ids,
            "timestamp": self.timestamp.isoformat()
        }

class TaskCompleted(Event):
    def __init__(self, user_id: str, task_id: str, estimated_minutes: int,
                 actual_minutes: int, difficulty: int, completion_rate: float,
                 user_note: str | None = None, plan_id: str | None = None,
                 source: str = "personal", source_metadata: dict[str, Any] | None = None):
        self.user_id = user_id
        self.task_id = task_id
        self.estimated_minutes = estimated_minutes
        self.actual_minutes = actual_minutes
        self.difficulty = difficulty
        self.completion_rate = completion_rate
        self.user_note = user_note
        self.plan_id = plan_id
        self.source = source
        self.source_metadata = source_metadata or {}
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "task.completed",
            "user_id": self.user_id,
            "task_id": self.task_id,
            "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes,
            "difficulty": self.difficulty,
            "completion_rate": self.completion_rate,
            "user_note": self.user_note,
            "plan_id": self.plan_id,
            "source": self.source,
            "source_metadata": self.source_metadata,
            "timestamp": self.timestamp.isoformat()
        }

class TaskAbandoned(Event):
    def __init__(self, user_id: str, task_id: str, reason: str | None = None,
                 estimated_minutes: int | None = None, time_spent: int | None = None,
                 plan_id: str | None = None):
        self.user_id = user_id
        self.task_id = task_id
        self.reason = reason
        self.estimated_minutes = estimated_minutes
        self.time_spent = time_spent
        self.plan_id = plan_id
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "task.abandoned",
            "user_id": self.user_id,
            "task_id": self.task_id,
            "reason": self.reason,
            "estimated_minutes": self.estimated_minutes,
            "time_spent": self.time_spent,
            "plan_id": self.plan_id,
            "timestamp": self.timestamp.isoformat()
        }


class ProfilePreferenceUpdated(Event):
    def __init__(
        self,
        user_id: str,
        pref_keys: list[str],
        preference_version: int,
        source: str,
    ):
        self.user_id = user_id
        self.pref_keys = pref_keys
        self.preference_version = preference_version
        self.source = source
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "profile.preference.updated",
            "user_id": self.user_id,
            "pref_keys": self.pref_keys,
            "preference_version": self.preference_version,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class ProfilePreferenceDeleted(Event):
    def __init__(
        self,
        user_id: str,
        pref_key: str,
        preference_version: int,
    ):
        self.user_id = user_id
        self.pref_key = pref_key
        self.preference_version = preference_version
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "profile.preference.deleted",
            "user_id": self.user_id,
            "pref_key": self.pref_key,
            "preference_version": self.preference_version,
            "timestamp": self.timestamp.isoformat(),
        }

class EventBus:
    """
    Event Bus - Redis Streams Implementation
    Supports asynchronous publishing and consumer groups.
    """
    def __init__(self, redis_url: str | None = None):
        # We delay connection until needed or explicitly initialized
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis: redis.Redis | None = None
        self._consumers = []
        self._consumer_tasks: list[asyncio.Task] = []
        self._running = False
        self.max_retries = getattr(settings, "EVENT_BUS_MAX_RETRIES", 3)
        self.dlq_suffix = getattr(settings, "EVENT_BUS_DLQ_SUFFIX", ":dlq")

    def _dlq_stream(self, stream: str) -> str:
        return f"{stream}{self.dlq_suffix}"

    @staticmethod
    def _serialize_stream_body(message: dict[str, Any]) -> dict[str, str]:
        msg_body: dict[str, str] = {}
        for key, value in message.items():
            if isinstance(value, (dict, list)):
                msg_body[key] = json.dumps(value, ensure_ascii=False, default=str)
            else:
                msg_body[key] = str(value)
        return msg_body

    @staticmethod
    def _extract_retry_count(message: dict[str, Any]) -> int:
        try:
            return int(message.get("_retry_count", 0) or 0)
        except (TypeError, ValueError):
            return 0

    async def _move_to_dlq(
        self,
        *,
        stream: str,
        group_name: str,
        consumer_name: str,
        message_id: str,
        parsed_data: dict[str, Any],
        error: Exception,
        retry_count: int,
    ) -> None:
        if not self.redis:
            return

        payload = {
            "event": parsed_data,
            "error": str(error),
            "stream": stream,
            "group_name": group_name,
            "consumer_name": consumer_name,
            "message_id": message_id,
            "retry_count": retry_count,
            "failed_at": datetime.now(UTC).isoformat(),
        }
        await self.redis.xadd(
            self._dlq_stream(stream),
            {"data": json.dumps(payload, ensure_ascii=False, default=str)},
        )
        await self.redis.xack(stream, group_name, message_id)
        logger.error(
            "Moved event to DLQ: stream={} group={} consumer={} message_id={} retry_count={} error={}",
            stream,
            group_name,
            consumer_name,
            message_id,
            retry_count,
            error,
        )

    async def _requeue_for_retry(
        self,
        *,
        stream: str,
        group_name: str,
        consumer_name: str,
        message_id: str,
        parsed_data: dict[str, Any],
        error: Exception,
        retry_count: int,
    ) -> None:
        if not self.redis:
            return

        next_retry = retry_count + 1
        retry_payload = dict(parsed_data)
        retry_payload["_retry_count"] = next_retry
        retry_payload["_last_error"] = str(error)
        retry_payload["_failed_consumer_group"] = group_name
        retry_payload["_failed_consumer_name"] = consumer_name
        retry_payload["_failed_at"] = datetime.now(UTC).isoformat()
        retry_payload["_original_message_id"] = parsed_data.get("_original_message_id", message_id)

        await self.redis.xadd(stream, self._serialize_stream_body(retry_payload))
        await self.redis.xack(stream, group_name, message_id)
        logger.warning(
            "Requeued failed event: stream={} group={} consumer={} message_id={} retry={}/{} error={}",
            stream,
            group_name,
            consumer_name,
            message_id,
            next_retry,
            self.max_retries,
            error,
        )

    async def _handle_failed_message(
        self,
        *,
        stream: str,
        group_name: str,
        consumer_name: str,
        message_id: str,
        parsed_data: dict[str, Any],
        error: Exception,
    ) -> None:
        retry_count = self._extract_retry_count(parsed_data)
        try:
            if retry_count >= self.max_retries:
                await self._move_to_dlq(
                    stream=stream,
                    group_name=group_name,
                    consumer_name=consumer_name,
                    message_id=message_id,
                    parsed_data=parsed_data,
                    error=error,
                    retry_count=retry_count,
                )
            else:
                await self._requeue_for_retry(
                    stream=stream,
                    group_name=group_name,
                    consumer_name=consumer_name,
                    message_id=message_id,
                    parsed_data=parsed_data,
                    error=error,
                    retry_count=retry_count,
                )
        except Exception as dlq_error:
            logger.error(
                "Failed to requeue/DLQ event: stream={} group={} message_id={} original_error={} dlq_error={}",
                stream,
                group_name,
                message_id,
                error,
                dlq_error,
            )

    async def connect(self):
        """Establish Redis connection"""
        if not self.redis:
            try:
                password, password_source = resolve_redis_password(self.redis_url, settings.REDIS_PASSWORD)
                kwargs = {
                    "encoding": "utf-8",
                    "decode_responses": True
                }
                if password:
                    kwargs["password"] = password

                self.redis = redis.from_url(
                    self.redis_url,
                    **kwargs
                )
                await self.redis.ping()
                logger.info(
                    "Successfully connected to Redis Event Bus: {}, Password={}, PasswordSource={}".format(
                        format_redis_url_for_log(self.redis_url),
                        "Yes" if password else "No",
                        password_source,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis = None

    async def close(self):
        """Close connection and stop consumers"""
        self._running = False
        for task in self._consumer_tasks:
            task.cancel()
        for task in self._consumer_tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._consumer_tasks.clear()
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Redis Event Bus connection closed")

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        """
        Publish event to Redis Stream

        Args:
            event_type: Type of the event (used as key in payload usually, but here just for logging/logic)
            payload: Dictionary data to send
            stream: Redis Stream key name

        Returns:
            Message ID if successful, None otherwise
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                logger.error("Cannot publish: Redis not connected")
                return None

        try:
            # Ensure payload implies event_type if not present, or wrap it
            message = payload.copy()
            if "event_type" not in message:
                message["event_type"] = event_type

            # Serialize complex types if necessary (Redis expects str->str dict for simpler usage)
            # We use json dumps for the whole payload or individual fields.
            # Here we dump the whole payload into a 'data' field to avoid field limitation issues,
            # or we flatten it. For simplicity and flexibility, let's put it in 'data'.
            # However, standard stream usage often puts fields directly.
            # Let's stringify values.

            msg_body = self._serialize_stream_body(message)

            # XADD
            msg_id = await self.redis.xadd(stream, msg_body)
            logger.debug(f"Published event {event_type} to {stream} with ID {msg_id}")
            return msg_id

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return None

    async def subscribe(self, stream: str, group_name: str, consumer_name: str, callback: Callable[[dict], Any]):
        """
        Start a background consumer for a consumer group.

        Args:
            stream: Redis Stream key
            group_name: Consumer Group name
            consumer_name: Unique consumer name instance
            callback: Async function to handle message payload (dict)
        """
        if not self.redis:
            await self.connect()

        # 1. Create Consumer Group if not exists
        try:
            await self.redis.xgroup_create(stream, group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group {group_name} for stream {stream}")
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {group_name} already exists")
            else:
                logger.error(f"Error creating consumer group: {e}")
                return

        # 2. Start Consumption Loop
        self._running = True
        task = asyncio.create_task(self._consume_loop(stream, group_name, consumer_name, callback))
        self._consumer_tasks.append(task)

    async def _consume_loop(self, stream: str, group_name: str, consumer_name: str, callback: Callable):
        logger.info(f"Starting consumer loop: {group_name}:{consumer_name} on {stream}")

        while self._running:
            try:
                if not self.redis:
                    await asyncio.sleep(1)
                    continue

                # Read from group
                # count=1 for processing one by one, block=5000ms
                entries = await self.redis.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream: ">"},
                    count=1,
                    block=2000
                )

                if not entries:
                    continue

                for _stream_name, messages in entries:
                    for message_id, data in messages:
                        try:
                            # Parse data (handling json strings if we did that)
                            parsed_data = {}
                            for k, v in data.items():
                                try:
                                    parsed_data[k] = json.loads(v)
                                except (json.JSONDecodeError, TypeError):
                                    parsed_data[k] = v

                            # Invoke callback
                            await callback(parsed_data)

                            # ACK
                            await self.redis.xack(stream, group_name, message_id)

                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {e}")
                            await self._handle_failed_message(
                                stream=stream,
                                group_name=group_name,
                                consumer_name=consumer_name,
                                message_id=message_id,
                                parsed_data=parsed_data,
                                error=e,
                            )

            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1) # Backoff

# Global instance
event_bus = EventBus()
