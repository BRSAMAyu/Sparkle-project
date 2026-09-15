"""
Core: infrastructure
Phase: adapt
Stage: STAB-019/020 — Blue-Green Deployment Health + Chaos Testing

STAB-019: Blue-green deployment with auto-rollback.
  - Health check comparison between blue/green instances
  - Auto-rollback if green fails health criteria
  - Metrics-based promotion gate

STAB-020: Chaos testing infrastructure.
  - Fault injection patterns (latency, error, resource exhaustion)
  - Circuit breaker validation
  - Graceful degradation verification
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# STAB-019: Blue-Green Deployment Health
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DeploymentHealth:
    """Health snapshot of a deployment slot (blue or green)."""
    slot: str                    # "blue" | "green"
    healthy: bool = True
    error_rate_5xx: float = 0.0  # 0-1
    p95_latency_ms: float = 0.0
    success_rate: float = 1.0    # 0-1
    active_connections: int = 0
    checked_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "healthy": self.healthy,
            "error_rate_5xx": round(self.error_rate_5xx, 4),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "success_rate": round(self.success_rate, 4),
            "active_connections": self.active_connections,
            "checked_at": self.checked_at,
        }


@dataclass
class PromotionCheckResult:
    """Result of a blue-green promotion health check."""
    can_promote: bool
    blue_health: DeploymentHealth | None = None
    green_health: DeploymentHealth | None = None
    violations: list[str] = field(default_factory=list)
    recommendation: str = ""
    checked_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_promote": self.can_promote,
            "blue_health": self.blue_health.to_dict() if self.blue_health else None,
            "green_health": self.green_health.to_dict() if self.green_health else None,
            "violations": self.violations,
            "recommendation": self.recommendation,
            "checked_at": self.checked_at,
        }


class BlueGreenHealthCheck:
    """STAB-019: Blue-green deployment health verification.

    Before promoting green → blue:
    1. Green must be healthy (no 5xx spike, acceptable latency)
    2. Green must not be worse than blue on key metrics
    3. Auto-rollback triggered if violations detected post-promotion
    """

    # Thresholds
    MAX_5XX_RATE = 0.02        # 2%
    MAX_P95_LATENCY_MS = 2000  # 2 seconds
    MIN_SUCCESS_RATE = 0.98    # 98%

    @classmethod
    def check_deployment_health(
        cls,
        *,
        slot: str,
        error_rate_5xx: float,
        p95_latency_ms: float,
        success_rate: float,
        active_connections: int = 0,
    ) -> DeploymentHealth:
        """Check if a deployment slot is healthy."""
        healthy = (
            error_rate_5xx <= cls.MAX_5XX_RATE
            and p95_latency_ms <= cls.MAX_P95_LATENCY_MS
            and success_rate >= cls.MIN_SUCCESS_RATE
        )
        return DeploymentHealth(
            slot=slot,
            healthy=healthy,
            error_rate_5xx=error_rate_5xx,
            p95_latency_ms=p95_latency_ms,
            success_rate=success_rate,
            active_connections=active_connections,
        )

    @classmethod
    def evaluate_promotion(
        cls,
        *,
        blue: DeploymentHealth,
        green: DeploymentHealth,
    ) -> PromotionCheckResult:
        """Evaluate whether green can be promoted to replace blue."""
        violations = []

        if not green.healthy:
            violations.append(f"green_unhealthy: 5xx={green.error_rate_5xx:.2%}, p95={green.p95_latency_ms:.0f}ms")

        # Green must not be significantly worse than blue
        if green.error_rate_5xx > blue.error_rate_5xx * 2:
            violations.append(
                f"green_5xx_regression: green={green.error_rate_5xx:.2%} > 2x blue={blue.error_rate_5xx:.2%}"
            )

        if green.p95_latency_ms > blue.p95_latency_ms * 1.5:
            violations.append(
                f"green_latency_regression: green={green.p95_latency_ms:.0f}ms > 1.5x blue={blue.p95_latency_ms:.0f}ms"
            )

        can_promote = len(violations) == 0
        recommendation = "safe_to_promote" if can_promote else "rollback_required"

        return PromotionCheckResult(
            can_promote=can_promote,
            blue_health=blue,
            green_health=green,
            violations=violations,
            recommendation=recommendation,
        )

    @classmethod
    def check_post_promotion(
        cls,
        current: DeploymentHealth,
        baseline: DeploymentHealth,
    ) -> PromotionCheckResult:
        """Post-promotion health check. Triggers rollback if degraded."""
        violations = []

        if current.error_rate_5xx > baseline.error_rate_5xx * 3:
            violations.append(f"post_promotion_5xx_spike: {current.error_rate_5xx:.2%}")

        if current.success_rate < 0.95:
            violations.append(f"post_promotion_success_drop: {current.success_rate:.2%}")

        if current.p95_latency_ms > baseline.p95_latency_ms * 2:
            violations.append(f"post_promotion_latency_spike: {current.p95_latency_ms:.0f}ms")

        return PromotionCheckResult(
            can_promote=len(violations) == 0,
            green_health=current,
            blue_health=baseline,
            violations=violations,
            recommendation="stable" if not violations else "rollback_required",
        )


# ═══════════════════════════════════════════════════════════════════════
# STAB-020: Chaos Testing Infrastructure
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ChaosFault:
    """A fault to inject for chaos testing."""
    fault_id: str = ""
    fault_type: str = ""       # "latency" | "error" | "connection_reset" | "resource_exhaustion" | "partition"
    target: str = ""           # Component being tested (e.g. "spine_pipeline", "redis", "llm")
    magnitude: float = 0.0     # e.g. latency_ms=500, error_rate=0.5
    duration_seconds: float = 10.0
    enabled: bool = True

    def __post_init__(self):
        if not self.fault_id:
            self.fault_id = _uid("cf")

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_id": self.fault_id,
            "fault_type": self.fault_type,
            "target": self.target,
            "magnitude": self.magnitude,
            "duration_seconds": self.duration_seconds,
            "enabled": self.enabled,
        }


@dataclass
class ChaosTestResult:
    """Result of a chaos test run."""
    test_id: str = ""
    fault: ChaosFault | None = None
    system_survived: bool = True
    degradation_detected: bool = False
    recovery_time_seconds: float = 0.0
    circuit_breaker_activated: bool = False
    graceful_degradation: bool = True
    violations: list[str] = field(default_factory=list)
    tested_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.test_id:
            self.test_id = _uid("ctest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "fault": self.fault.to_dict() if self.fault else None,
            "system_survived": self.system_survived,
            "degradation_detected": self.degradation_detected,
            "recovery_time_seconds": round(self.recovery_time_seconds, 2),
            "circuit_breaker_activated": self.circuit_breaker_activated,
            "graceful_degradation": self.graceful_degradation,
            "violations": self.violations,
            "tested_at": self.tested_at,
        }


class ChaosTestRunner:
    """STAB-020: Chaos testing runner.

    Validates system resilience by simulating fault conditions:
    1. Latency injection (slow Redis, slow LLM)
    2. Error injection (5xx responses, connection failures)
    3. Resource exhaustion (memory pressure, connection pool)
    4. Network partition (service isolation)

    Each test verifies:
    - Circuit breakers activate correctly
    - Graceful degradation (not hard crash)
    - Recovery after fault is removed
    """

    STANDARD_FAULTS: list[ChaosFault] = [
        ChaosFault(fault_type="latency", target="redis", magnitude=500, duration_seconds=10),
        ChaosFault(fault_type="latency", target="llm", magnitude=2000, duration_seconds=10),
        ChaosFault(fault_type="error", target="llm", magnitude=0.5, duration_seconds=10),
        ChaosFault(fault_type="connection_reset", target="redis", magnitude=1.0, duration_seconds=5),
        ChaosFault(fault_type="resource_exhaustion", target="connection_pool", magnitude=0.9, duration_seconds=10),
    ]

    @classmethod
    def evaluate_resilience(
        cls,
        *,
        fault: ChaosFault,
        system_survived: bool,
        degradation_detected: bool,
        recovery_time_seconds: float,
        circuit_breaker_activated: bool,
        graceful_degradation: bool,
    ) -> ChaosTestResult:
        """Evaluate resilience against an injected fault."""
        violations = []

        if not system_survived:
            violations.append("system_crashed")
        if not graceful_degradation and degradation_detected:
            violations.append("hard_failure_not_graceful")
        if degradation_detected and recovery_time_seconds > 30:
            violations.append(f"slow_recovery: {recovery_time_seconds:.0f}s")
        if not circuit_breaker_activated and fault.fault_type in ("error", "connection_reset"):
            violations.append("circuit_breaker_not_activated")

        result = ChaosTestResult(
            fault=fault,
            system_survived=system_survived,
            degradation_detected=degradation_detected,
            recovery_time_seconds=recovery_time_seconds,
            circuit_breaker_activated=circuit_breaker_activated,
            graceful_degradation=graceful_degradation,
            violations=violations,
        )

        if violations:
            logger.warning(
                "Chaos test {} failed: {} — violations: {}",
                result.test_id, fault.fault_type, violations,
            )

        return result

    @classmethod
    def run_standard_suite(
        cls,
        resilience_fn,
    ) -> list[ChaosTestResult]:
        """Run the standard fault suite against a resilience evaluation function.

        resilience_fn: (ChaosFault) -> dict with keys:
            system_survived, degradation_detected, recovery_time_seconds,
            circuit_breaker_activated, graceful_degradation
        """
        results = []
        for fault in cls.STANDARD_FAULTS:
            response = resilience_fn(fault)
            result = cls.evaluate_resilience(fault=fault, **response)
            results.append(result)
        return results
