from __future__ import annotations

import json
from collections import Counter
from datetime import timezone, datetime
from typing import Any

from prometheus_client import Counter as PrometheusCounter

from app.core.cache import cache_service
from app.core.metrics import get_or_create_metric


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


ACHIEVEMENT_PHOTON_COMPENSATION_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_achievement_photon_compensation_total",
    "Achievement photon compensation lifecycle events",
    ["channel", "status"],
)


class AchievementRewardObservability:
    AUDIT_KEY = "achievement:photon_compensation:audit"
    MAX_EVENTS = 200
    LOCAL_TTL_SECONDS = 86400 * 7
    ALERT_STATUSES = {"enqueue_failed", "retry_failed", "exhausted"}

    @classmethod
    async def record_event(
        cls,
        *,
        status: str,
        channel: str,
        user_id: str,
        achievement_id: str,
        achievement_name: str,
        quantity: int,
        attempt: int | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": f"{achievement_id}:{user_id}:{int(_utcnow().timestamp() * 1000)}",
            "created_at": _utcnow().isoformat(),
            "compensation_key": f"{achievement_id}:{user_id}",
            "status": status,
            "channel": channel,
            "user_id": str(user_id),
            "achievement_id": achievement_id,
            "achievement_name": achievement_name,
            "quantity": quantity,
            "attempt": attempt,
            "error_message": error_message,
        }

        ACHIEVEMENT_PHOTON_COMPENSATION_TOTAL.labels(
            channel=channel,
            status=status,
        ).inc()

        if cache_service.redis:
            await cache_service.redis.lpush(cls.AUDIT_KEY, json.dumps(event, ensure_ascii=True))
            await cache_service.redis.ltrim(cls.AUDIT_KEY, 0, cls.MAX_EVENTS - 1)
            return event

        events = await cache_service.get(cls.AUDIT_KEY) or []
        events.insert(0, event)
        await cache_service.set(
            cls.AUDIT_KEY,
            events[: cls.MAX_EVENTS],
            ttl=cls.LOCAL_TTL_SECONDS,
        )
        return event

    @classmethod
    async def list_events(
        cls,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, cls.MAX_EVENTS))
        if cache_service.redis:
            raw_events = await cache_service.redis.lrange(cls.AUDIT_KEY, 0, limit - 1)
            return [json.loads(item) for item in raw_events]

        events = await cache_service.get(cls.AUDIT_KEY) or []
        return list(events[:limit])

    @classmethod
    async def get_dashboard_payload(
        cls,
        *,
        limit: int = 20,
    ) -> dict[str, Any]:
        events = await cls.list_events(limit=max(limit, 100))
        latest_by_compensation: dict[str, dict[str, Any]] = {}
        status_counts = Counter(event["status"] for event in events)
        channel_counts = Counter(event["channel"] for event in events)

        last_success_at = None
        last_failure_at = None
        for event in events:
            latest_by_compensation.setdefault(event["compensation_key"], event)
            if last_success_at is None and event["status"] == "retry_succeeded":
                last_success_at = event["created_at"]
            if last_failure_at is None and event["status"] in cls.ALERT_STATUSES:
                last_failure_at = event["created_at"]

        open_alerts = [
            event
            for event in latest_by_compensation.values()
            if event["status"] in cls.ALERT_STATUSES
        ]

        return {
            "summary": {
                "tracked_events": len(events),
                "open_alert_count": len(open_alerts),
                "status_counts": dict(status_counts),
                "channel_counts": dict(channel_counts),
                "last_success_at": last_success_at,
                "last_failure_at": last_failure_at,
            },
            "open_alerts": open_alerts[:limit],
            "events": events[:limit],
        }
