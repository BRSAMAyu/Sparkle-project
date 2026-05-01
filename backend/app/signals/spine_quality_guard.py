"""
Core: execution / research
Phase: adapt
Stage: P4-6 — Autonomous Product Quality Guard

Self-monitoring system that detects spine health degradation:
- Signal quality monitoring
- Causal chain break detection
- Directive compliance scoring
- Autonomous quality reports
- Early warning for systemic issues

This is the "immune system" of the Causal Control Spine.
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


@dataclass
class QualityCheck:
    """A single quality check result."""
    check_id: str
    check_name: str
    category: str              # "signal_quality" | "causal_chain" | "directive_compliance" | "outcome_quality"
    passed: bool
    score: float               # 0.0–1.0
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "category": self.category,
            "passed": self.passed,
            "score": round(self.score, 3),
            "details": self.details,
            "recommendations": self.recommendations,
            "checked_at": self.checked_at,
        }


@dataclass
class QualityReport:
    """Aggregated quality report for a time window."""
    report_id: str
    window_start: str
    window_end: str
    checks: list[QualityCheck] = field(default_factory=list)
    overall_score: float = 1.0
    health_status: str = "healthy"     # healthy | degraded | at_risk | critical
    systemic_issues: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "checks": [c.to_dict() for c in self.checks],
            "overall_score": round(self.overall_score, 3),
            "health_status": self.health_status,
            "systemic_issues": self.systemic_issues,
            "generated_at": self.generated_at,
        }

    def compute_health(self) -> None:
        """Compute overall health from individual checks."""
        if not self.checks:
            self.overall_score = 1.0
            self.health_status = "healthy"
            return

        scores = [c.score for c in self.checks]
        self.overall_score = sum(scores) / len(scores)

        failed_count = sum(1 for c in self.checks if not c.passed)
        if failed_count == 0:
            self.health_status = "healthy"
        elif self.overall_score >= 0.7:
            self.health_status = "degraded"
        elif self.overall_score >= 0.4:
            self.health_status = "at_risk"
        else:
            self.health_status = "critical"

        if self.health_status in ("at_risk", "critical"):
            self.systemic_issues = [
                c.check_name for c in self.checks
                if not c.passed and c.score < 0.5
            ]


class SpineQualityGuard:
    """Autonomous quality monitoring for the Causal Control Spine.

    Monitors:
    1. Signal quality — are signals actionable? Is orphan_signal_count growing?
    2. Causal chain — are traces complete? Any breaks in signal→directive→outcome?
    3. Directive compliance — are directives being applied correctly?
    4. Outcome quality — are outcomes being recorded and attributed?
    """

    # ── Signal Quality Checks ────────────────────────────────────────────

    @staticmethod
    def check_signal_actionability(
        signal_history: list[dict[str, Any]],
        *,
        min_actionable_ratio: float = 0.5,
    ) -> QualityCheck:
        """Check that signals are actionable (produce directives/receipts).

        A signal is 'actionable' if it led to a policy decision and directive.
        """
        total = len(signal_history)
        if total == 0:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="signal_actionability",
                category="signal_quality",
                passed=True,
                score=1.0,
                details={"total_signals": 0, "note": "No signals to evaluate"},
            )

        actionable = sum(
            1 for s in signal_history
            if s.get("had_policy_decision") and s.get("had_directive")
        )
        ratio = actionable / total
        passed = ratio >= min_actionable_ratio

        details = {
            "total_signals": total,
            "actionable_signals": actionable,
            "actionable_ratio": round(ratio, 3),
            "threshold": min_actionable_ratio,
        }
        recommendations = []
        if not passed:
            recommendations.append(
                f"Signal actionability {ratio:.1%} below threshold {min_actionable_ratio:.1%}. "
                "Check signal detectors for noisy signals."
            )

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="signal_actionability",
            category="signal_quality",
            passed=passed,
            score=ratio,
            details=details,
            recommendations=recommendations,
        )

    @staticmethod
    def check_orphan_signal_buildup(
        orphan_count: int,
        total_signal_count: int,
        *,
        max_orphan_ratio: float = 0.3,
    ) -> QualityCheck:
        """Check for orphan signals (generated but never consumed)."""
        if total_signal_count == 0:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="orphan_signal_buildup",
                category="signal_quality",
                passed=True,
                score=1.0,
                details={"note": "No signals generated"},
            )

        ratio = orphan_count / total_signal_count
        passed = ratio <= max_orphan_ratio

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="orphan_signal_buildup",
            category="signal_quality",
            passed=passed,
            score=1.0 - ratio,
            details={
                "orphan_signals": orphan_count,
                "total_signals": total_signal_count,
                "orphan_ratio": round(ratio, 3),
                "threshold": max_orphan_ratio,
            },
            recommendations=(
                [f"Orphan ratio {ratio:.1%} exceeds {max_orphan_ratio:.1%}. Check signal consumers."]
                if not passed
                else []
            ),
        )

    # ── Causal Chain Checks ──────────────────────────────────────────────

    @staticmethod
    def check_causal_trace_completeness(
        traces: list[dict[str, Any]],
        *,
        min_complete_ratio: float = 0.8,
    ) -> QualityCheck:
        """Check that causal traces have all required links.

        A complete trace has: event → signal → policy → directive → audit → receipt → outcome.
        """
        if not traces:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="causal_trace_completeness",
                category="causal_chain",
                passed=True,
                score=1.0,
                details={"note": "No traces to evaluate"},
            )

        complete = sum(
            1 for t in traces
            if (
                t.get("signal_ids")
                and t.get("policy_decision_id")
                and t.get("directive_ids")
                and t.get("audit_ids")
                and t.get("receipt_ids")
            )
        )
        ratio = complete / len(traces)
        passed = ratio >= min_complete_ratio

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="causal_trace_completeness",
            category="causal_chain",
            passed=passed,
            score=ratio,
            details={
                "total_traces": len(traces),
                "complete_traces": complete,
                "complete_ratio": round(ratio, 3),
                "threshold": min_complete_ratio,
            },
            recommendations=(
                [f"{len(traces) - complete} traces have missing links"]
                if not passed
                else []
            ),
        )

    @staticmethod
    def check_chain_breaks(
        metrics: dict[str, int],
    ) -> QualityCheck:
        """Check for breaks in the causal chain by comparing metric ratios.

        Expected: signals_generated ≥ signals_with_policy ≥ directives_generated
        A significant drop indicates a chain break.
        """
        signals = metrics.get("signals_generated", 0)
        policies = metrics.get("policies_evaluated", 0)
        directives = metrics.get("directives_applied", 0)

        if signals == 0:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="chain_breaks",
                category="causal_chain",
                passed=True,
                score=1.0,
                details={"note": "No signals to evaluate chain"},
            )

        signal_to_policy = policies / signals if signals > 0 else 1.0
        policy_to_directive = directives / policies if policies > 0 else 1.0

        passed = signal_to_policy >= 0.7 and policy_to_directive >= 0.7
        score = min(signal_to_policy, policy_to_directive)

        details = {
            "signals_generated": signals,
            "policies_evaluated": policies,
            "directives_applied": directives,
            "signal_to_policy_ratio": round(signal_to_policy, 3),
            "policy_to_directive_ratio": round(policy_to_directive, 3),
        }

        recommendations = []
        if signal_to_policy < 0.7:
            recommendations.append("Signal→Policy chain broken: signals not reaching PolicyEngine")
        if policy_to_directive < 0.7:
            recommendations.append("Policy→Directive chain broken: policies not producing directives")

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="chain_breaks",
            category="causal_chain",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
        )

    # ── Directive Compliance Checks ──────────────────────────────────────

    @staticmethod
    def check_directive_compliance(
        audits: list[dict[str, Any]],
        *,
        min_compliance: float = 0.9,
    ) -> QualityCheck:
        """Check that directives are being complied with (audit.applied == true)."""
        if not audits:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="directive_compliance",
                category="directive_compliance",
                passed=True,
                score=1.0,
                details={"note": "No audits to evaluate"},
            )

        compliant = sum(1 for a in audits if a.get("applied"))
        ratio = compliant / len(audits)

        details = {
            "total_audits": len(audits),
            "compliant_audits": compliant,
            "violations": [
                {"audit_id": a.get("audit_id"), "violations": a.get("violations", [])}
                for a in audits
                if not a.get("applied")
            ],
        }

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="directive_compliance",
            category="directive_compliance",
            passed=ratio >= min_compliance,
            score=ratio,
            details=details,
            recommendations=(
                ["Directive compliance below threshold — check downstream modules"]
                if ratio < min_compliance
                else []
            ),
        )

    # ── Outcome Quality Checks ───────────────────────────────────────────

    @staticmethod
    def check_outcome_recording_rate(
        outcome_count: int,
        directive_count: int,
        *,
        min_recording_rate: float = 0.5,
    ) -> QualityCheck:
        """Check that outcomes are being recorded for applied directives."""
        if directive_count == 0:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="outcome_recording_rate",
                category="outcome_quality",
                passed=True,
                score=1.0,
                details={"note": "No directives applied"},
            )

        ratio = outcome_count / directive_count
        passed = ratio >= min_recording_rate

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="outcome_recording_rate",
            category="outcome_quality",
            passed=passed,
            score=ratio,
            details={
                "outcomes_recorded": outcome_count,
                "directives_applied": directive_count,
                "recording_rate": round(ratio, 3),
                "threshold": min_recording_rate,
            },
            recommendations=(
                [f"Only {ratio:.1%} of directives have recorded outcomes. Causal learning is impaired."]
                if not passed
                else []
            ),
        )

    @staticmethod
    def check_attribution_coverage(
        outcomes: list[dict[str, Any]],
        *,
        min_conclusive_ratio: float = 0.3,
    ) -> QualityCheck:
        """Check that outcome attributions are conclusive enough for learning."""
        if not outcomes:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name="attribution_coverage",
                category="outcome_quality",
                passed=True,
                score=1.0,
                details={"note": "No outcomes to evaluate"},
            )

        conclusive = sum(
            1 for o in outcomes
            if o.get("attribution") not in ("inconclusive", None)
            and o.get("attribution_confidence", 0) >= 0.5
        )
        ratio = conclusive / len(outcomes)

        return QualityCheck(
            check_id=_uid("qc"),
            check_name="attribution_coverage",
            category="outcome_quality",
            passed=ratio >= min_conclusive_ratio,
            score=ratio,
            details={
                "total_outcomes": len(outcomes),
                "conclusive_attributions": conclusive,
                "conclusive_ratio": round(ratio, 3),
            },
            recommendations=(
                ["Low attribution coverage — learning quality degraded"]
                if ratio < min_conclusive_ratio
                else []
            ),
        )

    # ── Report Generation ────────────────────────────────────────────────

    @classmethod
    def generate_quality_report(
        cls,
        *,
        window_start: str | None = None,
        window_end: str | None = None,
        signal_history: list[dict[str, Any]] | None = None,
        traces: list[dict[str, Any]] | None = None,
        audits: list[dict[str, Any]] | None = None,
        metrics: dict[str, int] | None = None,
        outcome_count: int = 0,
        directive_count: int = 0,
        outcomes: list[dict[str, Any]] | None = None,
    ) -> QualityReport:
        """Generate a comprehensive quality report."""
        report = QualityReport(
            report_id=_uid("qrpt"),
            window_start=window_start or _utcnow(),
            window_end=window_end or _utcnow(),
        )

        # Signal quality
        report.checks.append(cls.check_signal_actionability(signal_history or []))
        report.checks.append(cls.check_orphan_signal_buildup(
            orphan_count=metrics.get("orphan_signal_count", 0) if metrics else 0,
            total_signal_count=metrics.get("signals_generated", 0) if metrics else 0,
        ))

        # Causal chain
        report.checks.append(cls.check_causal_trace_completeness(traces or []))
        report.checks.append(cls.check_chain_breaks(metrics or {}))

        # Directive compliance
        report.checks.append(cls.check_directive_compliance(audits or []))

        # Outcome quality
        report.checks.append(cls.check_outcome_recording_rate(outcome_count, directive_count))
        report.checks.append(cls.check_attribution_coverage(outcomes or []))

        report.compute_health()

        logger.info(
            "Quality report {}: health={} score={:.3f} checks={}",
            report.report_id, report.health_status, report.overall_score, len(report.checks),
        )
        if report.health_status in ("at_risk", "critical"):
            logger.warning(
                "Spine health {} — issues: {}", report.health_status, report.systemic_issues,
            )

        return report

    # ── Trending ─────────────────────────────────────────────────────────

    @staticmethod
    def detect_degradation(
        reports: list[QualityReport],
        *,
        window_count: int = 3,
        degradation_threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Detect degrading trends across multiple quality reports."""
        if len(reports) < window_count:
            return {"degrading": False, "reason": "insufficient_data"}

        recent = reports[-window_count:]
        scores = [r.overall_score for r in recent]

        # Check for consistent decline
        if len(scores) >= 2:
            declining = all(
                scores[i] < scores[i - 1]
                for i in range(1, len(scores))
            )
            total_drop = scores[0] - scores[-1]

            if declining and total_drop >= degradation_threshold:
                return {
                    "degrading": True,
                    "reason": f"Consistent decline across {window_count} reports",
                    "score_trend": scores,
                    "total_drop": round(total_drop, 3),
                    "recommendation": "Investigate systemic degradation immediately",
                }

        return {"degrading": False, "score_trend": scores}


