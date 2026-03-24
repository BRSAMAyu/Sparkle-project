from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_superuser, get_current_user
from app.core.cache import cache_service
from app.models.user import User

router = APIRouter(prefix="/client-telemetry", tags=["client-telemetry"])

_RECENT_EVENTS_KEY = "client_telemetry:recent"
_TTL_SECONDS = 45 * 24 * 60 * 60


class ClientTelemetryEventRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    category: str = Field("general", min_length=1, max_length=32)
    route: str | None = Field(default=None, max_length=160)
    status: str = Field("ok", min_length=1, max_length=16)
    severity: str = Field("info", min_length=1, max_length=16)
    duration_ms: int | None = Field(default=None, ge=0, le=600_000)
    metadata: dict[str, Any] | None = None
    occurred_at: datetime | None = None


class ClientTelemetryBatchRequest(BaseModel):
    events: list[ClientTelemetryEventRequest] = Field(default_factory=list, max_length=50)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _date_key(day: datetime) -> str:
    return day.astimezone(timezone.utc).date().isoformat()


def _aggregate_key(day: datetime, event_type: str) -> str:
    return f"client_telemetry:daily:{_date_key(day)}:{event_type}"


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


async def _update_hash(redis_client, key: str, payload: ClientTelemetryEventRequest, now: datetime) -> None:
    is_error = payload.status.lower() not in {"ok", "success"}
    is_crash = payload.event_type.lower() == "crash"
    duration_ms = payload.duration_ms or 0

    await redis_client.hincrby(key, "count", 1)
    await redis_client.hincrby(key, "success_count", 0 if is_error else 1)
    await redis_client.hincrby(key, "error_count", 1 if is_error else 0)
    await redis_client.hincrby(key, "crash_count", 1 if is_crash else 0)
    await redis_client.hincrby(key, "duration_total_ms", duration_ms)
    await redis_client.hincrby(key, "duration_samples", 1 if payload.duration_ms is not None else 0)
    await redis_client.hset(
        key,
        mapping={
            "category": payload.category,
            "route": payload.route or "",
            "severity": payload.severity,
            "latest_iso": now.isoformat(),
        },
    )
    await redis_client.expire(key, _TTL_SECONDS)


async def _store_event(
    *,
    redis_client,
    payload: ClientTelemetryEventRequest,
    user_id: str,
) -> tuple[str, datetime]:
    now = payload.occurred_at.astimezone(timezone.utc) if payload.occurred_at else _utcnow()
    event_type = payload.event_type.strip().lower().replace(" ", "_")
    platform = str((payload.metadata or {}).get("platform") or "unknown").lower()
    normalized = payload.model_copy(update={"event_type": event_type})

    for key in (
        _aggregate_key(now, "all"),
        _aggregate_key(now, event_type),
        _aggregate_key(now, f"{event_type}:{platform}"),
    ):
        await _update_hash(redis_client, key, normalized, now)

    recent_event = {
        "user_id": user_id,
        "event_type": event_type,
        "category": normalized.category,
        "route": normalized.route,
        "status": normalized.status,
        "severity": normalized.severity,
        "duration_ms": normalized.duration_ms,
        "platform": platform,
        "occurred_at": now.isoformat(),
        "metadata": normalized.metadata or {},
    }
    await redis_client.lpush(_RECENT_EVENTS_KEY, json.dumps(recent_event, ensure_ascii=True))
    await redis_client.ltrim(_RECENT_EVENTS_KEY, 0, 199)
    await redis_client.expire(_RECENT_EVENTS_KEY, _TTL_SECONDS)
    return event_type, now


