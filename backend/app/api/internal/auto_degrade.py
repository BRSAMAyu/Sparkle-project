"""
Core: infra
Phase: sense
Stage: FV-24

SLO Auto-Response + Server-side Weak Network.

Receives Alertmanager webhooks, maps alerts to kill-switch flips
and model-tier degradations, then publishes audit events.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from loguru import logger

from app.config import settings
from app.core.kill_switch import KillSwitchBinding, write_mode
from app.core.metrics import get_or_create_metric
from prometheus_client import Counter, Histogram

router = APIRouter()

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

SLO_AUTO_RESPONSE_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_slo_auto_response_actions_total",
    "Auto-response actions triggered by SLO alerts",
    ["alert_type", "action", "status"],
)

SLO_AUTO_RESPONSE_DURATION = get_or_create_metric(
    Histogram,
    "sparkle_slo_auto_response_duration_seconds",
    "Duration of auto-response action execution",
    ["alert_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ---------------------------------------------------------------------------
# Alert-to-action mapping
# ---------------------------------------------------------------------------

class AlertType(str, Enum):
    LLM_LATENCY_HIGH = "LLM_LATENCY_HIGH"
    REDIS_NEAR_FULL = "REDIS_NEAR_FULL"
    DB_CONNECTION_EXHAUST = "DB_CONNECTION_EXHAUST"
    EVENT_BUS_LAG = "EVENT_BUS_LAG"
    GW_HIGH_5XX = "GW_HIGH_5XX"

# Maps Prometheus alert names to internal AlertType
ALERT_NAME_MAP: dict[str, AlertType] = {
    "SparkleBackendP95LatencyHigh": AlertType.LLM_LATENCY_HIGH,
    "SparkleContainerMemoryHigh": AlertType.REDIS_NEAR_FULL,
    "SparkleDatabasePoolExhaustion": AlertType.DB_CONNECTION_EXHAUST,
    "SparkleEventStreamLagHigh": AlertType.EVENT_BUS_LAG,
    "SparkleEventBusConsumerLagHigh": AlertType.EVENT_BUS_LAG,
    "SparkleBackendHigh5xxRate": AlertType.GW_HIGH_5XX,
}

# Kill-switch bindings for each alert type
SLO_AUTO_DEGRADE_BINDINGS: dict[AlertType, KillSwitchBinding] = {
    AlertType.LLM_LATENCY_HIGH: KillSwitchBinding(
        stage="slo_auto",
        feature="llm_degrade",
        redis_key="aurora:slo_auto:llm_degrade",
        settings_attr="SLO_AUTO_LLM_DEGRADE_MODE",
        fallback_mode="off",
    ),
    AlertType.REDIS_NEAR_FULL: KillSwitchBinding(
        stage="slo_auto",
        feature="redis_fallback",
        redis_key="aurora:slo_auto:redis_fallback",
        settings_attr="SLO_AUTO_REDIS_FALLBACK_MODE",
        fallback_mode="off",
    ),
    AlertType.DB_CONNECTION_EXHAUST: KillSwitchBinding(
        stage="slo_auto",
        feature="db_throttle",
        redis_key="aurora:slo_auto:db_throttle",
        settings_attr="SLO_AUTO_DB_THROTTLE_MODE",
        fallback_mode="off",
    ),
    AlertType.EVENT_BUS_LAG: KillSwitchBinding(
        stage="slo_auto",
        feature="event_bus_throttle",
        redis_key="aurora:slo_auto:event_bus_throttle",
        settings_attr="SLO_AUTO_EVENT_BUS_THROTTLE_MODE",
        fallback_mode="off",
    ),
    AlertType.GW_HIGH_5XX: KillSwitchBinding(
        stage="slo_auto",
        feature="rate_limit_tighten",
        redis_key="aurora:slo_auto:rate_limit_tighten",
        settings_attr="SLO_AUTO_RATE_LIMIT_TIGHTEN_MODE",
        fallback_mode="off",
    ),
}

# ---------------------------------------------------------------------------
# Action descriptions (for audit trail)
# ---------------------------------------------------------------------------

ACTION_DESCRIPTIONS: dict[AlertType, dict[str, str]] = {
    AlertType.LLM_LATENCY_HIGH: {
        "firing": "Degrading LLM to cheaper/faster model tier",
        "resolved": "Restoring LLM to normal model tier",
    },
    AlertType.REDIS_NEAR_FULL: {
        "firing": "Enabling disk cache fallback for Redis",
        "resolved": "Disabling disk cache fallback",
    },
    AlertType.DB_CONNECTION_EXHAUST: {
        "firing": "Enabling DB connection throttle mode",
        "resolved": "Disabling DB connection throttle",
    },
    AlertType.EVENT_BUS_LAG: {
        "firing": "Enabling event bus throttle mode",
        "resolved": "Disabling event bus throttle",
    },
    AlertType.GW_HIGH_5XX: {
        "firing": "Tightening rate limits and enabling circuit breaker",
        "resolved": "Relaxing rate limits to normal",
    },
}

# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

async def _write_audit(
    alert_type: AlertType,
    alert_status: str,
    action_taken: str,
    alert_labels: dict[str, str],
    result: str,
    duration_s: float,
) -> None:
    """Publish audit event to EventBus for durable record."""
    try:
        from app.core.event_bus import event_bus

        await event_bus.publish(
            SLOAutoResponseAuditEvent(
                alert_type=alert_type.value,
                alert_status=alert_status,
                action_taken=action_taken,
                alert_labels=json.dumps(alert_labels, default=str),
                result=result,
                duration_s=round(duration_s, 4),
                timestamp=datetime.now(UTC).isoformat(),
            )
        )
    except Exception:
        logger.exception("Failed to publish SLO auto-response audit event")


class SLOAutoResponseAuditEvent:
    """Audit event for SLO auto-response actions."""

    def __init__(
        self,
        alert_type: str,
        alert_status: str,
        action_taken: str,
        alert_labels: str,
        result: str,
        duration_s: float,
        timestamp: str,
    ):
        self.alert_type = alert_type
        self.alert_status = alert_status
        self.action_taken = action_taken
        self.alert_labels = alert_labels
        self.result = result
        self.duration_s = duration_s
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "event_type": "slo_auto_response_audit",
            "alert_type": self.alert_type,
            "alert_status": self.alert_status,
            "action_taken": self.action_taken,
            "alert_labels": self.alert_labels,
            "result": self.result,
            "duration_s": self.duration_s,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Core auto-response logic
# ---------------------------------------------------------------------------

async def execute_auto_response(
    alert_type: AlertType,
    alert_status: str,
    alert_labels: dict[str, str],
) -> dict[str, Any]:
    """Execute the appropriate auto-response for an alert type."""
    t0 = time.monotonic()
    binding = SLO_AUTO_DEGRADE_BINDINGS.get(alert_type)
    if not binding:
        return {"status": "no_binding", "alert_type": alert_type.value}

    target_mode = "live" if alert_status == "firing" else "off"
    description = ACTION_DESCRIPTIONS.get(alert_type, {}).get(alert_status, f"Mode change to {target_mode}")

    try:
        from app.core.cache import cache_service

        redis_client = cache_service.redis
        if redis_client is None:
            return {
                "status": "error",
                "alert_type": alert_type.value,
                "error": "Redis is not available",
            }
        normalized = await write_mode(
            redis_client=redis_client,
            prefix="sparkle:",
            binding=binding,
            mode=target_mode,
        )

        duration = time.monotonic() - t0
        SLO_AUTO_RESPONSE_TOTAL.labels(
            alert_type=alert_type.value,
            action=target_mode,
            status="success",
        ).inc()
        SLO_AUTO_RESPONSE_DURATION.labels(alert_type=alert_type.value).observe(duration)

        await _write_audit(
            alert_type=alert_type,
            alert_status=alert_status,
            action_taken=description,
            alert_labels=alert_labels,
            result=f"mode={normalized}",
            duration_s=duration,
        )

        logger.info(
            "SLO auto-response: {} → mode={} ({}) in {:.3f}s",
            alert_type.value,
            normalized,
            description,
            duration,
        )

        return {
            "status": "success",
            "alert_type": alert_type.value,
            "action": target_mode,
            "mode": normalized,
            "duration_s": round(duration, 4),
        }

    except Exception as exc:
        duration = time.monotonic() - t0
        SLO_AUTO_RESPONSE_TOTAL.labels(
            alert_type=alert_type.value,
            action=target_mode,
            status="error",
        ).inc()

        await _write_audit(
            alert_type=alert_type,
            alert_status=alert_status,
            action_taken=description,
            alert_labels=alert_labels,
            result=f"error: {exc}",
            duration_s=duration,
        )

        logger.exception("SLO auto-response failed for {}: {}", alert_type.value, exc)
        return {
            "status": "error",
            "alert_type": alert_type.value,
            "error": str(exc),
            "duration_s": round(duration, 4),
        }


# ---------------------------------------------------------------------------
# Webhook handler
# ---------------------------------------------------------------------------

def _verify_internal_key(api_key: str | None) -> None:
    """Verify the internal API key."""
    expected = settings.INTERNAL_API_KEY
    if not expected:
        raise HTTPException(status_code=500, detail="INTERNAL_API_KEY not configured")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-Internal-API-Key header")
    if not _constant_time_compare(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def _constant_time_compare(a: str, b: str) -> bool:
    """Timing-attack resistant comparison."""
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())


# route-tier: internal
@router.post("/auto-degrade/webhook")
async def handle_alertmanager_webhook(
    request: Request,
    x_internal_api_key: str | None = Header(None),
) -> dict[str, Any]:
    """
    Receive Alertmanager webhook and trigger auto-degradation.

    Alertmanager sends POST with JSON payload containing alerts.
    Each alert's `alertname` label is mapped to an AlertType,
    and the corresponding kill switch is flipped.
    """
    _verify_internal_key(x_internal_api_key)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    alerts = payload.get("alerts", [])
    if not alerts:
        return {"status": "no_alerts", "processed": 0}

    overall_status = payload.get("status", "firing")
    results = []

    for alert in alerts:
        alert_labels = alert.get("labels", {})
        alert_name = alert_labels.get("alertname", "")
        alert_status = alert.get("status", overall_status)
        alert_type = ALERT_NAME_MAP.get(alert_name)

        if not alert_type:
            logger.debug("No auto-response mapping for alert: {}", alert_name)
            continue

        result = await execute_auto_response(alert_type, alert_status, alert_labels)
        results.append(result)

    return {
        "status": "processed",
        "total_alerts": len(alerts),
        "actions_taken": len(results),
        "results": results,
    }


# route-tier: internal
@router.get("/auto-degrade/status")
async def get_auto_degrade_status(
    x_internal_api_key: str | None = Header(None),
) -> dict[str, Any]:
    """Return current state of all auto-degrade kill switches."""
    _verify_internal_key(x_internal_api_key)

    from app.core.cache import cache_service
    from app.core.kill_switch import read_mode

    redis_client = cache_service.redis
    if redis_client is None:
        return {"status": "error", "error": "Redis is not available", "bindings": {}}
    statuses = {}

    for alert_type, binding in SLO_AUTO_DEGRADE_BINDINGS.items():
        mode = await read_mode(
            redis_client=redis_client,
            prefix="sparkle:",
            binding=binding,
        )
        statuses[alert_type.value] = {
            "mode": mode,
            "degraded": mode == "live",
            "redis_key": binding.redis_key,
        }

    return {"statuses": statuses}


# ---------------------------------------------------------------------------
# Python client-disconnect state saver
# ---------------------------------------------------------------------------

class ClientDisconnectGuard:
    """
    Context manager that auto-saves intermediate state when a client
    disconnects during streaming.

    Usage in streaming handlers::

        async with ClientDisconnectGuard(request, save_fn) as guard:
            for chunk in stream:
                guard.check()
                yield chunk

    When the client disconnects, ``save_fn(current_state)`` is called
    on the next ``check()`` call, and the guard raises
    ``ClientDisconnected`` to break the loop.
    """

    class ClientDisconnected(Exception):
        """Raised when client disconnect is detected."""

    def __init__(self, request: Request, save_fn, state_factory=None):
        """
        Args:
            request: The FastAPI Request object.
            save_fn: Async callable that receives state to persist.
            state_factory: Optional callable to create state snapshot.
                           Defaults to None (save_fn must handle it).
        """
        self._request = request
        self._save_fn = save_fn
        self._state_factory = state_factory
        self._disconnected = False
        self._saved = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._disconnected and not self._saved:
            await self._save_state()
        return False

    async def check(self) -> None:
        """Check if client is still connected. Raises on disconnect."""
        if await self._request.is_disconnected():
            self._disconnected = True
            await self._save_state()
            raise self.ClientDisconnected()

    async def _save_state(self) -> None:
        """Save intermediate state on disconnect."""
        if self._saved:
            return
        self._saved = True
        try:
            state = self._state_factory() if self._state_factory else None
            await self._save_fn(state)
            logger.info("Client disconnect: intermediate state saved")
        except Exception:
            logger.exception("Failed to save state on client disconnect")