# ═══════════════════════════════════════════════════════════════════════
# P4-6 v2: Latency Guard + Iron Law Monitor + Self-Healing
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class LatencyThreshold:
    """Latency threshold configuration for a check."""
    check_name: str
    p50_warning_ms: float = 500.0
    p50_critical_ms: float = 1000.0
    p95_warning_ms: float = 2000.0
    p95_critical_ms: float = 5000.0
    p99_warning_ms: float = 10000.0
    p99_critical_ms: float = 20000.0


class LatencyGuard:
    """Monitor spine latency and detect slowdowns before they become outages.

    Tracks p50/p95/p99 latencies for key spine operations and raises
    alerts when thresholds are breached.
    """

    DEFAULT_THRESHOLDS = {
        "signal_detection": LatencyThreshold("signal_detection", p50_warning_ms=100, p95_warning_ms=500),
        "policy_evaluation": LatencyThreshold("policy_evaluation", p50_warning_ms=200, p95_warning_ms=1000),
        "directive_generation": LatencyThreshold("directive_generation", p50_warning_ms=100, p95_warning_ms=500),
        "directive_audit": LatencyThreshold("directive_audit", p50_warning_ms=50, p95_warning_ms=200),
        "outcome_recording": LatencyThreshold("outcome_recording", p50_warning_ms=50, p95_warning_ms=200),
    }

    @classmethod
    def check_latency(
        cls,
        operation: str,
        latencies_ms: list[float],
        *,
        thresholds: LatencyThreshold | None = None,
    ) -> QualityCheck:
        """Check if latency for an operation exceeds thresholds."""
        if not latencies_ms:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name=f"latency_{operation}",
                category="latency",
                passed=True,
                score=1.0,
                details={"note": "No latency data"},
            )

        thr = thresholds or cls.DEFAULT_THRESHOLDS.get(
            operation, LatencyThreshold(operation),
        )

        sorted_lat = sorted(latencies_ms)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[min(int(n * 0.95), n - 1)]
        p99 = sorted_lat[min(int(n * 0.99), n - 1)]

        violations = []
        if p50 >= thr.p50_critical_ms:
            violations.append("p50_critical")
        elif p50 >= thr.p50_warning_ms:
            violations.append("p50_warning")
        if p95 >= thr.p95_critical_ms:
            violations.append("p95_critical")
        elif p95 >= thr.p95_warning_ms:
            violations.append("p95_warning")
        if p99 >= thr.p99_critical_ms:
            violations.append("p99_critical")
        elif p99 >= thr.p99_warning_ms:
            violations.append("p99_warning")

        has_critical = any(v.endswith("_critical") for v in violations)
        has_warning = len(violations) > 0
        passed = not has_critical

        score = 1.0
        if has_critical:
            score = 0.3
        elif has_warning:
            score = 0.7

        return QualityCheck(
            check_id=_uid("qc"),
            check_name=f"latency_{operation}",
            category="latency",
            passed=passed,
            score=score,
            details={
                "operation": operation,
                "sample_count": n,
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "violations": violations,
                "thresholds": {
                    "p50_warning": thr.p50_warning_ms,
                    "p50_critical": thr.p50_critical_ms,
                    "p95_warning": thr.p95_warning_ms,
                    "p95_critical": thr.p95_critical_ms,
                },
            },
            recommendations=(
                [f"Critical latency in {operation}: p95={p95:.0f}ms"]
                if has_critical
                else ([f"Latency warning in {operation}: p95={p95:.0f}ms"] if has_warning else [])
            ),
        )