@router.post("/events")
async def ingest_client_telemetry(
    payload: ClientTelemetryEventRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    redis_client = cache_service.redis
    if not redis_client:
        return {
            "accepted": True,
            "storage": "disabled",
            "reason": "redis_unavailable",
        }

    event_type, now = await _store_event(
        redis_client=redis_client,
        payload=payload,
        user_id=str(current_user.id),
    )

    return {
        "accepted": True,
        "storage": "redis",
        "event_type": event_type,
        "occurred_at": now.isoformat(),
    }


@router.post("/events/batch")
async def ingest_client_telemetry_batch(
    payload: ClientTelemetryBatchRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    redis_client = cache_service.redis
    if not redis_client:
        return {
            "accepted": True,
            "storage": "disabled",
            "accepted_count": len(payload.events),
            "reason": "redis_unavailable",
        }
    if not payload.events:
        return {
            "accepted": True,
            "storage": "redis",
            "accepted_count": 0,
            "events": [],
        }

    accepted_events = []
    for event in payload.events[:50]:
        event_type, occurred_at = await _store_event(
            redis_client=redis_client,
            payload=event,
            user_id=str(current_user.id),
        )
        accepted_events.append(
            {
                "event_type": event_type,
                "occurred_at": occurred_at.isoformat(),
            }
        )

    return {
        "accepted": True,
        "storage": "redis",
        "accepted_count": len(accepted_events),
        "events": accepted_events,
    }


@router.get("/summary")
async def get_client_telemetry_summary(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    del current_user
    redis_client = cache_service.redis
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    start_day = _utcnow().date()
    aggregates: dict[str, dict[str, Any]] = {}
    daily_totals: dict[str, dict[str, Any]] = {}

    for offset in range(days):
        day = start_day - timedelta(days=offset)
        pattern = f"client_telemetry:daily:{day.isoformat()}:*"
        async for key in redis_client.scan_iter(pattern):
            parts = key.split(":")
            if len(parts) < 4:
                continue
            event_type = ":".join(parts[3:])
            values = await redis_client.hgetall(key)
            item = aggregates.setdefault(
                event_type,
                {
                    "event_type": event_type,
                    "count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "crash_count": 0,
                    "duration_total_ms": 0,
                    "duration_samples": 0,
                    "latest_iso": None,
                },
            )
            item["count"] += _safe_int(values.get("count"))
            item["success_count"] += _safe_int(values.get("success_count"))
            item["error_count"] += _safe_int(values.get("error_count"))
            item["crash_count"] += _safe_int(values.get("crash_count"))
            item["duration_total_ms"] += _safe_int(values.get("duration_total_ms"))
            item["duration_samples"] += _safe_int(values.get("duration_samples"))
            latest_iso = values.get("latest_iso")
            if latest_iso and (item["latest_iso"] is None or latest_iso > item["latest_iso"]):
                item["latest_iso"] = latest_iso

            daily = daily_totals.setdefault(
                day.isoformat(),
                {
                    "date": day.isoformat(),
                    "count": 0,
                    "error_count": 0,
                    "crash_count": 0,
                    "duration_total_ms": 0,
                    "duration_samples": 0,
                },
            )
            if event_type == "all":
                daily["count"] += _safe_int(values.get("count"))
                daily["error_count"] += _safe_int(values.get("error_count"))
                daily["crash_count"] += _safe_int(values.get("crash_count"))
                daily["duration_total_ms"] += _safe_int(values.get("duration_total_ms"))
                daily["duration_samples"] += _safe_int(values.get("duration_samples"))

    summary_items = []
    overall = {
        "count": 0,
        "success_count": 0,
        "error_count": 0,
        "crash_count": 0,
        "avg_duration_ms": 0.0,
    }

    for event_type, item in sorted(aggregates.items()):
        duration_samples = max(item["duration_samples"], 0)
        avg_duration_ms = item["duration_total_ms"] / duration_samples if duration_samples > 0 else 0.0
        success_rate = item["success_count"] / item["count"] if item["count"] > 0 else 0.0
        summary_items.append(
            {
                "event_type": event_type,
                "count": item["count"],
                "success_rate_percent": round(success_rate * 100, 2),
                "error_count": item["error_count"],
                "crash_count": item["crash_count"],
                "avg_duration_ms": round(avg_duration_ms, 2),
                "latest_iso": item["latest_iso"],
            }
        )
        if event_type == "all":
            overall.update(
                {
                    "count": item["count"],
                    "success_count": item["success_count"],
                    "error_count": item["error_count"],
                    "crash_count": item["crash_count"],
                    "avg_duration_ms": round(avg_duration_ms, 2),
                }
            )

    recent_events = []
    for value in await redis_client.lrange(_RECENT_EVENTS_KEY, 0, 19):
        try:
            recent_events.append(json.loads(value))
        except json.JSONDecodeError:
            continue

    daily_items = []
    for _, item in sorted(daily_totals.items()):
        samples = max(_safe_int(item.get("duration_samples")), 0)
        avg_duration_ms = item["duration_total_ms"] / samples if samples > 0 else 0.0
        daily_items.append(
            {
                "date": item["date"],
                "count": item["count"],
                "error_count": item["error_count"],
                "crash_count": item["crash_count"],
                "avg_duration_ms": round(avg_duration_ms, 2),
            }
        )

    return {
        "days": days,
        "overall": overall,
        "daily_totals": daily_items,
        "by_event_type": summary_items,
        "recent_events": recent_events,
        "generated_at": _utcnow().isoformat(),
    }
