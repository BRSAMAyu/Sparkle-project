"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass as _dataclass
from datetime import UTC, datetime
from functools import wraps
from typing import Any

import redis.asyncio as redis
from loguru import logger
from redis.exceptions import ResponseError

from app.config import settings
from app.core.metrics import (
    EVENT_BUS_CONSUMER_FAILURE_TOTAL,
    EVENT_BUS_DLQ_TOTAL,
    EVENT_BUS_PUBLISH_RETRIES_TOTAL,
)
from app.core.redis_utils import format_redis_url_for_log, resolve_redis_password
from app.db.session import AsyncSessionLocal
from app.models.event_bus_dlq import EventBusDLQEntry


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
            "timestamp": self.timestamp.isoformat(),
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
            "timestamp": self.timestamp.isoformat(),
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
            "timestamp": self.timestamp.isoformat(),
        }


@_dataclass
class GroupFileSharedEvent:
    event_type: str = "group.file.shared"
    group_id: str = ""
    file_id: str = ""
    group_file_id: str = ""
    shared_by_user_id: str = ""
    triggered_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "group_id": self.group_id,
            "file_id": self.file_id,
            "group_file_id": self.group_file_id,
            "shared_by_user_id": self.shared_by_user_id,
            "triggered_at": self.triggered_at,
        }


@_dataclass
class GroupFileDeletedEvent:
    event_type: str = "group.file.deleted"
    group_id: str = ""
    file_id: str = ""
    group_file_id: str = ""
    shared_by_user_id: str = ""
    triggered_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "group_id": self.group_id,
            "file_id": self.file_id,
            "group_file_id": self.group_file_id,
            "shared_by_user_id": self.shared_by_user_id,
            "triggered_at": self.triggered_at,
        }


@_dataclass
class MasteryUpdatedFromError:
    event_type: str = "mastery_updated_from_error"
    user_id: str = ""
    node_id: str = ""
    node_name: str = ""
    old_mastery: float = 0.0
    new_mastery: float = 0.0
    delta: float = 0.0
    error_type: str = ""
    triggered_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "old_mastery": self.old_mastery,
            "new_mastery": self.new_mastery,
            "delta": self.delta,
            "error_type": self.error_type,
            "triggered_at": self.triggered_at,
        }


class TaskCompleted(Event):
    def __init__(
        self,
        user_id: str,
        task_id: str,
        estimated_minutes: int,
        actual_minutes: int,
        difficulty: int,
        completion_rate: float,
        user_note: str | None = None,
        plan_id: str | None = None,
        source: str = "personal",
        source_metadata: dict[str, Any] | None = None,
    ):
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
            "timestamp": self.timestamp.isoformat(),
        }


class FocusSessionCompletedEvent(Event):
    def __init__(
        self,
        user_id: str,
        session_id: str,
        duration_minutes: int,
        task_id: str | None = None,
        plan_id: str | None = None,
        mastery_updates: list[dict[str, Any]] | None = None,
        started_at: str | None = None,
        completed: bool = True,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.duration_minutes = duration_minutes
        self.task_id = task_id
        self.plan_id = plan_id
        self.mastery_updates = mastery_updates or []
        self.started_at = started_at
        self.completed = completed
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "focus.session.completed",
            "user_id": self.user_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "duration_minutes": self.duration_minutes,
            "mastery_updates": self.mastery_updates,
            "started_at": self.started_at,
            "completed": self.completed,
            "timestamp": self.timestamp.isoformat(),
        }


class TaskAbandoned(Event):
    def __init__(
        self,
        user_id: str,
        task_id: str,
        reason: str | None = None,
        estimated_minutes: int | None = None,
        time_spent: int | None = None,
        plan_id: str | None = None,
    ):
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
            "timestamp": self.timestamp.isoformat(),
        }


class TaskStartedEvent(Event):
    def __init__(
        self,
        user_id: str,
        task_id: str,
        plan_id: str | None = None,
        source: str = "task_service",
    ):
        self.user_id = user_id
        self.task_id = task_id
        self.plan_id = plan_id
        self.source = source
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "task.started",
            "user_id": self.user_id,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class TaskStuckEvent(Event):
    def __init__(
        self,
        user_id: str,
        task_id: str,
        plan_id: str | None = None,
        stuck_point: str | None = None,
        recent_steps: list[str] | None = None,
        elapsed_seconds: int | None = None,
        diagnosis: dict[str, Any] | None = None,
    ):
        self.user_id = user_id
        self.task_id = task_id
        self.plan_id = plan_id
        self.stuck_point = stuck_point
        self.recent_steps = recent_steps or []
        self.elapsed_seconds = elapsed_seconds
        self.diagnosis = diagnosis or {}
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "task.stuck",
            "user_id": self.user_id,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "stuck_point": self.stuck_point,
            "recent_steps": self.recent_steps,
            "elapsed_seconds": self.elapsed_seconds,
            "diagnosis": self.diagnosis,
            "timestamp": self.timestamp.isoformat(),
        }


