from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser
from app.core.event_bus import event_bus
from app.core.metrics import (
    EVENT_BUS_CONSUMER_LAG_MESSAGES,
    EVENT_BUS_CONSUMER_LAG_SECONDS,
    EVENT_BUS_DLQ_MESSAGES,
)

router = APIRouter(prefix="/event-bus", tags=["Event Bus Health"])


@router.get("/health", response_model=dict[str, Any])
async def get_event_bus_health(
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """
    Get event bus health status including DLQ stats and consumer lag.
    Requires superuser privileges.
    """
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
        )


@router.get("/dlq", response_model=dict[str, Any])
async def get_dlq_details(
    stream: str = "sparkle_events",
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """
    Get detailed DLQ statistics for a specific stream.
    Requires superuser privileges.
    """
    await event_bus.connect()
    return await event_bus.get_dlq_stats(stream)


@router.get("/lag", response_model=dict[str, Any])
async def get_consumer_lag_details(
    stream: str = "sparkle_events",
    group_name: str | None = None,
    _admin=Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """
    Get consumer lag details for a stream.
    Optionally filter by consumer group name.
    Requires superuser privileges.
    """
    await event_bus.connect()
    return await event_bus.get_consumer_lag(stream, group_name)
