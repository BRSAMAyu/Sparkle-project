"""
Sparkle Service Level Objective (SLO) definitions.

Single source of truth for all performance and reliability SLO targets.
Prometheus alert rules in monitoring/ reference these same targets.

Phase 6 / T6.1 — STAB-018: Formal SLO definitions with error budget tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar


class SLOSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SLOTier(StrEnum):
    P1 = "P1"  # Immediate page
    P2 = "P2"  # Alert within 30 min
    P3 = "P3"  # Review within business day


@dataclass(frozen=True)
class SLOTarget:
    """Single SLO target definition."""

    name: str
    description: str
    metric: str
    target_seconds: float
    percentile: float = 0.95
    window_minutes: int = 10
    severity: SLOSeverity = SLOSeverity.WARNING
    tier: SLOTier = SLOTier.P2
    service: str = ""
    alert_name: str = ""
    recording_rule: str = ""

    # Error budget: allowed non-compliance fraction (e.g. 0.001 = 0.1%)
    error_budget_fraction: float = 0.001


@dataclass(frozen=True)
class SLODomain:
    """Group of related SLOs for a service domain."""

    domain: str
    targets: list[SLOTarget]


# ── Performance SLOs (T6.1) ────────────────────────────────────────────────

PERFORMANCE_SLOS = SLODomain(
    domain="performance",
    targets=[
        SLOTarget(
            name="chat_first_token_p95_lt_2s",
            description="AI chat first token/event P95 latency",
            metric="sparkle_ai_response_first_token_duration_seconds",
            target_seconds=2.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="ai",
            alert_name="SparkleSLOChatFirstTokenSlow",
            recording_rule="sparkle:slo:chat_first_token_compliance",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="task_gen_p95_lt_5s",
            description="Task generation end-to-end P95 latency",
            metric="sparkle_task_generation_e2e_seconds",
            target_seconds=5.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="planning",
            alert_name="SparkleSLOTaskGenerationSlow",
            recording_rule="sparkle:slo:task_generation_compliance",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="planning_p95_lt_5s",
            description="LangGraph planning P95 latency",
            metric="sparkle_langgraph_planning_latency_seconds",
            target_seconds=5.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="planning",
            alert_name="SparkleSLOPlanningSlow",
            recording_rule="sparkle:slo:planning_compliance",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="retrieval_p95_lt_1s",
            description="RAG/memory retrieval P95 latency",
            metric="sparkle_rag_retrieval_seconds",
            target_seconds=1.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="retrieval",
            alert_name="SparkleSLORetrievalSlow",
            recording_rule="sparkle:slo:rag_retrieval_compliance",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="galaxy_p95_lt_3s",
            description="Galaxy knowledge graph E2E P95 latency",
            metric="sparkle_galaxy_e2e_latency_seconds",
            target_seconds=3.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="galaxy",
            alert_name="SparkleSLOGalaxySlow",
            recording_rule="sparkle:slo:galaxy_compliance",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="aurora_l3_p95_lt_15s",
            description="Aurora L3 full core inference P95 latency",
            metric="sparkle_aurora_tier_latency_seconds",
            target_seconds=15.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="aurora",
            alert_name="SparkleSLOAuroraL3Slow",
            recording_rule="sparkle:slo:aurora_l3_compliance",
            error_budget_fraction=0.002,
        ),
    ],
)


# ── Infrastructure SLOs ─────────────────────────────────────────────────────

INFRASTRUCTURE_SLOS = SLODomain(
    domain="infrastructure",
    targets=[
        SLOTarget(
            name="backend_p95_lt_1_5s",
            description="Backend HTTP P95 latency",
            metric="http_request_duration_seconds",
            target_seconds=1.5,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="backend",
            alert_name="SparkleBackendP95LatencyHigh",
            recording_rule="",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="product_loop_p95_lt_2s",
            description="Product loop user-facing P95 latency",
            metric="sparkle_product_loop_latency_seconds",
            target_seconds=2.0,
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P3,
            service="backend",
            alert_name="SparkleProductLoopLatencyHigh",
            recording_rule="",
            error_budget_fraction=0.005,
        ),
    ],
)


# ── Reliability SLOs ────────────────────────────────────────────────────────

RELIABILITY_SLOS = SLODomain(
    domain="reliability",
    targets=[
        SLOTarget(
            name="gateway_uptime_gt_99_9",
            description="Gateway uptime (99.9% = 43.2 min/month downtime budget)",
            metric="up",
            target_seconds=0.0,  # up == 0 triggers alert
            percentile=1.0,
            window_minutes=2,
            severity=SLOSeverity.CRITICAL,
            tier=SLOTier.P1,
            service="gateway",
            alert_name="SparkleGatewayDown",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="backend_uptime_gt_99_9",
            description="Backend uptime (99.9% = 43.2 min/month downtime budget)",
            metric="up",
            target_seconds=0.0,
            percentile=1.0,
            window_minutes=2,
            severity=SLOSeverity.CRITICAL,
            tier=SLOTier.P1,
            service="backend",
            alert_name="SparkleBackendDown",
            error_budget_fraction=0.001,
        ),
        SLOTarget(
            name="backend_5xx_lt_2pct",
            description="Backend 5xx error rate < 2%",
            metric="http_requests_total",
            target_seconds=0.02,  # 2% threshold
            percentile=0.95,
            window_minutes=10,
            tier=SLOTier.P2,
            service="backend",
            alert_name="SparkleBackendHigh5xxRate",
            error_budget_fraction=0.02,
        ),
    ],
)


# ── Resource SLOs ───────────────────────────────────────────────────────────

RESOURCE_SLOS = SLODomain(
    domain="resource",
    targets=[
        SLOTarget(
            name="db_connections_lt_25",
            description="Database active connections < 25",
            metric="pg_stat_activity_count",
            target_seconds=25.0,
            percentile=1.0,
            window_minutes=5,
            tier=SLOTier.P2,
            service="database",
            alert_name="SparkleDatabasePoolExhaustion",
        ),
        SLOTarget(
            name="container_memory_lt_90pct",
            description="Container memory usage < 90% of limit",
            metric="container_memory_usage_bytes",
            target_seconds=0.90,
            percentile=1.0,
            window_minutes=5,
            tier=SLOTier.P2,
            service="infrastructure",
            alert_name="SparkleContainerMemoryHigh",
        ),
    ],
)


# ── Burn rate definitions ───────────────────────────────────────────────────

@dataclass(frozen=True)
class BurnRateWindow:
    """Multi-window burn rate alert configuration.

    Based on Google SRE workbook: https://sre.google/workbook/alerting-on-slos/

    Short window catches fast burns (critical); long window catches slow burns.
    """

    name: str
    window_hours: float
    burn_rate_threshold: float  # multiples of error budget consumption rate
    severity: SLOSeverity


# Standard multi-window burn rate config
BURN_RATE_WINDOWS: ClassVar[list[BurnRateWindow]] = [
    BurnRateWindow(
        name="fast_burn_1h",
        window_hours=1.0,
        burn_rate_threshold=14.4,  # 2% of 30d budget burned in 1h
        severity=SLOSeverity.CRITICAL,
    ),
    BurnRateWindow(
        name="slow_burn_6h",
        window_hours=6.0,
        burn_rate_threshold=6.0,  # 5% of 30d budget burned in 6h
        severity=SLOSeverity.WARNING,
    ),
]

# Error budget window (30 days)
ERROR_BUDGET_WINDOW_SECONDS: int = 30 * 24 * 3600  # 2,592,000


def error_budget_seconds(target: SLOTarget) -> float:
    """Calculate error budget in seconds for a 30-day window."""
    return float(target.error_budget_fraction * ERROR_BUDGET_WINDOW_SECONDS)


def burn_rate(
    target: SLOTarget,
    non_compliance_ratio: float,
) -> float:
    """Calculate SRE burn rate: error_ratio / error_budget.

    A burn rate of 1.0 means consuming budget at the exact allocated rate.
    A burn rate of 14.4 means the entire 30-day error budget would be exhausted
    in ~2 days. In a 1-hour window at 14.4x, ~2% of the monthly budget is consumed.

    This matches the Google SRE workbook definition (Chapter 5).
    """
    if target.error_budget_fraction <= 0:
        return 0.0
    return non_compliance_ratio / target.error_budget_fraction


# ── Aggregate registry ──────────────────────────────────────────────────────

ALL_DOMAINS: ClassVar[list[SLODomain]] = [
    PERFORMANCE_SLOS,
    INFRASTRUCTURE_SLOS,
    RELIABILITY_SLOS,
    RESOURCE_SLOS,
]


def all_targets() -> list[SLOTarget]:
    """Flat list of all SLO targets across all domains."""
    result: list[SLOTarget] = []
    for domain in ALL_DOMAINS:
        result.extend(domain.targets)
    return result


def targets_by_tier(tier: SLOTier) -> list[SLOTarget]:
    return [t for t in all_targets() if t.tier == tier]


def targets_by_service(service: str) -> list[SLOTarget]:
    return [t for t in all_targets() if t.service == service]


SLO_TABLE: ClassVar[dict[str, SLOTarget]] = {
    t.name: t for t in all_targets()
}