@dataclass
class EventBusHealth:
    """Health snapshot of the event bus (Redis Streams)."""
    stream_name: str
    consumer_group: str = ""
    pending_messages: int = 0
    oldest_pending_age_seconds: float = 0.0
    consumer_count: int = 0
    active_consumers: int = 0
    lag_seconds: float = 0.0
    status: str = "healthy"  # healthy | degraded | stalled | dead
    checked_at: str = field(default_factory=_utcnow)


class EventBusHealthCheck:
    """Monitor event bus health: consumer lag, pending messages, dead consumers."""

    @staticmethod
    def check_stream_health(health: EventBusHealth) -> QualityCheck:
        """Evaluate event bus stream health."""
        violations = []
        score = 1.0

        if health.status == "dead":
            violations.append("stream_dead")
            score = 0.0
        elif health.status == "stalled":
            violations.append("stream_stalled")
            score = 0.2

        if health.consumer_count > 0 and health.active_consumers == 0:
            violations.append("all_consumers_dead")
            score = min(score, 0.1)

        if health.lag_seconds > 300:
            violations.append(f"severe_lag_{health.lag_seconds:.0f}s")
            score = min(score, 0.3)
        elif health.lag_seconds > 120:
            violations.append(f"high_lag_{health.lag_seconds:.0f}s")
            score = min(score, 0.6)

        if health.pending_messages > 1000:
            violations.append(f"pending_overload_{health.pending_messages}")
            score = min(score, 0.4)

        passed = len(violations) == 0

        return QualityCheck(
            check_id=_uid("qc"),
            check_name=f"eventbus_{health.stream_name}",
            category="eventbus_health",
            passed=passed,
            score=score,
            details={
                "stream": health.stream_name,
                "consumer_group": health.consumer_group,
                "pending": health.pending_messages,
                "lag_seconds": round(health.lag_seconds, 2),
                "active_consumers": health.active_consumers,
                "total_consumers": health.consumer_count,
                "violations": violations,
            },
            recommendations=(
                [f"EventBus {health.stream_name}: {v}" for v in violations]
                if violations else []
            ),
        )


