"""Hourly parameter effectiveness measurement for meta-learning.

Queries RoutingDecisionLog, groups by (parameter_version, dominant_signal, routing_mode),
computes success rate per group, compares against baseline, stores in Redis.

Core: bridge
Phase: adapt
Stage: meta_learning
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import get_or_create_metric, Gauge
from app.orchestration.routing_parameter_registry import ALL_DEFAULT_PARAMETERS, _config_hash

ROUTING_PARAMETER_EFFECTIVENESS = get_or_create_metric(
    Gauge,
    "sparkle_routing_parameter_effectiveness",
    "Parameter effectiveness by version, signal, and mode",
    ["parameter_version", "dominant_signal", "routing_mode"],
)

ROUTING_PARAMETER_EFFECTIVENESS_SAMPLES = get_or_create_metric(
    Gauge,
    "sparkle_routing_parameter_effectiveness_samples",
    "Sample count for parameter effectiveness measurement",
    ["parameter_version", "dominant_signal"],
)

EFFECTIVENESS_REDIS_KEY = "aurora:param_effectiveness:latest"
EFFECTIVENESS_REDIS_TTL = 86400  # 24 hours


class ParameterEffectivenessRow:
    __slots__ = ("parameter_version", "dominant_signal", "routing_mode", "total", "successes")

    def __init__(
        self,
        parameter_version: str,
        dominant_signal: str,
        routing_mode: str,
        total: int,
        successes: int,
    ):
        self.parameter_version = parameter_version
        self.dominant_signal = dominant_signal
        self.routing_mode = routing_mode
        self.total = total
        self.successes = successes

    @property
    def success_rate(self) -> float:
        return self.successes / self.total if self.total > 0 else 0.0


class RoutingParameterEffectivenessService:
    """Computes which parameter configurations produce better outcomes for which signal types."""

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client

    async def compute_effectiveness(self, hours: int = 24) -> list[ParameterEffectivenessRow]:
        """Compute effectiveness for recent routing decisions with outcomes."""
        from app.models.aurora_stage20 import RoutingDecisionLog

        cutoff = func.now() - timedelta(hours=hours)

        rows = (await self.db.execute(
            select(RoutingDecisionLog)
            .where(
                RoutingDecisionLog.decided_at >= cutoff,
                RoutingDecisionLog.outcome.isnot(None),
                RoutingDecisionLog.decision_type.in_(["execution_first", "cognitive_first", "balanced"]),
            )
            .order_by(RoutingDecisionLog.decided_at.desc())
            .limit(5000)
        )).scalars().all()

        grouped: dict[str, ParameterEffectivenessRow] = {}
        for row in rows:
            payload = row.decision_payload or {}
            routing_debug = payload.get("routing_debug") or {}
            parameter_version = str(routing_debug.get("parameter_version") or "defaults").strip()
            dominant_signal = str(routing_debug.get("dominant_signal") or "unknown").strip()
            routing_mode = str(row.decision_type or "unknown").strip()
            outcome = str(row.outcome or "").strip()

            key = f"{parameter_version}|{dominant_signal}|{routing_mode}"
            if key not in grouped:
                grouped[key] = ParameterEffectivenessRow(
                    parameter_version=parameter_version,
                    dominant_signal=dominant_signal,
                    routing_mode=routing_mode,
                    total=0,
                    successes=0,
                )
            grouped[key].total += 1
            if outcome in ("task_completion", "plan_success"):
                grouped[key].successes += 1

        results = list(grouped.values())

        # Update Prometheus gauges
        for row in results:
            ROUTING_PARAMETER_EFFECTIVENESS.labels(
                parameter_version=row.parameter_version,
                dominant_signal=row.dominant_signal,
                routing_mode=row.routing_mode,
            ).set(row.success_rate)
            ROUTING_PARAMETER_EFFECTIVENESS_SAMPLES.labels(
                parameter_version=row.parameter_version,
                dominant_signal=row.dominant_signal,
            ).set(row.total)

        # Cache in Redis
        if self.redis is not None:
            try:
                cache_data = [
                    {
                        "parameter_version": r.parameter_version,
                        "dominant_signal": r.dominant_signal,
                        "routing_mode": r.routing_mode,
                        "total": r.total,
                        "successes": r.successes,
                        "success_rate": round(r.success_rate, 4),
                    }
                    for r in results
                ]
                await self.redis.set(
                    EFFECTIVENESS_REDIS_KEY,
                    json.dumps(cache_data),
                    ex=EFFECTIVENESS_REDIS_TTL,
                )
            except Exception as exc:
                logger.warning("Failed to cache parameter effectiveness: {}", exc)

        logger.info(
            "Parameter effectiveness computed: {} groups from {} decisions",
            len(results),
            len(rows),
        )
        return results
