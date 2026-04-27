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
from datetime import datetime, timezone
from typing import Any

from loguru import logger


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