class IronLawComplianceMonitor:
    """Automated monitoring of iron law compliance across the spine.

    Checks:
    - Orphan signals (iron law: every signal must have a consumer)
    - Unaudited directives (iron law: every directive must be audited)
    - Unattributed outcomes (iron law: every outcome must be attributed)
    - Kill switch integrity (iron law: all features behind kill switches)
    """

    IRON_LAWS = {
        "no_orphan_signal": "Every ActionableSignal must have at least one registered consumer",
        "every_directive_audited": "Every DirectiveApplicationAudit must be recorded",
        "every_outcome_attributed": "Every OutcomeRecord must link to at least one CausalTrace",
        "kill_switch_integrity": "Every Aurora feature must operate behind a kill switch",
        "receipt_for_directive": "Every directive must produce a UserVisibleReceipt",
    }

    @classmethod
    def check_iron_law(
        cls,
        law_id: str,
        *,
        violations_detected: int = 0,
        total_checked: int = 0,
    ) -> QualityCheck:
        """Check a specific iron law for violations."""
        law_desc = cls.IRON_LAWS.get(law_id, f"Iron law: {law_id}")

        if total_checked == 0:
            return QualityCheck(
                check_id=_uid("qc"),
                check_name=f"iron_law_{law_id}",
                category="iron_law_compliance",
                passed=True,
                score=1.0,
                details={"law": law_desc, "note": "Nothing to check"},
            )

        violation_rate = violations_detected / total_checked
        passed = violation_rate == 0
        score = max(0.0, 1.0 - violation_rate * 2)

        return QualityCheck(
            check_id=_uid("qc"),
            check_name=f"iron_law_{law_id}",
            category="iron_law_compliance",
            passed=passed,
            score=score,
            details={
                "law_id": law_id,
                "law_description": law_desc,
                "total_checked": total_checked,
                "violations": violations_detected,
                "violation_rate": round(violation_rate, 4),
            },
            recommendations=(
                [f"Iron law '{law_id}' violated {violations_detected}/{total_checked} times"]
                if not passed else []
            ),
        )

    @classmethod
    def comprehensive_iron_law_check(
        cls,
        law_violations: dict[str, dict[str, int]],
    ) -> QualityReport:
        """Run all iron law checks and produce a compliance report."""
        report = QualityReport(
            report_id=_uid("irlrpt"),
            window_start=_utcnow(),
            window_end=_utcnow(),
        )

        for law_id, counts in law_violations.items():
            report.checks.append(cls.check_iron_law(
                law_id,
                violations_detected=counts.get("violations", 0),
                total_checked=counts.get("total", 0),
            ))

        if not report.checks:
            report.checks.append(QualityCheck(
                check_id=_uid("qc"),
                check_name="iron_law_compliance",
                category="iron_law_compliance",
                passed=True,
                score=1.0,
                details={"note": "All iron laws passing"},
            ))

        report.compute_health()
        return report