class PlanCreatedEvent(Event):
    def __init__(
        self,
        user_id: str,
        plan_id: str,
        evidence_id: str | None = None,
        source: str = "discovery_manager",
        metadata: dict[str, Any] | None = None,
    ):
        self.user_id = user_id
        self.plan_id = plan_id
        self.evidence_id = evidence_id
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "plan.created",
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "evidence_id": self.evidence_id,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class UserRegisteredEvent(Event):
    def __init__(
        self,
        user_id: str,
        username: str,
        registration_source: str = "email",
        metadata: dict[str, Any] | None = None,
    ):
        self.user_id = user_id
        self.username = username
        self.registration_source = registration_source
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "user.registered",
            "user_id": self.user_id,
            "username": self.username,
            "registration_source": self.registration_source,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class ReflectionCompletedEvent(Event):
    def __init__(
        self,
        user_id: str,
        feedback_id: str,
        task_id: str,
        plan_id: str | None = None,
        source: str = "task_reflection_service",
    ):
        self.user_id = user_id
        self.feedback_id = feedback_id
        self.task_id = task_id
        self.plan_id = plan_id
        self.source = source
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "reflection.completed",
            "user_id": self.user_id,
            "feedback_id": self.feedback_id,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class SRLPhaseTransitionEvent(Event):
    def __init__(
        self,
        user_id: str,
        trigger_event_type: str,
        evidence_id: str,
        metadata: dict[str, Any] | None = None,
        published_at: str | None = None,
    ):
        self.user_id = user_id
        self.trigger_event_type = trigger_event_type
        self.evidence_id = evidence_id
        self.metadata = metadata or {}
        self.published_at = published_at or datetime.now(UTC).isoformat()
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "srl.phase.transition",
            "user_id": self.user_id,
            "trigger_event_type": self.trigger_event_type,
            "evidence_id": self.evidence_id,
            "metadata": self.metadata,
            "published_at": self.published_at,
            "timestamp": self.timestamp.isoformat(),
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


class TraitObserved(Event):
    def __init__(
        self,
        user_id: str,
        evidence_id: str,
        source: str,
    ):
        self.user_id = user_id
        self.evidence_id = evidence_id
        self.source = source
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "trait_observed",
            "user_id": self.user_id,
            "evidence_id": self.evidence_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class TraitsColdstartCompleted(Event):
    def __init__(
        self,
        user_id: str,
        completed_at: str,
    ):
        self.user_id = user_id
        self.completed_at = completed_at
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "coldstart_completed",
            "user_id": self.user_id,
            "completed_at": self.completed_at,
            "timestamp": self.timestamp.isoformat(),
        }


class CalendarEventCreated(Event):
    """日历事件创建"""

    def __init__(
        self,
        user_id: str,
        event_id: str,
        title: str,
        start_time: datetime,
        source: str = "manual",
    ):
        self.user_id = user_id
        self.event_id = event_id
        self.title = title
        self.start_time = start_time
        self.source = source
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "calendar.event.created",
            "user_id": self.user_id,
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class CalendarEventUpdated(Event):
    """日历事件更新"""

    def __init__(
        self,
        user_id: str,
        event_id: str,
        changes: dict,
    ):
        self.user_id = user_id
        self.event_id = event_id
        self.changes = changes
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "calendar.event.updated",
            "user_id": self.user_id,
            "event_id": self.event_id,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
        }


