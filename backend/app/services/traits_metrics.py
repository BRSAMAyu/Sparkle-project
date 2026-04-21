from __future__ import annotations

from prometheus_client import Counter, Histogram

from app.core.metrics import get_or_create_metric


TRAITS_COLDSTART_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_traits_coldstart_total",
    "Traits coldstart outcomes",
    ["outcome"],
)

TRAITS_NLP_OBSERVATION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_traits_nlp_observation_total",
    "Traits NLP observation outcomes",
    ["outcome"],
)

TRAITS_MERGED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_traits_merged_total",
    "Traits merge outcomes",
    ["source"],
)

TRAITS_ROUTER_ZERO_HIT_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_traits_router_zero_hit_total",
    "Assertions that router does not read traits",
    ["outcome"],
)

TRAITS_CONFIDENCE_DISTRIBUTION = get_or_create_metric(
    Histogram,
    "sparkle_traits_confidence_distribution",
    "Distribution of merged trait confidence values",
    ["dimension"],
    buckets=(0.0, 0.1, 0.2, 0.3),
)