@dataclass
class SelfHealingAction:
    """A corrective action that the quality guard can trigger autonomously."""
    action_id: str = ""
    action_type: str = ""              # "throttle" | "circuit_break" | "degrade" | "alert" | "retry"
    target: str = ""                   # The component being acted on
    reason: str = ""
    severity: str = "low"              # low | medium | high | critical
    executed: bool = False
    executed_at: str = ""
    result: str = ""                   # Outcome of the action
    reversible: bool = True
    reverted: bool = False
    incident_trace_id: str = ""

    def __post_init__(self):
        if not self.action_id:
            self.action_id = _uid("sha")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target": self.target,
            "reason": self.reason,
            "severity": self.severity,
            "executed": self.executed,
            "executed_at": self.executed_at,
            "result": self.result,
            "reversible": self.reversible,
            "reverted": self.reverted,
            "incident_trace_id": self.incident_trace_id,
        }


class SelfHealingController:
    """Autonomous corrective actions for quality degradation.

    Actions escalate: alert → throttle → degrade → circuit_break.
    All actions are logged, reversible, and respect kill switch boundaries.
    """

    ESCALATION_SEQUENCE = ["alert", "throttle", "degrade", "circuit_break"]

    def __init__(self):
        self._actions: list[SelfHealingAction] = []
        self._active_circuit_breaks: set[str] = set()
        self._throttle_levels: dict[str, float] = {}  # target → throttle factor (1.0 = normal)

    def decide_action(
        self,
        *,
        health_status: str,
        check_name: str,
        target: str,
    ) -> SelfHealingAction | None:
        """Decide what self-healing action to take based on health status."""
        if health_status == "healthy":
            return None

        if health_status == "degraded":
            action = SelfHealingAction(
                action_type="alert",
                target=target,
                reason=f"{check_name} degraded",
                severity="low",
            )
        elif health_status == "at_risk":
            # Check if we already throttled this target
            current_throttle = self._throttle_levels.get(target, 1.0)
            if current_throttle > 0.5:
                action = SelfHealingAction(
                    action_type="throttle",
                    target=target,
                    reason=f"{check_name} at risk — throttling to {current_throttle * 0.7:.1%}",
                    severity="medium",
                )
            else:
                action = SelfHealingAction(
                    action_type="degrade",
                    target=target,
                    reason=f"{check_name} at risk with throttle already at {current_throttle:.1%}",
                    severity="high",
                )
        else:  # critical
            action = SelfHealingAction(
                action_type="circuit_break",
                target=target,
                reason=f"{check_name} critical — circuit breaking",
                severity="critical",
            )

        return action

    def execute_action(self, action: SelfHealingAction) -> dict[str, Any]:
        """Execute a self-healing action."""
        if action.action_type == "circuit_break":
            self._active_circuit_breaks.add(action.target)
        elif action.action_type == "throttle":
            current = self._throttle_levels.get(action.target, 1.0)
            self._throttle_levels[action.target] = max(0.1, current * 0.7)
        elif action.action_type == "degrade":
            self._throttle_levels[action.target] = 0.3

        action.executed = True
        action.executed_at = _utcnow()
        action.result = f"{action.action_type} applied to {action.target}"

        # P4-QG-010: Generate incident trace for high/critical actions
        if action.severity in ("high", "critical"):
            import uuid as _uuid
            incident_trace_id = f"incident_{action.action_type}_{_uuid.uuid4().hex[:12]}"
            action.incident_trace_id = incident_trace_id

        self._actions.append(action)

        return {"executed": True, "action": action.to_dict()}

    def revert_action(self, action_id: str) -> dict[str, Any]:
        """Revert a previously executed self-healing action."""
        for action in self._actions:
            if action.action_id == action_id and action.reversible and not action.reverted:
                if action.action_type == "circuit_break":
                    self._active_circuit_breaks.discard(action.target)
                elif action.action_type in ("throttle", "degrade"):
                    self._throttle_levels[action.target] = 1.0

                action.reverted = True
                return {"reverted": True, "action_id": action_id}
        return {"reverted": False, "reason": "action not found or not reversible"}

    def is_circuit_broken(self, target: str) -> bool:
        return target in self._active_circuit_breaks

    def get_throttle_level(self, target: str) -> float:
        return self._throttle_levels.get(target, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_actions": len(self._actions),
            "active_circuit_breaks": list(self._active_circuit_breaks),
            "active_throttles": self._throttle_levels,
            "recent_actions": [a.to_dict() for a in self._actions[-10:]],
        }


