"""Prometheus metrics and structured logging for Aurora."""

from __future__ import annotations

from contextlib import suppress
from time import perf_counter
from typing import Any

from loguru import logger
from prometheus_client import REGISTRY, Counter, Histogram

from app.aurora.config import DEFAULT_AURORA_CONFIG


def _get_or_create_metric(metric_type, name, documentation, labelnames=(), **kwargs):
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_type(name, documentation, labelnames, **kwargs)


AURORA_DECISION_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_decision_total",
    "Aurora decision counts by trigger, mechanism, basis, mode, and outcome",
    ["trigger_point", "mechanism", "basis", "mode", "outcome"],
)

AURORA_MATERIALITY_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_materiality_total",
    "Aurora materiality verdicts by trigger and outcome",
    ["trigger_point", "outcome"],
)

AURORA_TRIGGER_DISPATCH_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_trigger_dispatch_total",
    "Aurora trigger dispatch results by initiation type and trigger point",
    ["initiation_type", "trigger_point", "dispatch_mode"],
)

AURORA_FALLBACK_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_fallback_total",
    "Aurora fallback decisions by reason and trigger point",
    ["reason", "trigger_point"],
)

AURORA_SHADOW_DIVERGENCE_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_shadow_divergence_total",
    "Aurora shadow comparison divergences",
    ["signal", "trigger_point"],
)

AURORA_SHADOW_HOOK_TOTAL = _get_or_create_metric(
    Counter,
    "sparkle_aurora_shadow_hook_total",
    "Aurora shadow-only hook captures by hook point, trigger point, and outcome",
    ["hook_point", "trigger_point", "outcome"],
)

AURORA_DECISION_LATENCY_SECONDS = _get_or_create_metric(
    Histogram,
    "sparkle_aurora_decision_latency_seconds",
    "Aurora decision latency in seconds",
    ["trigger_point", "mode"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 0.9, 1.5],
)


def _enabled(enabled: bool | None = None) -> bool:
    return DEFAULT_AURORA_CONFIG.any_enabled if enabled is None else enabled


def _stringify(value: Any) -> str:
    with suppress(Exception):
        return str(value)
    return "<unprintable>"


def emit_observability_event(event: str, enabled: bool | None = None, **payload: Any) -> None:
    if not _enabled(enabled):
        return
    logger.bind(component="aurora", event=event, **{key: _stringify(value) for key, value in payload.items()}).info(
        "Aurora observability event"
    )


def record_materiality(trigger_point: str, outcome: str, *, enabled: bool | None = None) -> None:
    if not _enabled(enabled):
        return
    AURORA_MATERIALITY_TOTAL.labels(trigger_point=trigger_point, outcome=outcome).inc()


def record_trigger_dispatch(
    initiation_type: str,
    trigger_point: str,
    dispatch_mode: str,
    *,
    enabled: bool | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_TRIGGER_DISPATCH_TOTAL.labels(
        initiation_type=initiation_type,
        trigger_point=trigger_point,
        dispatch_mode=dispatch_mode,
    ).inc()


def record_decision(
    trigger_point: str,
    mechanism: str,
    basis: str,
    mode: str,
    outcome: str,
    *,
    enabled: bool | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_DECISION_TOTAL.labels(
        trigger_point=trigger_point,
        mechanism=mechanism,
        basis=basis,
        mode=mode,
        outcome=outcome,
    ).inc()


def record_fallback(
    *,
    reason: str,
    trigger_point: str,
    decision_id: str | None = None,
    enabled: bool | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_FALLBACK_TOTAL.labels(reason=reason, trigger_point=trigger_point).inc()
    emit_observability_event(
        "fallback",
        enabled=enabled,
        reason=reason,
        trigger_point=trigger_point,
        decision_id=decision_id or "",
    )


def record_shadow_divergence(
    signal: str,
    trigger_point: str,
    *,
    enabled: bool | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_SHADOW_DIVERGENCE_TOTAL.labels(signal=signal, trigger_point=trigger_point).inc()
    emit_observability_event(
        "shadow_divergence",
        enabled=enabled,
        signal=signal,
        trigger_point=trigger_point,
    )


def record_shadow_hook(
    hook_point: str,
    trigger_point: str,
    outcome: str,
    *,
    enabled: bool | None = None,
) -> None:
    if not _enabled(enabled):
        return
    AURORA_SHADOW_HOOK_TOTAL.labels(
        hook_point=hook_point,
        trigger_point=trigger_point,
        outcome=outcome,
    ).inc()
    emit_observability_event(
        "shadow_hook",
        enabled=enabled,
        hook_point=hook_point,
        trigger_point=trigger_point,
        outcome=outcome,
    )


class decision_latency:
    """Small timing context for latency metrics."""

    def __init__(self, trigger_point: str, mode: str, *, enabled: bool | None = None) -> None:
        self.trigger_point = trigger_point
        self.mode = mode
        self.enabled = enabled
        self._start = 0.0

    def __enter__(self):
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not _enabled(self.enabled):
            return None
        AURORA_DECISION_LATENCY_SECONDS.labels(trigger_point=self.trigger_point, mode=self.mode).observe(
            perf_counter() - self._start
        )
        return None
