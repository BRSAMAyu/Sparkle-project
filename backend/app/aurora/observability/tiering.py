"""Stage 4 tier observability sidecars.

These metrics remain local to the async substrate and do not alter Gate 0
schemas or Stage 3 user-visible behavior.
"""

from __future__ import annotations

from contextlib import suppress
from time import perf_counter
from typing import Any

from loguru import logger
from prometheus_client import REGISTRY, Counter, Histogram


def _get_or_create_metric(metric_type, name, documentation, labelnames=(), **kwargs):
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_type(name, documentation, labelnames, **kwargs)


def _enabled(enabled: bool) -> bool:
    return bool(enabled)


def _stringify(value: Any) -> str:
    with suppress(Exception):
        return str(value)
    return "<unprintable>"


AURORA_TIER_EXECUTION_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_tier_execution_total",
    "Aurora Stage 4 tier outcomes by tier, trigger point, and status",
    ["tier", "trigger_point", "status"],
)

AURORA_TIER_FAILURE_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_tier_failure_total",
    "Aurora Stage 4 tier failures by tier, trigger point, and reason",
    ["tier", "trigger_point", "reason"],
)

AURORA_TIER_LATENCY_SECONDS = _get_or_create_metric(
    Histogram,
    "sparkle_aurora_tier_latency_seconds",
    "Aurora Stage 4 tier latency in seconds",
    ["tier", "trigger_point"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0, 30.0, 60.0],
)


def emit_tier_event(event: str, *, enabled: bool, **payload: Any) -> None:
    if not _enabled(enabled):
        return
    logger.bind(component="aurora_stage4", event=event, **{key: _stringify(value) for key, value in payload.items()}).info(
        "Aurora tier observability event"
    )


def record_tier_outcome(
    *,
    tier: str,
    trigger_point: str,
    status: str,
    enabled: bool,
    reason: str | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_TIER_EXECUTION_TOTAL.labels(tier=tier, trigger_point=trigger_point, status=status).inc()
    if reason:
        emit_tier_event(
            "tier_outcome",
            enabled=enabled,
            tier=tier,
            trigger_point=trigger_point,
            status=status,
            reason=reason,
        )


def record_tier_failure(
    *,
    tier: str,
    trigger_point: str,
    reason: str,
    enabled: bool,
    error: str | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_TIER_FAILURE_TOTAL.labels(tier=tier, trigger_point=trigger_point, reason=reason).inc()
    emit_tier_event(
        "tier_failure",
        enabled=enabled,
        tier=tier,
        trigger_point=trigger_point,
        reason=reason,
        error=error or "",
    )


class tier_latency:
    """Context manager for tier-level latency metrics."""

    def __init__(self, tier: str, trigger_point: str, *, enabled: bool) -> None:
        self.tier = tier
        self.trigger_point = trigger_point
        self.enabled = enabled
        self._start = 0.0

    def __enter__(self):
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not _enabled(self.enabled):
            return None
        AURORA_TIER_LATENCY_SECONDS.labels(tier=self.tier, trigger_point=self.trigger_point).observe(
            perf_counter() - self._start
        )
        return None