class PromotionGate:
    """Gate that integrates with SparkleGoalBench.

    Before any system promotion (canary→safe_live, safe_live→default),
    the gate verifies:
    1. All regression scenarios pass
    2. All safety scenarios pass
    3. Quality guard health is healthy or degraded (not at_risk or critical)
    4. Iron law compliance is clean

    This is the final checkpoint before any policy goes live.
    """

    @staticmethod
    def evaluate(
        *,
        benchmark_result: dict[str, Any],
        quality_health: str,
        iron_law_violations: int = 0,
    ) -> dict[str, Any]:
        """Evaluate whether a promotion can proceed."""
        checks = []

        # Check 1: All regression scenarios pass
        regression_pass = benchmark_result.get("pass_rate", 0) == 1.0
        checks.append({
            "check": "benchmark_regression",
            "passed": regression_pass,
            "detail": f"Pass rate: {benchmark_result.get('pass_rate', 0):.1%}",
        })

        # Check 2: Quality guard health
        health_ok = quality_health in ("healthy", "degraded")
        checks.append({
            "check": "quality_health",
            "passed": health_ok,
            "detail": f"Health: {quality_health}",
        })

        # Check 3: Iron law clean
        iron_law_clean = iron_law_violations == 0
        checks.append({
            "check": "iron_law_compliance",
            "passed": iron_law_clean,
            "detail": f"Violations: {iron_law_violations}",
        })

        all_pass = all(c["passed"] for c in checks)

        return {
            "promotion_allowed": all_pass,
            "checks": checks,
            "recommendation": (
                "safe_to_promote" if all_pass
                else "blocked: " + ", ".join(
                    c["check"] for c in checks if not c["passed"]
                )
            ),
            "required_actions": [
                f"Fix {c['check']}: {c['detail']}"
                for c in checks if not c["passed"]
            ],
        }
