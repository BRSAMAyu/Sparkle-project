"""
Core: execution / research
Phase: adapt
Stage: P4-7 — Research Mode: Continuous Improvement Loop

Unified research workflow that integrates all P4 capabilities:
  - Counterfactual evaluation (P4-1)
  - Safe adaptive experiments (P4-2)
  - Pre-launch simulation (P4-3)
  - Knowledge marketplace (P4-4)
  - Privacy-preserving community (P4-5)
  - Autonomous quality guard (P4-6)

The Research Mode is the "operating system upgrade loop" — it continuously
detects gaps, proposes experiments, runs them safely, measures outcomes,
and applies validated improvements.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# 1. Research Proposal
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ResearchProposal:
    """A research proposal for system improvement.

    Generated from detected gaps in: quality guard reports, counterfactual
    evaluations, or community signals.
    """
    proposal_id: str = ""
    title: str = ""
    description: str = ""
    source: str = ""                    # "quality_guard" | "counterfactual" | "community" | "simulation"
    source_detail: str = ""             # Link to the triggering evidence
    hypothesis: str = ""
    target_metric: str = ""             # What metric should improve
    expected_effect_size: float = 0.0   # Estimated Cohen's d or relative improvement
    risk_level: str = "low"             # low | medium | high | critical
    domain: str = ""                    # "exam_sprint" | "project_delivery" | ...
    proposed_policies: list[str] = field(default_factory=list)
    required_sample_size: int = 0
    estimated_duration_days: int = 7
    status: str = "draft"               # draft | under_review | approved | running | completed | rejected
    evidence_grade: int = 0            # Current best evidence for this proposal
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = _uid("rp")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "source_detail": self.source_detail,
            "hypothesis": self.hypothesis,
            "target_metric": self.target_metric,
            "expected_effect_size": self.expected_effect_size,
            "risk_level": self.risk_level,
            "domain": self.domain,
            "proposed_policies": self.proposed_policies,
            "required_sample_size": self.required_sample_size,
            "estimated_duration_days": self.estimated_duration_days,
            "status": self.status,
            "evidence_grade": self.evidence_grade,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 2. Research Conclusion
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ResearchConclusion:
    """Comprehensive research conclusion with all evidence integrated."""
    conclusion_id: str = ""
    proposal_id: str = ""
    experiment_id: str = ""
    title: str = ""
    summary: str = ""
    evidence_grade: int = 0
    effect_size: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    statistical_significance: bool = False
    practical_significance: bool = False
    guardrail_violations: list[str] = field(default_factory=list)
    counterfactual_estimate: dict[str, Any] = field(default_factory=dict)
    simulation_result: dict[str, Any] = field(default_factory=dict)
    community_signal: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    action: str = ""                    # "promote" | "continue_testing" | "abandon" | "more_research"
    concluded_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.conclusion_id:
            self.conclusion_id = _uid("rc")

    def to_dict(self) -> dict[str, Any]:
        return {
            "conclusion_id": self.conclusion_id,
            "proposal_id": self.proposal_id,
            "experiment_id": self.experiment_id,
            "title": self.title,
            "summary": self.summary,
            "evidence_grade": self.evidence_grade,
            "effect_size": self.effect_size,
            "confidence_interval": list(self.confidence_interval),
            "statistical_significance": self.statistical_significance,
            "practical_significance": self.practical_significance,
            "guardrail_violations": self.guardrail_violations,
            "counterfactual_estimate": self.counterfactual_estimate,
            "simulation_result": self.simulation_result,
            "community_signal": self.community_signal,
            "limitations": self.limitations,
            "recommendations": self.recommendations,
            "action": self.action,
            "concluded_at": self.concluded_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. Research Dashboard
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ResearchDashboard:
    """Aggregated view of all research activity in the system.

    Provides a single pane of glass for all P4 capabilities.
    """
    dashboard_id: str = ""
    generated_at: str = field(default_factory=_utcnow)

    # Experiment overview
    active_experiments: int = 0
    completed_experiments: int = 0
    total_episodes_collected: int = 0
    total_users_reached: int = 0

    # Evidence pipeline
    evidence_distribution: dict[str, int] = field(default_factory=lambda: {
        "grade_0": 0, "grade_1": 0, "grade_2": 0, "grade_3": 0,
        "grade_4": 0, "grade_5": 0,
    })
    average_evidence_grade: float = 0.0

    # Quality
    quality_health: str = "unknown"
    quality_score: float = 0.0
    iron_law_violations: int = 0

    # Marketplace
    marketplace_cards: int = 0
    marketplace_adoptions: int = 0
    average_card_effectiveness: float = 0.0

    # Community
    active_cohorts: int = 0
    cohort_members_total: int = 0
    federated_insights: int = 0

    # Simulation
    benchmark_pass_rate: float = 0.0
    regression_scenarios: int = 0

    # Improvement loop
    proposals_active: int = 0
    proposals_completed: int = 0
    proposals_promoted: int = 0

    def __post_init__(self):
        if not self.dashboard_id:
            self.dashboard_id = _uid("rdb")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "generated_at": self.generated_at,
            "active_experiments": self.active_experiments,
            "completed_experiments": self.completed_experiments,
            "total_episodes_collected": self.total_episodes_collected,
            "total_users_reached": self.total_users_reached,
            "evidence_distribution": self.evidence_distribution,
            "average_evidence_grade": self.average_evidence_grade,
            "quality_health": self.quality_health,
            "quality_score": self.quality_score,
            "iron_law_violations": self.iron_law_violations,
            "marketplace_cards": self.marketplace_cards,
            "marketplace_adoptions": self.marketplace_adoptions,
            "average_card_effectiveness": self.average_card_effectiveness,
            "active_cohorts": self.active_cohorts,
            "cohort_members_total": self.cohort_members_total,
            "federated_insights": self.federated_insights,
            "benchmark_pass_rate": self.benchmark_pass_rate,
            "regression_scenarios": self.regression_scenarios,
            "proposals_active": self.proposals_active,
            "proposals_completed": self.proposals_completed,
            "proposals_promoted": self.proposals_promoted,
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. Gap Detector
# ═══════════════════════════════════════════════════════════════════════


class GapDetector:
    """Detect system improvement gaps from quality signals.

    Monitors quality guard reports, counterfactual evaluations, and
    community signals to produce research proposals.
    """

    @staticmethod
    def from_quality_report(
        quality_health: str,
        quality_score: float,
        systemic_issues: list[str],
        *,
        domain: str = "global",
    ) -> list[ResearchProposal]:
        """Generate research proposals from quality guard findings."""
        proposals: list[ResearchProposal] = []

        if quality_health in ("at_risk", "critical"):
            proposals.append(ResearchProposal(
                title=f"Quality Restoration: {quality_health}",
                description=f"System health is {quality_health} (score={quality_score:.2f}). "
                f"Issues: {', '.join(systemic_issues[:3])}",
                source="quality_guard",
                source_detail=f"health={quality_health}, score={quality_score:.2f}",
                hypothesis="Addressing systemic quality issues will restore health to healthy/degraded",
                target_metric="quality_score",
                expected_effect_size=0.3,
                risk_level="high" if quality_health == "critical" else "medium",
                domain=domain,
                evidence_grade=1,
            ))

        if quality_health == "degraded":
            proposals.append(ResearchProposal(
                title="Quality Uplift: Degraded Components",
                description=f"System is degraded with issues: {', '.join(systemic_issues[:3])}",
                source="quality_guard",
                source_detail=f"health={quality_health}",
                hypothesis="Targeted fixes to degraded components will restore full health",
                target_metric="quality_score",
                expected_effect_size=0.15,
                risk_level="low",
                domain=domain,
                evidence_grade=1,
            ))

        return proposals

    @staticmethod
    def from_counterfactual_gap(
        comparison: dict[str, Any],
        *,
        domain: str = "global",
    ) -> ResearchProposal | None:
        """Generate a proposal from a counterfactual evaluation gap."""
        if not comparison.get("recommendation") or comparison.get("recommendation") == "no_change":
            return None

        best = comparison.get("best_policy", "unknown")
        effect = comparison.get("effect_size", 0)

        return ResearchProposal(
            title=f"Policy Upgrade: {best}",
            description=f"Counterfactual evaluation found {best} superior "
            f"(effect_size={effect:.3f}, grade={comparison.get('evidence_grade', 0)})",
            source="counterfactual",
            source_detail=comparison.get("recommendation", ""),
            hypothesis=f"Switching to {best} will improve outcomes by {effect:.1%}",
            target_metric="primary_reward",
            expected_effect_size=abs(effect),
            risk_level="low" if comparison.get("evidence_grade", 0) >= 3 else "medium",
            domain=domain,
            proposed_policies=[best],
            evidence_grade=comparison.get("evidence_grade", 0),
        )

    @staticmethod
    def from_benchmark_failure(
        benchmark_result: dict[str, Any],
        *,
        domain: str = "global",
    ) -> list[ResearchProposal]:
        """Generate proposals from benchmark failures."""
        if benchmark_result.get("pass_rate", 1.0) >= 1.0:
            return []

        failing = []
        for report in benchmark_result.get("reports", []):
            if not report.get("passed"):
                failing.append(report)

        proposals = []
        for fail in failing[:3]:  # Top 3 failures
            proposals.append(ResearchProposal(
                title=f"Fix Regression: {fail.get('scenario_id', 'unknown')}",
                description=f"Scenario {fail.get('scenario_id')} failed with violations: "
                f"{fail.get('violations', [])}",
                source="simulation",
                source_detail=str(fail.get("violations", [])),
                hypothesis="Fixing this regression will restore benchmark pass rate",
                target_metric="benchmark_pass_rate",
                expected_effect_size=0.1,
                risk_level="medium",
                domain=domain,
                evidence_grade=2,
            ))

        return proposals


# ═══════════════════════════════════════════════════════════════════════
# 5. Continuous Improvement Loop
# ═══════════════════════════════════════════════════════════════════════


class ContinuousImprovementLoop:
    """The unified continuous improvement loop orchestrator.

    This is the "brain" of P4-7 — it continuously:
    1. Detects gaps from quality guard, counterfactual, and benchmarks
    2. Generates research proposals
    3. Prioritizes proposals by expected impact and risk
    4. Tracks proposal → experiment → conclusion → promotion lifecycle
    5. Measures system-wide improvement over time
    """

    def __init__(self):
        self._proposals: dict[str, ResearchProposal] = {}
        self._conclusions: dict[str, ResearchConclusion] = {}
        self._improvement_log: list[dict[str, Any]] = []

    # ── Proposal Management ──────────────────────────────────────────────

    def ingest_gaps(
        self,
        *,
        quality_health: str = "healthy",
        quality_score: float = 1.0,
        systemic_issues: list[str] | None = None,
        counterfactual_comparisons: list[dict[str, Any]] | None = None,
        benchmark_result: dict[str, Any] | None = None,
        domain: str = "global",
    ) -> list[ResearchProposal]:
        """Ingest gaps from all sources and generate proposals."""
        new_proposals: list[ResearchProposal] = []

        # Quality guard gaps
        new_proposals.extend(GapDetector.from_quality_report(
            quality_health, quality_score,
            systemic_issues or [], domain=domain,
        ))

        # Counterfactual gaps
        for comp in (counterfactual_comparisons or []):
            prop = GapDetector.from_counterfactual_gap(comp, domain=domain)
            if prop:
                new_proposals.append(prop)

        # Benchmark gaps
        if benchmark_result:
            new_proposals.extend(GapDetector.from_benchmark_failure(
                benchmark_result, domain=domain,
            ))

        # Register new proposals
        for prop in new_proposals:
            if prop.proposal_id not in self._proposals:
                self._proposals[prop.proposal_id] = prop

        # Remove duplicates by similarity (same title ≈ same proposal)
        seen_titles = set()
        deduped = []
        for prop in new_proposals:
            if prop.title not in seen_titles:
                seen_titles.add(prop.title)
                deduped.append(prop)

        if deduped:
            self._improvement_log.append({
                "event": "gaps_ingested",
                "new_proposals": len(deduped),
                "sources": {
                    "quality": quality_health != "healthy",
                    "counterfactual": bool(counterfactual_comparisons),
                    "benchmark": benchmark_result is not None,
                },
                "timestamp": _utcnow(),
            })

        return deduped

    def prioritize_proposals(
        self,
        proposals: list[ResearchProposal] | None = None,
    ) -> list[dict[str, Any]]:
        """Prioritize proposals by: evidence grade, risk level, expected effect.

        High evidence + high effect + low risk = top priority.
        """
        targets = proposals or list(self._proposals.values())
        active = [p for p in targets if p.status in ("draft", "under_review", "approved")]

        def priority_score(p: ResearchProposal) -> float:
            evidence_weight = min(p.evidence_grade / 5.0, 1.0) * 0.3
            effect_weight = min(abs(p.expected_effect_size), 1.0) * 0.4
            risk_weight = (1.0 - {"low": 0.0, "medium": 0.3, "high": 0.6, "critical": 1.0}[p.risk_level]) * 0.3
            return evidence_weight + effect_weight + risk_weight

        sorted_proposals = sorted(active, key=priority_score, reverse=True)

        return [
            {
                "proposal_id": p.proposal_id,
                "title": p.title,
                "priority_score": round(priority_score(p), 3),
                "evidence_grade": p.evidence_grade,
                "expected_effect_size": p.expected_effect_size,
                "risk_level": p.risk_level,
                "status": p.status,
            }
            for p in sorted_proposals
        ]

    def get_top_proposal(self) -> dict[str, Any] | None:
        """Get the highest-priority proposal ready for experimentation."""
        ranked = self.prioritize_proposals()
        if not ranked:
            return None
        top = ranked[0]
        top["proposal"] = self._proposals[top["proposal_id"]].to_dict()
        return top

    # ── Conclusion Management ────────────────────────────────────────────

    def record_conclusion(self, conclusion: ResearchConclusion) -> dict[str, Any]:
        """Record a research conclusion and update the improvement log."""
        self._conclusions[conclusion.conclusion_id] = conclusion

        # Update proposal status
        if conclusion.proposal_id in self._proposals:
            prop = self._proposals[conclusion.proposal_id]
            if conclusion.action == "promote":
                prop.status = "completed"
            elif conclusion.action == "abandon":
                prop.status = "completed"

        log_entry = {
            "event": "conclusion_recorded",
            "conclusion_id": conclusion.conclusion_id,
            "action": conclusion.action,
            "evidence_grade": conclusion.evidence_grade,
            "effect_size": conclusion.effect_size,
            "timestamp": _utcnow(),
        }

        if conclusion.action == "promote":
            log_entry["impact"] = f"Promoted with effect size {conclusion.effect_size:.3f}"
            self._improvement_log.append(log_entry)
        else:
            log_entry["impact"] = f"No promotion (action={conclusion.action})"
            self._improvement_log.append(log_entry)

        return {"recorded": True, "conclusion_id": conclusion.conclusion_id}

    # ── System Improvement Measurement ───────────────────────────────────

    def measure_improvement(self) -> dict[str, Any]:
        """Measure system-wide improvement over the loop's lifetime."""
        promoted = [
            c for c in self._conclusions.values()
            if c.action == "promote"
        ]

        if not promoted:
            return {
                "total_conclusions": len(self._conclusions),
                "promoted_count": 0,
                "cumulative_effect": 0.0,
                "average_evidence_grade": 0.0,
                "improvement_trajectory": "no_data",
            }

        cumulative_effect = sum(c.effect_size for c in promoted)
        avg_grade = sum(c.evidence_grade for c in promoted) / len(promoted)

        # Trajectory: are recent promotions more effective than earlier ones?
        sorted_promoted = sorted(promoted, key=lambda c: c.concluded_at)
        if len(sorted_promoted) >= 2:
            midpoint = len(sorted_promoted) // 2
            early_avg = sum(c.effect_size for c in sorted_promoted[:midpoint]) / midpoint
            late_avg = sum(c.effect_size for c in sorted_promoted[midpoint:]) / (len(sorted_promoted) - midpoint)
            trajectory = "accelerating" if late_avg > early_avg else "decelerating" if late_avg < early_avg else "stable"
        else:
            trajectory = "single_promotion"

        return {
            "total_conclusions": len(self._conclusions),
            "promoted_count": len(promoted),
            "cumulative_effect": round(cumulative_effect, 3),
            "average_evidence_grade": round(avg_grade, 2),
            "improvement_trajectory": trajectory,
            "recent_promotions": [
                {"title": c.title, "effect_size": c.effect_size, "action": c.action}
                for c in sorted_promoted[-5:]
            ],
        }

    def build_dashboard(
        self,
        *,
        experiment_registry: dict[str, Any] | None = None,
        marketplace_registry: dict[str, Any] | None = None,
        quality_health: str = "healthy",
        quality_score: float = 1.0,
        iron_law_violations: int = 0,
        benchmark_pass_rate: float = 1.0,
        total_regression_scenarios: int = 0,
        community_stats: dict[str, Any] | None = None,
    ) -> ResearchDashboard:
        """Build a comprehensive research dashboard from all P4 data sources."""
        dashboard = ResearchDashboard()

        # Experiment data
        if experiment_registry:
            dashboard.active_experiments = experiment_registry.get("active_experiments", 0)
            dashboard.completed_experiments = experiment_registry.get("completed_experiments", 0)
            dashboard.total_episodes_collected = experiment_registry.get("total_episodes", 0)
            dashboard.total_users_reached = experiment_registry.get("total_users", 0)

        # Quality
        dashboard.quality_health = quality_health
        dashboard.quality_score = quality_score
        dashboard.iron_law_violations = iron_law_violations

        # Marketplace
        if marketplace_registry:
            dashboard.marketplace_cards = marketplace_registry.get("total_cards", 0)
            dashboard.marketplace_adoptions = marketplace_registry.get("total_adoptions", 0)
            active_cards = [c for c in marketplace_registry.get("cards", []) if c.get("status") == "active"]
            if active_cards:
                dashboard.average_card_effectiveness = round(
                    sum(c.get("effectiveness_decay", 1.0) for c in active_cards) / len(active_cards), 3,
                )

        # Community
        if community_stats:
            dashboard.active_cohorts = community_stats.get("active_cohorts", 0)
            dashboard.cohort_members_total = community_stats.get("total_members", 0)
            dashboard.federated_insights = community_stats.get("federated_insights", 0)

        # Benchmark
        dashboard.benchmark_pass_rate = benchmark_pass_rate
        dashboard.regression_scenarios = total_regression_scenarios

        # Proposals
        dashboard.proposals_active = sum(
            1 for p in self._proposals.values() if p.status in ("draft", "under_review", "approved", "running")
        )
        dashboard.proposals_completed = sum(
            1 for p in self._proposals.values() if p.status == "completed"
        )
        dashboard.proposals_promoted = sum(
            1 for c in self._conclusions.values() if c.action == "promote"
        )

        return dashboard

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_proposals": len(self._proposals),
            "active_proposals": sum(
                1 for p in self._proposals.values() if p.status in ("draft", "under_review", "approved", "running")
            ),
            "total_conclusions": len(self._conclusions),
            "improvement_log_entries": len(self._improvement_log),
            "improvement_summary": self.measure_improvement(),
            "recent_log": self._improvement_log[-10:],
        }