class CalendarEventDeleted(Event):
    """日历事件删除"""

    def __init__(
        self,
        user_id: str,
        event_id: str,
        hard_delete: bool = False,
    ):
        self.user_id = user_id
        self.event_id = event_id
        self.hard_delete = hard_delete
        self.timestamp = datetime.now(UTC)

    def to_dict(self):
        return {
            "event_type": "calendar.event.deleted",
            "user_id": self.user_id,
            "event_id": self.event_id,
            "hard_delete": self.hard_delete,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Card Protocol Events (Phase 1)
# NOTE: Card/Occurrence/Intervention events removed — zero publishers.
# Re-add when Card Protocol Phase 1 publishers are implemented.
# Reference: docs/product/SPARKLE_CARD_PROTOCOL_TAXONOMY_2026-04-02.md
# ---------------------------------------------------------------------------


class DocumentCitationFeedbackEvent(Event):
    """Document citation feedback published by explicit UI actions or implicit turn heuristics."""

    def __init__(
        self,
        *,
        user_id: str,
        file_id: str,
        chunk_id: str | None,
        query_type: str | None,
        rating: int,
        feedback_source: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        self.user_id = user_id
        self.file_id = file_id
        self.chunk_id = chunk_id
        self.query_type = query_type
        self.rating = rating
        self.feedback_source = feedback_source
        self.conversation_id = conversation_id
        self.context = context or {}
        self.timestamp = datetime.now(UTC)

    @property
    def event_type(self) -> str:
        return "document.citation.feedback"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "file_id": self.file_id,
            "chunk_id": self.chunk_id,
            "query_type": self.query_type,
            "rating": self.rating,
            "feedback_source": self.feedback_source,
            "conversation_id": self.conversation_id,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """
    Event Bus - Redis Streams Implementation
    Supports asynchronous publishing and consumer groups.
    """

    def __init__(self, redis_url: str | None = None):
        # We delay connection until needed or explicitly initialized
        self.redis_url = redis_url or os.getenv("REDIS_URL") or settings.REDIS_URL
        self.redis: redis.Redis | None = None
        self._consumers = []
        self._consumer_tasks: list[asyncio.Task] = []
        self._running = False
        self.max_retries = getattr(settings, "EVENT_BUS_MAX_RETRIES", 3)
        self.publish_base_delay_ms = getattr(settings, "EVENT_BUS_PUBLISH_BASE_DELAY_MS", 200)
        self.publish_max_delay_ms = getattr(settings, "EVENT_BUS_PUBLISH_MAX_DELAY_MS", 2000)
        self.consumer_retry_base_delay_ms = getattr(
            settings,
            "EVENT_BUS_CONSUMER_RETRY_BASE_DELAY_MS",
            self.publish_base_delay_ms,
        )
        self.consumer_retry_max_delay_ms = getattr(
            settings,
            "EVENT_BUS_CONSUMER_RETRY_MAX_DELAY_MS",
            self.publish_max_delay_ms,
        )
        self.dlq_suffix = getattr(settings, "EVENT_BUS_DLQ_SUFFIX", ":dlq")
        self.dlq_maxlen = getattr(settings, "EVENT_BUS_DLQ_MAXLEN", 10000)
        self.dlq_enabled = bool(getattr(settings, "EVENT_BUS_DLQ_ENABLED", True))
        self.pending_retry_idle_ms = getattr(settings, "EVENT_BUS_PENDING_RETRY_IDLE_MS", 5000)
        self.retry_stream_maxlen = getattr(
            settings,
            "EVENT_BUS_RETRY_STREAM_MAXLEN",
            getattr(settings, "EVENT_BUS_STREAM_MAXLEN", 50000),
        )
        # Idempotency store for deduplication
        self._idempotency = None  # Lazy initialized

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

    @staticmethod
    def _consumer_label(callback: Callable[..., Any], consumer_name: str) -> str:
        label = getattr(callback, "__event_bus_consumer_name__", None)
        if isinstance(label, str) and label.strip():
            return label.strip()
        return consumer_name

    async def _persist_dlq_entry(
        self,
        *,
        stream: str,
        group_name: str,
        consumer_name: str,
        message_id: str,
        parsed_data: dict[str, Any],
        error: Exception,
        retry_count: int,
        failure_stage: str,
    ) -> None:
        if not self.dlq_enabled:
            return

        raw_user_id = parsed_data.get("user_id")
        user_id = None
        if raw_user_id:
            try:
                from uuid import UUID

                user_id = UUID(str(raw_user_id))
            except (TypeError, ValueError):
                user_id = None

        async with AsyncSessionLocal() as db:
            db.add(
                EventBusDLQEntry(
                    stream=stream,
                    event_type=str(parsed_data.get("event_type") or "unknown"),
                    user_id=user_id,
                    group_name=group_name,
                    consumer_name=consumer_name,
                    message_id=message_id,
                    retry_count=retry_count,
                    failure_stage=failure_stage,
                    error=str(error),
                    payload=dict(parsed_data),
                )
            )
            await db.commit()

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
        if self.redis:
            await self.redis.xadd(
                self._dlq_stream(stream),
                {"data": json.dumps(payload, ensure_ascii=False, default=str)},
                maxlen=self.dlq_maxlen,
            )
        await self._persist_dlq_entry(
            stream=stream,
            group_name=group_name,
            consumer_name=consumer_name,
            message_id=message_id,
            parsed_data=parsed_data,
            error=error,
            retry_count=retry_count,
            failure_stage="consume",
        )
        EVENT_BUS_DLQ_TOTAL.labels(event_type=str(parsed_data.get("event_type") or "unknown")).inc()
        # Ack AFTER DLQ write succeeds — safe because DLQ has captured the event.
        if self.redis:
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

        # Requeue FIRST, then ack. If ack fails the message may be
        # reprocessed (idempotent consumers handle this), but the
        # retry payload is never lost.
        await self.redis.xadd(
            stream,
            self._serialize_stream_body(retry_payload),
            maxlen=self.retry_stream_maxlen,
        )
        await self.redis.xack(stream, group_name, message_id)
        delay_ms = min(self.consumer_retry_base_delay_ms * (2**retry_count), self.consumer_retry_max_delay_ms)
        logger.warning(
            "Requeued failed event: stream={} group={} consumer={} message_id={} retry={}/{} delay_ms={} error={}",
            stream,
            group_name,
            consumer_name,
            message_id,
            next_retry,
            self.max_retries,
            delay_ms,
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
            # Best-effort ack to prevent permanent pending messages
            try:
                if self.redis:
                    await self.redis.xack(stream, group_name, message_id)
            except Exception as ack_err:
                logger.error("Failed to ack after DLQ failure: {}", ack_err)
            logger.error(
                "Failed to requeue/DLQ event: stream={} group={} message_id={} original_error={} dlq_error={}",
                stream,
                group_name,
                message_id,
                error,
                dlq_error,
            )

    async def _publish_once(self, event_type: str, payload: dict[str, Any], stream: str) -> str:
        if not self.redis:
            await self.connect()
            if not self.redis:
                raise RuntimeError("redis_not_connected")

        message = payload.copy()
        if "event_type" not in message:
            message["event_type"] = event_type

        maxlen = getattr(
            settings,
            "EVENT_BUS_STREAM_MAXLEN",
            50000,
        )
        return await self.redis.xadd(
            stream,
            self._serialize_stream_body(message),
            maxlen=maxlen,
            approximate=True,
        )

    async def connect(self):
        """Establish Redis connection"""
        if not self.redis:
            try:
                password, password_source = resolve_redis_password(self.redis_url, settings.REDIS_PASSWORD)
                kwargs = {"encoding": "utf-8", "decode_responses": True}
                if password:
                    kwargs["password"] = password

                self.redis = redis.from_url(self.redis_url, **kwargs)
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
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                msg_id = await self._publish_once(event_type, payload, stream)
                logger.debug(f"Published event {event_type} to {stream} with ID {msg_id}")
                return msg_id
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                EVENT_BUS_PUBLISH_RETRIES_TOTAL.labels(event_type=event_type).inc()
                delay_ms = min(self.publish_base_delay_ms * (2**attempt), self.publish_max_delay_ms)
                logger.warning(
                    "Retrying event publish: event_type={} stream={} attempt={}/{} delay_ms={} error={}",
                    event_type,
                    stream,
                    attempt + 1,
                    self.max_retries,
                    delay_ms,
                    exc,
                )
                await asyncio.sleep(delay_ms / 1000)

        logger.error(f"Failed to publish event {event_type}: {last_error}")
        if self.dlq_enabled:
            try:
                await self._persist_dlq_entry(
                    stream=stream,
                    group_name="publisher",
                    consumer_name="event_bus.publish",
                    message_id="publish-failure",
                    parsed_data=dict(payload or {}, event_type=payload.get("event_type") or event_type),
                    error=last_error or RuntimeError("unknown_publish_error"),
                    retry_count=self.max_retries,
                    failure_stage="publish",
                )
                EVENT_BUS_DLQ_TOTAL.labels(event_type=event_type).inc()
            except Exception as dlq_exc:
                logger.error("Failed to persist publish failure DLQ entry for {}: {}", event_type, dlq_exc)
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

    async def _get_idempotency_store(self):
        """Lazy initialization of idempotency store"""
        if self._idempotency is None:
            from app.core.idempotency import get_idempotency_store

            self._idempotency = get_idempotency_store("redis")
        return self._idempotency

    async def _claim_stale_messages(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        if not self.redis:
            return []
        try:
            # redis-py 7.0+ returns (next_id, messages, deleted_ids)
            result = await self.redis.xautoclaim(
                stream,
                group_name,
                consumer_name,
                min_idle_time=self.pending_retry_idle_ms,
                start_id="0-0",
                count=10,
            )
            next_id, messages = result[0], result[1]
            if next_id:
                _ = next_id
            return list(messages or [])
        except ResponseError:
            return []

    async def _process_stream_message(
        self,
        *,
        stream: str,
        group_name: str,
        consumer_name: str,
        callback: Callable[[dict], Any],
        message_id: str,
        data: dict[str, Any],
    ) -> None:
        parsed_data: dict[str, Any] = {}
        try:
            for key, value in data.items():
                try:
                    parsed_data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_data[key] = value

            idempotency_key = f"evt:{stream}:{message_id}"
            idempotency = await self._get_idempotency_store()
            existing = await idempotency.get(idempotency_key)
            if existing:
                logger.info(f"Skipping duplicate message: {message_id}")
                await self.redis.xack(stream, group_name, message_id)
                return

            if not await idempotency.lock(idempotency_key):
                logger.warning(f"Could not acquire lock for message: {message_id}")
                return

            try:
                await callback(parsed_data)
                await idempotency.set(idempotency_key, {"status": "done"}, ttl=86400)
                await self.redis.xack(stream, group_name, message_id)
            except Exception:
                await idempotency.unlock(idempotency_key)
                raise
        except Exception as exc:
            label = self._consumer_label(callback, consumer_name)
            EVENT_BUS_CONSUMER_FAILURE_TOTAL.labels(consumer=label).inc()
            logger.error(f"Error processing message {message_id}: {exc}")
            await self._handle_failed_message(
                stream=stream,
                group_name=group_name,
                consumer_name=label,
                message_id=message_id,
                parsed_data=parsed_data,
                error=exc,
            )

    async def _consume_loop(self, stream: str, group_name: str, consumer_name: str, callback: Callable):
        logger.info(f"Starting consumer loop: {group_name}:{consumer_name} on {stream}")

        while self._running:
            try:
                if not self.redis:
                    await asyncio.sleep(1)
                    continue

                # Process stale messages first (from crashed/slow consumers)
                stale_messages = await self._claim_stale_messages(stream, group_name, consumer_name)
                if stale_messages:
                    for msg_id, msg_data in stale_messages:
                        await self._process_stream_message(
                            stream=stream,
                            group_name=group_name,
                            consumer_name=consumer_name,
                            callback=callback,
                            message_id=msg_id,
                            data=msg_data,
                        )

                # Always try to read new messages (non-blocking)
                entries = await self.redis.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream: ">"},
                    count=1,
                    block=2000,
                )

                if not entries:
                    continue

                for _stream_name, messages in entries:
                    for message_id, data in messages:
                        await self._process_stream_message(
                            stream=stream,
                            group_name=group_name,
                            consumer_name=consumer_name,
                            callback=callback,
                            message_id=message_id,
                            data=data,
                        )

            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                # R5-P2-20: Attempt Redis reconnection on connection errors
                if "ConnectionError" in type(e).__name__ or "connection" in str(e).lower():
                    try:
                        await self.connect()
                        logger.info("EventBus consumer reconnected to Redis")
                    except Exception as rc_err:
                        logger.warning(f"EventBus reconnection failed: {rc_err}")
                await asyncio.sleep(1)  # Backoff

    async def get_dlq_stats(self, stream: str = "sparkle_events") -> dict[str, Any]:
        """
        Get statistics about the Dead Letter Queue for a stream.

        Returns:
            dict with keys: dlq_stream, message_count, oldest_message_age_seconds
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return {"error": "Redis not connected", "dlq_stream": self._dlq_stream(stream)}

        dlq_stream = self._dlq_stream(stream)
        try:
            info = await self.redis.xinfo_stream(dlq_stream)
            message_count = info.get("length", 0)

            oldest_age_seconds = 0
            if message_count > 0:
                first_entry = await self.redis.xrange(dlq_stream, count=1)
                if first_entry:
                    message_id = first_entry[0][0]
                    timestamp_ms = int(message_id.split("-")[0])
                    oldest_age_seconds = (datetime.now(UTC).timestamp() * 1000 - timestamp_ms) / 1000

            return {
                "dlq_stream": dlq_stream,
                "message_count": message_count,
                "oldest_message_age_seconds": round(oldest_age_seconds, 2),
            }
        except ResponseError as e:
            if "no such key" in str(e).lower():
                return {
                    "dlq_stream": dlq_stream,
                    "message_count": 0,
                    "oldest_message_age_seconds": 0,
                }
            logger.error(f"Failed to get DLQ stats: {e}")
            return {"error": str(e), "dlq_stream": dlq_stream}

    async def get_consumer_lag(self, stream: str = "sparkle_events", group_name: str | None = None) -> dict[str, Any]:
        """
        Get consumer lag information for a stream and optionally a specific group.

        Returns:
            dict with keys: stream, groups (list of group info with lag details)
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return {"error": "Redis not connected", "stream": stream}

        try:
            stream_info = await self.redis.xinfo_stream(stream)
            last_generated_id = stream_info.get("last-generated-id", "0-0")

            try:
                last_generated_ms = int(last_generated_id.split("-")[0])
            except (ValueError, IndexError):
                last_generated_ms = 0

            groups_info = await self.redis.xinfo_groups(stream)
            groups = []

            for group in groups_info:
                group_name_actual = group.get("name", "unknown")
                if group_name and group_name_actual != group_name:
                    continue

                pending = group.get("pending", 0)
                last_delivered_id = group.get("last-delivered-id", "0-0")

                try:
                    last_delivered_ms = int(last_delivered_id.split("-")[0])
                except (ValueError, IndexError):
                    last_delivered_ms = 0

                lag_ms = last_generated_ms - last_delivered_ms if last_generated_ms > last_delivered_ms else 0
                if last_delivered_id == "0-0":
                    lag_ms = 0

                groups.append(
                    {
                        "name": group_name_actual,
                        "consumers": group.get("consumers", 0),
                        "pending_messages": pending,
                        "last_delivered_id": last_delivered_id,
                        "lag_messages": 0 if last_delivered_id == last_generated_id else pending,
                        "lag_time_seconds": round(lag_ms / 1000, 2) if lag_ms > 0 else 0,
                    }
                )

            return {
                "stream": stream,
                "stream_length": stream_info.get("length", 0),
                "last_generated_id": last_generated_id,
                "groups": groups,
            }
        except ResponseError as e:
            if "no such key" in str(e).lower():
                return {
                    "stream": stream,
                    "stream_length": 0,
                    "last_generated_id": "0-0",
                    "groups": [],
                    "error": "stream not found",
                }
            logger.error(f"Failed to get consumer lag: {e}")
            return {"error": str(e), "stream": stream}


# Global instance
event_bus = EventBus()


def reliable_consumer(consumer_name: str | None = None):
    """Mark a callback as a reliable consumer for Rule AZ enforcement."""

    def decorator(func):
        label = consumer_name or getattr(func, "__qualname__", getattr(func, "__name__", "consumer"))

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper.__event_bus_reliable_consumer__ = True
        wrapper.__event_bus_consumer_name__ = label
        return wrapper

    return decorator


class EventBusReliablePublisher:
    """Thin compatibility layer for governed EventBus publishing."""

    def __init__(self, bus: EventBus):
        self._bus = bus

    async def publish(self, event_type: str, payload: dict[str, Any], stream: str = "sparkle_events") -> str | None:
        return await self._bus.publish(event_type, payload, stream=stream)


event_bus_reliable = EventBusReliablePublisher(event_bus)



@_dataclass
class InterventionRecorded:
    event_type: str = "intervention_recorded"
    user_id: str = ""
    intervention_id: str = ""
    intervention_type: str = ""
    triggered_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "intervention_id": self.intervention_id,
            "intervention_type": self.intervention_type,
            "triggered_at": self.triggered_at,
        }


@_dataclass
class InterventionOutcomeRecorded:
    event_type: str = "intervention_outcome_recorded"
    user_id: str = ""
    intervention_id: str = ""
    effective: bool | None = None
    status: str = ""
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "intervention_id": self.intervention_id,
            "effective": self.effective,
            "status": self.status,
            "checked_at": self.checked_at,
        }
