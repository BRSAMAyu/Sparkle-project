from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser
from app.core.event_bus import event_bus
from app.core.metrics import (
    EVENT_BUS_CONSUMER_LAG_MESSAGES,
    EVENT_BUS_CONSUMER_LAG_SECONDS,
    EVENT_BUS_DLQ_MESSAGES,
)
from app.middleware.admin_audit import audit_admin_action
from app.schemas.dlq import (
    EventBusDlqEntry,
    EventBusDlqListResponse,
    EventBusDlqReplayRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/event-bus", tags=["Event Bus Health"])


def _parse_dlq_message(message_id: str, data: dict) -> EventBusDlqEntry | None:
    payload_raw = data.get("data")
    try:
        payload = json.loads(payload_raw) if payload_raw else {}
    except json.JSONDecodeError:
        return None

    event = payload.get("event", {})
    return EventBusDlqEntry(
        message_id=message_id,
        stream=payload.get("stream", "unknown"),
        event_type=event.get("event_type", "unknown"),
        user_id=event.get("user_id"),
        group_name=payload.get("group_name", "unknown"),
        consumer_name=payload.get("consumer_name", "unknown"),
        retry_count=payload.get("retry_count", 0),
        failure_stage=payload.get("failure_stage", "consume"),
        error=payload.get("error", ""),
        payload=event,
        failed_at=payload.get("failed_at"),
    )


@router.get("/health", response_model=dict[str, Any])
async def get_event_bus_health(
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    try:
        await event_bus.connect()

        dlq_stats = await event_bus.get_dlq_stats("sparkle_events")
        consumer_lag = await event_bus.get_consumer_lag("sparkle_events")

        EVENT_BUS_DLQ_MESSAGES.labels(stream="sparkle_events").set(dlq_stats.get("message_count", 0))

        for group in consumer_lag.get("groups", []):
            group_name = group.get("name", "unknown")
            EVENT_BUS_CONSUMER_LAG_MESSAGES.labels(stream="sparkle_events", consumer_group=group_name).set(
                group.get("lag_messages", 0)
            )
            EVENT_BUS_CONSUMER_LAG_SECONDS.labels(stream="sparkle_events", consumer_group=group_name).set(
                group.get("lag_time_seconds", 0)
            )

        is_healthy = dlq_stats.get("message_count", 0) < 100 and all(
            g.get("lag_messages", 0) < 1000 for g in consumer_lag.get("groups", [])
        )

        return {
            "status": "healthy" if is_healthy else "degraded",
            "stream": "sparkle_events",
            "dlq": dlq_stats,
            "consumer_lag": consumer_lag,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Event bus health check failed: {e}",
        ) from e


@router.get("/dlq", response_model=dict[str, Any])
async def get_dlq_details(
    stream: str = "sparkle_events",
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    await event_bus.connect()
    return await event_bus.get_dlq_stats(stream)


@router.get("/dlq/entries", response_model=EventBusDlqListResponse)
@audit_admin_action(category="dlq_inspection", risk="medium", action="list_event_bus_dlq")
async def list_event_bus_dlq(
    stream: str = "sparkle_events",
    limit: int = 50,
    _admin=Depends(get_current_active_superuser),
) -> EventBusDlqListResponse:
    if limit > 500:
        limit = 500
    await event_bus.connect()
    if not event_bus.redis:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable")

    dlq_stream = event_bus._dlq_stream(stream)
    entries_raw = await event_bus.redis.xrevrange(dlq_stream, count=limit)
    entries: list[EventBusDlqEntry] = []
    for message_id, data in entries_raw:
        parsed = _parse_dlq_message(message_id, data)
        if parsed is not None:
            entries.append(parsed)

    return EventBusDlqListResponse(
        entries=entries,
        total=len(entries),
        stream=dlq_stream,
    )


@router.post("/dlq/replay", response_model=dict[str, Any])
@audit_admin_action(category="dlq_replay", risk="high", action="replay_event_bus_dlq")
async def replay_event_bus_dlq(
    request: EventBusDlqReplayRequest,
    admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    if request.approver_id == str(admin.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approver must differ from admin")

    await event_bus.connect()
    if not event_bus.redis:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable")

    dlq_stream = event_bus._dlq_stream("sparkle_events")
    replayed = []
    failed = []

    for message_id in request.message_ids:
        entry = await event_bus.redis.xrange(dlq_stream, message_id, message_id)
        if not entry:
            failed.append({"message_id": message_id, "error": "not_found"})
            continue

        _, data = entry[0]
        payload_raw = data.get("data")
        if not payload_raw:
            failed.append({"message_id": message_id, "error": "empty_payload"})
            continue

        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            failed.append({"message_id": message_id, "error": "invalid_payload"})
            continue

        original_event = payload.get("event")
        if not original_event:
            failed.append({"message_id": message_id, "error": "missing_event"})
            continue

        event_type = original_event.get("event_type", "unknown")
        try:
            await event_bus.publish(event_type, original_event)
            if request.delete_after:
                await event_bus.redis.xdel(dlq_stream, message_id)
            replayed.append(message_id)
            logger.info("Replayed DLQ event %s (%s) by admin %s", message_id, event_type, admin.id)
        except Exception as exc:
            failed.append({"message_id": message_id, "error": str(exc)})
            logger.error("Failed to replay DLQ event %s: %s", message_id, exc)

    return {"replayed": replayed, "failed": failed}


@router.delete("/dlq/{message_id}", response_model=dict[str, Any])
@audit_admin_action(category="dlq_delete", risk="high", action="delete_event_bus_dlq")
async def delete_event_bus_dlq(
    message_id: str,
    stream: str = "sparkle_events",
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    await event_bus.connect()
    if not event_bus.redis:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable")

    dlq_stream = event_bus._dlq_stream(stream)
    deleted = await event_bus.redis.xdel(dlq_stream, message_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Message {message_id} not found in DLQ")

    return {"deleted": message_id, "stream": dlq_stream}


@router.get("/lag", response_model=dict[str, Any])
async def get_consumer_lag_details(
    stream: str = "sparkle_events",
    group_name: str | None = None,
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    await event_bus.connect()
    return await event_bus.get_consumer_lag(stream, group_name)
