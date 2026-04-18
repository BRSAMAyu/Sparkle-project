"""Aurora observability helpers."""

from .metrics import (
    AURORA_DECISION_LATENCY_SECONDS,
    AURORA_DECISION_TOTAL,
    AURORA_FALLBACK_TOTAL,
    AURORA_MATERIALITY_TOTAL,
    AURORA_SHADOW_DIVERGENCE_TOTAL,
    AURORA_TRIGGER_DISPATCH_TOTAL,
    record_decision,
    record_fallback,
    record_materiality,
    record_shadow_divergence,
    record_trigger_dispatch,
)

__all__ = [
    "AURORA_DECISION_LATENCY_SECONDS",
    "AURORA_DECISION_TOTAL",
    "AURORA_FALLBACK_TOTAL",
    "AURORA_MATERIALITY_TOTAL",
    "AURORA_SHADOW_DIVERGENCE_TOTAL",
    "AURORA_TRIGGER_DISPATCH_TOTAL",
    "record_decision",
    "record_fallback",
    "record_materiality",
    "record_shadow_divergence",
    "record_trigger_dispatch",
]

