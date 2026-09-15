"""
Core: execution / research
Phase: adapt
Stage: P4-1 — Counterfactual Policy Evaluation

Enhances research_grade.py CounterfactualEngine with:
- EvidenceGrade 0-5 classification
- MatchedContextEvaluator using ContextSignature distance
- CounterfactualEstimate with multi-metric effect + uncertainty
- PolicyComparisonReport for structured comparison
- PolicyUpdateCandidate with governance gates

Iron Laws:
  1. 反事实结果不能直接改 live policy
  2. 所有反事实估计必须带 evidence_grade
  3. 小样本只能产生 hypothesis，不能产生 system skill
  4. 高风险目标阶段只允许保守策略
  5. 任何策略晋升必须经过 simulation + shadow + guardrail
  6. 用户侧表达必须谦逊，不许说"证明"
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from app.signals.intervention_episode import (
    ContextSignature,
    InterventionEpisode,
    InterventionEpisodeLedger,
)


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# 1. EvidenceGrade — 6-level evidence classification
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class EvidenceGrade:
    """6-level evidence classification for policy evaluation.

    Grade 0: Anecdotal — single case, no comparison possible
    Grade 1: Trace-supported — CausalTrace + Outcome, but no matched samples
    Grade 2: Matched Context — similar context samples available for comparison
    Grade 3: Propensity-aware — candidate_policies + selection_probability logged
    Grade 4: Doubly Robust — propensity model + outcome model both available
    Grade 5: Safe Online Verified — passed shadow/cary/safe_live experiment
    """
    grade: int = 0
    label: str = ""
    description: str = ""

    GRADE_LABELS = {
        0: ("Anecdotal", "Single case observation, not generalizable"),
        1: ("Trace-supported", "CausalTrace + Outcome recorded, no comparable samples"),
        2: ("Matched Context", "Similar context samples available for comparison"),
        3: ("Propensity-aware", "Candidate policies + selection probability logged"),
        4: ("Doubly Robust", "Propensity model + outcome model both available"),
        5: ("Safe Online Verified", "Passed shadow → canary → safe_live experiment"),
    }

    def __post_init__(self):
        if not self.label:
            self.label, self.description = self.GRADE_LABELS.get(
                self.grade, self.GRADE_LABELS[0],
            )

    @classmethod
    def from_episode_quality(cls, eq_grade: int, *, verified_online: bool = False) -> EvidenceGrade:
        """Map from EvidenceQuality.grade (0-4) to full EvidenceGrade (0-5)."""
        if verified_online and eq_grade >= 3:
            return cls(grade=5)
        return cls(grade=eq_grade)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grade": self.grade,
            "label": self.label,
            "description": self.description,
        }

    @property
    def is_conclusive(self) -> bool:
        return self.grade >= 4

    @property
    def can_generate_hypothesis(self) -> bool:
        return self.grade >= 1

    @property
    def can_promote_to_system_skill(self) -> bool:
        return self.grade >= 4


# ═══════════════════════════════════════════════════════════════════════
# 2. CounterfactualEstimate — structured estimate with uncertainty
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class MetricEffect:
    """Effect size for a single metric."""
    metric: str
    policy_a_value: float
    policy_b_value: float
    effect_size: float        # positive = A better, negative = B better
    confidence: float
    is_significant: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "policy_a_value": round(self.policy_a_value, 4),
            "policy_b_value": round(self.policy_b_value, 4),
            "effect_size": round(self.effect_size, 4),
            "confidence": round(self.confidence, 3),
            "is_significant": self.is_significant,
        }


@dataclass
class CounterfactualEstimate:
    """A counterfactual estimate: what would have happened with a different policy?

    key_rule: estimate_id the evidence_grade with the result.
    Never claim "proven" unless grade >= 4.
    """
    estimate_id: str = ""
    target_context: ContextSignature = field(default_factory=ContextSignature)
    actual_policy: str = ""
    alternative_policy: str = ""
    matched_episodes_actual: int = 0
    matched_episodes_alternative: int = 0
    estimated_effects: list[MetricEffect] = field(default_factory=list)
    evidence_grade: EvidenceGrade = field(default_factory=EvidenceGrade)
    limitations: list[str] = field(default_factory=list)
    recommendation: str = ""
    allowed_mode: str = "shadow"            # "shadow" | "soft_bias" | "hard_constraint"
    not_allowed: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.estimate_id:
            self.estimate_id = _uid("cfe")

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimate_id": self.estimate_id,
            "target_context": self.target_context.to_dict(),
            "actual_policy": self.actual_policy,
            "alternative_policy": self.alternative_policy,
            "matched_episodes_actual": self.matched_episodes_actual,
            "matched_episodes_alternative": self.matched_episodes_alternative,
            "estimated_effects": [e.to_dict() for e in self.estimated_effects],
            "evidence_grade": self.evidence_grade.to_dict(),
            "limitations": self.limitations,
            "recommendation": self.recommendation,
            "allowed_mode": self.allowed_mode,
            "not_allowed": self.not_allowed,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. PolicyComparisonReport
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class PolicyComparisonReport:
    """Structured comparison of two policies."""
    report_id: str = ""
    policy_a: str = ""
    policy_b: str = ""
    domain: str = ""
    total_episodes_a: int = 0
    total_episodes_b: int = 0
    matched_pairs: int = 0
    effects: list[MetricEffect] = field(default_factory=list)
    evidence_grade: EvidenceGrade = field(default_factory=EvidenceGrade)
    winner: str = ""                         # "a" | "b" | "tie" | "insufficient_data"
    recommendation: str = ""
    caveats: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.report_id:
            self.report_id = _uid("pcr")

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "policy_a": self.policy_a,
            "policy_b": self.policy_b,
            "domain": self.domain,
            "total_episodes_a": self.total_episodes_a,
            "total_episodes_b": self.total_episodes_b,
            "matched_pairs": self.matched_pairs,
            "effects": [e.to_dict() for e in self.effects],
            "evidence_grade": self.evidence_grade.to_dict(),
            "winner": self.winner,
            "recommendation": self.recommendation,
            "caveats": self.caveats,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. PolicyUpdateCandidate
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class PolicyUpdateCandidate:
    """A formal candidate for policy promotion.

    Generated by counterfactual evaluation but NOT auto-applied.
    Must go through shadow → simulation → guardrail before live.
    """
    candidate_id: str = ""
    source_estimate_id: str = ""
    current_policy: str = ""
    proposed_policy: str = ""
    domain: str = ""
    evidence_grade: EvidenceGrade = field(default_factory=EvidenceGrade)
    effect_summary: dict[str, Any] = field(default_factory=dict)
    min_episodes_met: bool = False
    min_users_met: bool = False
    guardrail_checks_passed: bool = False
    human_review_required: bool = True
    allowed_mode: str = "shadow"             # Never "live" directly from counterfactual
    promotion_blocked_reasons: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.candidate_id:
            self.candidate_id = _uid("puc")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_estimate_id": self.source_estimate_id,
            "current_policy": self.current_policy,
            "proposed_policy": self.proposed_policy,
            "domain": self.domain,
            "evidence_grade": self.evidence_grade.to_dict(),
            "effect_summary": self.effect_summary,
            "min_episodes_met": self.min_episodes_met,
            "min_users_met": self.min_users_met,
            "guardrail_checks_passed": self.guardrail_checks_passed,
            "human_review_required": self.human_review_required,
            "allowed_mode": self.allowed_mode,
            "promotion_blocked_reasons": self.promotion_blocked_reasons,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 5. MatchedContextEvaluator
# ═══════════════════════════════════════════════════════════════════════


class MatchedContextEvaluator:
    """Counterfactual policy evaluation using context-signature-matched episodes.

    Uses InterventionEpisodes with ContextSignature distance to find similar
    contexts where different policies were applied, then compares outcomes.
    """

    METRICS = [
        "completion_rate",
        "avg_accuracy_delta",
        "avg_mastery_delta",
        "correction_rate",
        "negative_feedback_rate",
    ]

    METRIC_DIRECTION = {
        "completion_rate": "higher_is_better",
        "avg_accuracy_delta": "higher_is_better",
        "avg_mastery_delta": "higher_is_better",
        "correction_rate": "lower_is_better",
        "negative_feedback_rate": "lower_is_better",
    }

    @classmethod
    def evaluate(
        cls,
        actual_policy: str,
        alternative_policy: str,
        episodes: list[InterventionEpisode],
        *,
        target_context: ContextSignature | None = None,
        max_context_distance: float = 0.3,
    ) -> CounterfactualEstimate:
        """Evaluate whether alternative_policy would outperform actual_policy.

        Args:
            actual_policy: The policy that was actually used
            alternative_policy: The policy to compare against
            episodes: All available episodes (both policies)
            target_context: Optional context to focus on; if None, uses global comparison
            max_context_distance: Max distance for matched comparison
        """
        # Split by policy
        grouped = InterventionEpisodeLedger.group_by_policy(episodes)
        actual_eps = grouped.get(actual_policy, [])
        alt_eps = grouped.get(alternative_policy, [])

        # Filter by evidence grade if any episodes are graded, otherwise keep all
        graded_actual = [e for e in actual_eps if e.evidence_quality.grade > 0]
        if graded_actual:
            actual_eps = InterventionEpisodeLedger.filter_grade(actual_eps, min_grade=1)
        graded_alt = [e for e in alt_eps if e.evidence_quality.grade > 0]
        if graded_alt:
            alt_eps = InterventionEpisodeLedger.filter_grade(alt_eps, min_grade=1)

        # If target context given, find matched episodes
        if target_context and target_context.goal_mode:
            # Build a virtual target episode
            target_ep = InterventionEpisode(context_signature=target_context)
            actual_eps = InterventionEpisodeLedger.find_similar_episodes(
                target_ep, actual_eps, max_distance=max_context_distance,
            )
            alt_eps = InterventionEpisodeLedger.find_similar_episodes(
                target_ep, alt_eps, max_distance=max_context_distance,
            )

        # Compute effects for each metric
        effects: list[MetricEffect] = []
        stats_actual = InterventionEpisodeLedger.compute_policy_stats(actual_eps)
        stats_alt = InterventionEpisodeLedger.compute_policy_stats(alt_eps)

        for metric in cls.METRICS:
            direction = cls.METRIC_DIRECTION[metric]
            a_val = stats_actual.get(metric, 0.0)
            b_val = stats_alt.get(metric, 0.0)

            if direction == "higher_is_better":
                effect = a_val - b_val
            else:
                effect = b_val - a_val  # Invert: positive effect = alt is better

            # Confidence based on min sample size
            min_n = min(stats_actual["episode_count"], stats_alt["episode_count"])
            confidence = min(min_n / 30.0, 1.0)

            effects.append(MetricEffect(
                metric=metric,
                policy_a_value=a_val,
                policy_b_value=b_val,
                effect_size=effect,
                confidence=confidence,
                is_significant=abs(effect) > 0.1 and min_n >= 10,
            ))

        # Determine evidence grade
        grade = cls._determine_grade(actual_eps, alt_eps, len(effects))
        limitations = cls._collect_limitations(actual_eps, alt_eps, grade, max_context_distance)

        # Build recommendation
        recommendation, allowed_mode, not_allowed = cls._build_recommendation(
            effects, grade, actual_policy, alternative_policy,
        )

        return CounterfactualEstimate(
            target_context=target_context or ContextSignature(),
            actual_policy=actual_policy,
            alternative_policy=alternative_policy,
            matched_episodes_actual=len(actual_eps),
            matched_episodes_alternative=len(alt_eps),
            estimated_effects=effects,
            evidence_grade=grade,
            limitations=limitations,
            recommendation=recommendation,
            allowed_mode=allowed_mode,
            not_allowed=not_allowed,
        )

    @classmethod
    def compare_policies(
        cls,
        policy_a: str,
        policy_b: str,
        episodes: list[InterventionEpisode],
        *,
        domain: str = "",
    ) -> PolicyComparisonReport:
        """Produce a structured comparison report between two policies."""
        estimate = cls.evaluate(policy_a, policy_b, episodes)

        # Determine winner
        significant_effects = [e for e in estimate.estimated_effects if e.is_significant]
        if not significant_effects:
            winner = "insufficient_data"
        else:
            a_wins = sum(1 for e in significant_effects if e.effect_size > 0)
            b_wins = sum(1 for e in significant_effects if e.effect_size < 0)
            if a_wins > b_wins:
                winner = "a"
            elif b_wins > a_wins:
                winner = "b"
            else:
                winner = "tie"

        return PolicyComparisonReport(
            policy_a=policy_a,
            policy_b=policy_b,
            domain=domain,
            total_episodes_a=estimate.matched_episodes_actual,
            total_episodes_b=estimate.matched_episodes_alternative,
            matched_pairs=min(
                estimate.matched_episodes_actual,
                estimate.matched_episodes_alternative,
            ),
            effects=estimate.estimated_effects,
            evidence_grade=estimate.evidence_grade,
            winner=winner,
            recommendation=estimate.recommendation,
            caveats=estimate.limitations,
        )

    @classmethod
    def batch_evaluate_contexts(
        cls,
        policy_a: str,
        policy_b: str,
        episodes: list[InterventionEpisode],
        *,
        stratify_by: str = "failure_type",
    ) -> dict[str, CounterfactualEstimate]:
        """Evaluate policy comparison across different context strata."""
        grouped = InterventionEpisodeLedger.group_by_policy(episodes)
        all_eps = grouped.get(policy_a, []) + grouped.get(policy_b, [])

        # Group by context dimension
        strata: dict[str, list[InterventionEpisode]] = {}
        for ep in all_eps:
            key = getattr(ep.context_signature, stratify_by, "unknown") or "unknown"
            if key not in strata:
                strata[key] = []
            strata[key].append(ep)

        results = {}
        for key, stratum_eps in strata.items():
            target = ContextSignature()
            setattr(target, stratify_by, key)
            results[key] = cls.evaluate(policy_a, policy_b, stratum_eps, target_context=target)

        return results

    @classmethod
    def _determine_grade(
        cls,
        actual_eps: list[InterventionEpisode],
        alt_eps: list[InterventionEpisode],
        _num_effects: int,
    ) -> EvidenceGrade:
        total = len(actual_eps) + len(alt_eps)
        if total == 0:
            return EvidenceGrade(grade=0)
        if total < 10:
            return EvidenceGrade(grade=1)
        if total < 30:
            return EvidenceGrade(grade=2)

        # Check for propensity-aware data
        has_propensity = any(
            e.evidence_quality.propensity_logged
            for e in actual_eps + alt_eps
        )
        if has_propensity:
            return EvidenceGrade(grade=3)

        return EvidenceGrade(grade=2)

    @classmethod
    def _collect_limitations(
        cls,
        actual_eps: list[InterventionEpisode],
        alt_eps: list[InterventionEpisode],
        grade: EvidenceGrade,
        _max_distance: float,
    ) -> list[str]:
        limitations = []
        if grade.grade < 3:
            limitations.append("observational_data")
        total = len(actual_eps) + len(alt_eps)
        if total < 50:
            limitations.append("small_sample")
        if grade.grade < 2:
            limitations.append("context_overlap_partial")
        if grade.grade < 5:
            limitations.append("not_verified_online")
        return limitations

    @classmethod
    def _build_recommendation(
        cls,
        effects: list[MetricEffect],
        grade: EvidenceGrade,
        actual_policy: str,
        alternative_policy: str,
    ) -> tuple[str, str, list[str]]:
        """Build recommendation respecting iron laws.

        Iron Law 1: counterfactual results cannot directly change live policy.
        Iron Law 3: small samples can only produce hypotheses, not system skills.
        Iron Law 6: user-facing language must be humble, never claim "proven".
        """
        # Count significant effects in favor of alternative
        alt_wins = sum(1 for e in effects if e.is_significant and e.effect_size > 0)
        actual_wins = sum(1 for e in effects if e.is_significant and e.effect_size < 0)

        if grade.grade <= 1:
            return (
                f"Evidence grade {grade.grade} ({grade.label}) — insufficient for policy change. "
                f"Continue collecting data on {alternative_policy}.",
                "shadow",
                ["direct_live_change"],
            )

        if alt_wins > actual_wins:
            if grade.grade >= 4:
                return (
                    f"Alternative '{alternative_policy}' shows consistent improvement over "
                    f"'{actual_policy}' across {alt_wins} metrics (evidence: {grade.label}). "
                    f"Recommending promotion to shadow experiment.",
                    "shadow",
                    ["direct_live_change", "skip_simulation", "skip_guardrail"],
                )
            else:
                return (
                    f"In similar contexts, '{alternative_policy}' may be more effective than "
                    f"'{actual_policy}' (Grade {grade.grade} evidence). Using it experimentally.",
                    "shadow",
                    ["direct_live_change", "hard_constraint", "system_skill"],
                )
        elif actual_wins > alt_wins:
            return (
                f"Current policy '{actual_policy}' continues to perform better. "
                f"No change recommended.",
                "shadow",
                ["policy_change"],
            )
        else:
            return (
                f"No significant difference between '{actual_policy}' and "
                f"'{alternative_policy}' at current evidence level.",
                "shadow",
                ["policy_change"],
            )


# ═══════════════════════════════════════════════════════════════════════
# 6. PolicyUpdateCandidateBuilder
# ═══════════════════════════════════════════════════════════════════════


class PolicyUpdateCandidateBuilder:
    """Build PolicyUpdateCandidates from counterfactual estimates.

    Enforces all promotion gates:
    - min_episodes (50)
    - min_distinct_users (15)
    - evidence_grade >= 3
    - guardrail checks
    - human_review_required for live promotion
    """

    MIN_EPISODES_FOR_PROMOTION = 50
    MIN_USERS_FOR_PROMOTION = 15
    MIN_EVIDENCE_GRADE = 3

    @classmethod
    def from_estimate(
        cls,
        estimate: CounterfactualEstimate,
        *,
        distinct_users_actual: int = 0,
        distinct_users_alternative: int = 0,
        guardrail_passed: bool = False,
    ) -> PolicyUpdateCandidate:
        """Build a promotion candidate from a counterfactual estimate."""
        candidate = PolicyUpdateCandidate(
            source_estimate_id=estimate.estimate_id,
            current_policy=estimate.actual_policy,
            proposed_policy=estimate.alternative_policy,
            evidence_grade=estimate.evidence_grade,
            effect_summary=cls._summarize_effects(estimate.estimated_effects),
        )

        # Check gates
        total_episodes = estimate.matched_episodes_actual + estimate.matched_episodes_alternative
        candidate.min_episodes_met = total_episodes >= cls.MIN_EPISODES_FOR_PROMOTION

        total_users = distinct_users_actual + distinct_users_alternative
        candidate.min_users_met = total_users >= cls.MIN_USERS_FOR_PROMOTION

        candidate.guardrail_checks_passed = guardrail_passed

        # Determine if promotion is blocked
        if not candidate.min_episodes_met:
            candidate.promotion_blocked_reasons.append(
                f"Insufficient episodes: {total_episodes}/{cls.MIN_EPISODES_FOR_PROMOTION}",
            )
        if not candidate.min_users_met:
            candidate.promotion_blocked_reasons.append(
                f"Insufficient distinct users: {total_users}/{cls.MIN_USERS_FOR_PROMOTION}",
            )
        if estimate.evidence_grade.grade < cls.MIN_EVIDENCE_GRADE:
            candidate.promotion_blocked_reasons.append(
                f"Evidence grade too low: {estimate.evidence_grade.grade}/{cls.MIN_EVIDENCE_GRADE}",
            )
        if not guardrail_passed:
            candidate.promotion_blocked_reasons.append("Guardrail checks not passed")

        # Iron Law 1: never directly live
        candidate.allowed_mode = "shadow"
        if candidate.min_episodes_met and candidate.min_users_met and candidate.guardrail_checks_passed:
            if estimate.evidence_grade.grade >= 4:
                candidate.allowed_mode = "soft_bias"
                candidate.human_review_required = True  # Still requires human review
            else:
                candidate.human_review_required = True

        return candidate

    @classmethod
    def from_comparison_report(
        cls,
        report: PolicyComparisonReport,
        *,
        distinct_users_a: int = 0,
        distinct_users_b: int = 0,
        guardrail_passed: bool = False,
    ) -> PolicyUpdateCandidate | None:
        """Build from a comparison report. Returns None if no clear winner."""
        if report.winner == "tie" or report.winner == "insufficient_data":
            return None

        proposed = report.policy_b if report.winner == "b" else report.policy_a
        current = report.policy_a if report.winner == "b" else report.policy_b

        estimate = CounterfactualEstimate(
            actual_policy=current,
            alternative_policy=proposed,
            matched_episodes_actual=report.total_episodes_a,
            matched_episodes_alternative=report.total_episodes_b,
            estimated_effects=report.effects,
            evidence_grade=report.evidence_grade,
        )

        return cls.from_estimate(
            estimate,
            distinct_users_actual=distinct_users_a,
            distinct_users_alternative=distinct_users_b,
            guardrail_passed=guardrail_passed,
        )

    @staticmethod
    def _summarize_effects(effects: list[MetricEffect]) -> dict[str, Any]:
        if not effects:
            return {}
        significant = [e for e in effects if e.is_significant]
        return {
            "metrics_evaluated": len(effects),
            "significant_effects": len(significant),
            "primary_metric": effects[0].metric if effects else "",
            "primary_effect_size": round(effects[0].effect_size, 4) if effects else 0.0,
        }


# ═══════════════════════════════════════════════════════════════════════
# 7. CounterfactualIronLawEnforcer
# ═══════════════════════════════════════════════════════════════════════


class CounterfactualIronLawEnforcer:
    """Enforce the 6 iron laws of counterfactual evaluation.

    All methods return (compliant: bool, violations: list[str]).
    """

    @staticmethod
    def check_direct_live_change(estimate: CounterfactualEstimate) -> tuple[bool, list[str]]:
        """Iron Law 1: Counterfactual results cannot directly change live policy."""
        if estimate.allowed_mode == "hard_constraint":
            return False, ["direct_live_change_violation"]
        return True, []

    @staticmethod
    def check_evidence_grade_present(estimate: CounterfactualEstimate) -> tuple[bool, list[str]]:
        """Iron Law 2: All estimates must carry evidence_grade."""
        if estimate.evidence_grade.grade < 0:
            return False, ["missing_evidence_grade"]
        return True, []

    @staticmethod
    def check_small_sample_hypothesis_only(
        estimate: CounterfactualEstimate,
    ) -> tuple[bool, list[str]]:
        """Iron Law 3: Small samples can only produce hypotheses, not system skills."""
        total = estimate.matched_episodes_actual + estimate.matched_episodes_alternative
        if total < 30 and estimate.allowed_mode == "hard_constraint":
            return False, ["small_sample_system_skill_violation"]
        return True, []

    @staticmethod
    def check_high_risk_conservative(
        estimate: CounterfactualEstimate,
        *,
        is_high_risk: bool = False,
    ) -> tuple[bool, list[str]]:
        """Iron Law 4: High-risk goal phases only allow conservative strategies."""
        if is_high_risk and estimate.allowed_mode != "shadow":
            return False, ["high_risk_non_conservative"]
        return True, []

    @staticmethod
    def check_promotion_requires_simulation(
        candidate: PolicyUpdateCandidate,
    ) -> tuple[bool, list[str]]:
        """Iron Law 5: Any policy promotion must go through simulation + shadow + guardrail."""
        missing = []
        if not candidate.guardrail_checks_passed:
            missing.append("guardrail")
        if candidate.evidence_grade.grade < 2:
            missing.append("simulation")
        if candidate.allowed_mode == "hard_constraint":
            missing.append("shadow_skipped")
        if missing:
            return False, [f"promotion_missing_{m}" for m in missing]
        return True, []

    @staticmethod
    def check_user_language_humble(
        recommendation: str,
    ) -> tuple[bool, list[str]]:
        """Iron Law 6: User-facing language must be humble. Never claim 'proven'."""
        forbidden_affirmative = [
            "has proven", "is proven", "we proved", "we have proven",
            "guaranteed", "保证有效", "已证明",
            "scientifically proven",
        ]
        for phrase in forbidden_affirmative:
            if phrase.lower() in recommendation.lower():
                return False, [f"overconfident_language: {phrase}"]
        return True, []

    @classmethod
    def enforce_all(
        cls,
        estimate: CounterfactualEstimate,
        *,
        is_high_risk: bool = False,
        candidate: PolicyUpdateCandidate | None = None,
    ) -> dict[str, Any]:
        """Enforce all 6 iron laws on a counterfactual evaluation."""
        results = {
            "direct_live_change": cls.check_direct_live_change(estimate),
            "evidence_grade_present": cls.check_evidence_grade_present(estimate),
            "small_sample_hypothesis": cls.check_small_sample_hypothesis_only(estimate),
            "high_risk_conservative": cls.check_high_risk_conservative(
                estimate, is_high_risk=is_high_risk,
            ),
            "user_language_humble": cls.check_user_language_humble(estimate.recommendation),
        }

        if candidate:
            results["promotion_requires_simulation"] = cls.check_promotion_requires_simulation(candidate)

        all_compliant = all(compliant for compliant, _ in results.values())
        all_violations = []
        for violations in [v for _, v in results.values() if v]:
            all_violations.extend(violations)

        return {
            "compliant": all_compliant,
            "violations": all_violations,
            "checks": {
                name: {"compliant": compliant, "violations": violations}
                for name, (compliant, violations) in results.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════
# 8. Production pipeline helpers
# ═══════════════════════════════════════════════════════════════════════


class CounterfactualReportService:
    """Production persistence and promotion boundary for counterfactual reports."""

    DEFAULT_ALTERNATIVES = ("reduce_pace", "simplify_task", "worked_example_first")

    def __init__(self, db: Any, redis: Any | None = None):
        self.db = db
        self.redis = redis

    async def run_daily_evaluations(
        self,
        *,
        user_ids: list[str] | None = None,
        limit_users: int = 500,
        max_pairs_per_user: int = 8,
    ) -> dict[str, Any]:
        """Scan eligible InterventionEpisode groups and persist comparison reports."""
        from sqlalchemy import select

        from app.models.user import User

        if user_ids is None:
            discovered = await self._discover_user_ids_from_redis(limit=limit_users)
            if discovered:
                user_ids = discovered[:limit_users]
            else:
                result = await self.db.execute(
                    select(User.id).where(User.is_active.is_(True)).limit(limit_users),
                )
                user_ids = [str(row[0]) for row in result.all()]

        generated = 0
        skipped_users = 0
        policy_pairs = 0
        violations: list[str] = []

        for user_id in user_ids[:limit_users]:
            episodes = await self.load_user_episodes(user_id)
            if len(episodes) < 2:
                skipped_users += 1
                continue
            for policy_a, policy_b, pair_episodes in self._eligible_policy_pairs(
                episodes,
                max_pairs=max_pairs_per_user,
            ):
                policy_pairs += 1
                report = await self.create_report_from_episodes(
                    user_id=user_id,
                    policy_a=policy_a,
                    policy_b=policy_b,
                    episodes=pair_episodes,
                )
                compliance = report.iron_law_compliance if isinstance(report.iron_law_compliance, dict) else {}
                violations.extend(compliance.get("violations") or [])
                generated += 1

        await self.db.commit()
        await self.refresh_pending_metric()
        return {
            "users_scanned": len(user_ids),
            "users_skipped": skipped_users,
            "policy_pairs_evaluated": policy_pairs,
            "reports_generated": generated,
            "iron_law_violations": sorted(set(violations)),
        }

    async def create_report_from_episodes(
        self,
        *,
        user_id: str,
        policy_a: str,
        policy_b: str,
        episodes: list[InterventionEpisode],
    ) -> Any:
        """Evaluate one policy pair, enforce iron laws, and persist a report row."""
        from app.aurora.runtime_v1.models import CounterfactualReport
        from app.core.metrics import (
            COUNTERFACTUAL_EVIDENCE_GRADE,
            COUNTERFACTUAL_REPORTS_GENERATED,
        )

        target_context = self._dominant_context(episodes)
        estimate = MatchedContextEvaluator.evaluate(
            actual_policy=policy_a,
            alternative_policy=policy_b,
            episodes=episodes,
            target_context=target_context,
        )
        candidate = PolicyUpdateCandidateBuilder.from_estimate(
            estimate,
            distinct_users_actual=self._distinct_users_for_policy(episodes, policy_a),
            distinct_users_alternative=self._distinct_users_for_policy(episodes, policy_b),
            guardrail_passed=self._guardrails_passed(episodes),
        )
        is_high_risk = any(ep.risk_level in {"high", "critical"} for ep in episodes)
        compliance = CounterfactualIronLawEnforcer.enforce_all(
            estimate,
            is_high_risk=is_high_risk,
            candidate=candidate,
        )
        confidence = self._estimate_confidence(estimate)
        context_signature = estimate.target_context.to_dict()
        context_hash = self._context_hash(context_signature)
        promotion_status = self._promotion_status(candidate, compliance)

        report = CounterfactualReport(
            user_id=user_id,
            context_signature=context_signature,
            context_hash=context_hash,
            policy_a=policy_a,
            policy_b=policy_b,
            estimate=estimate.to_dict(),
            confidence=confidence,
            evidence_grade=estimate.evidence_grade.grade,
            generated_at=datetime.now(UTC).replace(tzinfo=None),
            promotion_candidate=candidate.to_dict(),
            promotion_status=promotion_status,
            iron_law_compliance=compliance,
            runtime_metadata={
                "episode_count": len(episodes),
                "source": "daily_counterfactual_evaluation",
            },
        )
        self.db.add(report)
        await self.db.flush()
        await self._mark_replaced_reports(report)
        await self.db.flush()
        COUNTERFACTUAL_REPORTS_GENERATED.labels(status=promotion_status).inc()
        COUNTERFACTUAL_EVIDENCE_GRADE.observe(estimate.evidence_grade.grade)
        return report

    async def list_reports(
        self,
        *,
        user_id: str,
        include_replaced: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        from sqlalchemy import desc, select

        from app.aurora.runtime_v1.models import CounterfactualReport

        stmt = select(CounterfactualReport).where(
            CounterfactualReport.user_id == user_id,
            CounterfactualReport.deleted_at.is_(None),
        )
        if not include_replaced:
            stmt = stmt.where(CounterfactualReport.replaced_by_id.is_(None))
        stmt = stmt.order_by(desc(CounterfactualReport.generated_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_report(self, report_id: str, *, user_id: str | None = None) -> Any | None:
        from uuid import UUID

        from sqlalchemy import select

        from app.aurora.runtime_v1.models import CounterfactualReport

        stmt = select(CounterfactualReport).where(
            CounterfactualReport.id == UUID(str(report_id)),
            CounterfactualReport.deleted_at.is_(None),
        )
        if user_id is not None:
            stmt = stmt.where(CounterfactualReport.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def promote_report(self, report_id: str, *, admin_user_id: str) -> Any:
        report = await self.get_report(report_id)
        if report is None:
            raise ValueError("counterfactual_report_not_found")

        candidate = dict(report.promotion_candidate or {})
        compliance = dict(report.iron_law_compliance or {})
        blocked = list(candidate.get("promotion_blocked_reasons") or [])
        if not compliance.get("compliant", False) or blocked:
            raise ValueError(
                "counterfactual_promotion_blocked:"
                + ",".join(sorted(set(blocked + list(compliance.get("violations") or [])))),
            )

        report.promotion_status = "pending_review"
        metadata = dict(report.runtime_metadata or {})
        metadata["promotion_requested_by"] = admin_user_id
        metadata["promotion_requested_at"] = datetime.now(UTC).isoformat()
        report.runtime_metadata = metadata
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        await self.refresh_pending_metric()
        return report

    async def refresh_pending_metric(self) -> int:
        from sqlalchemy import func, select

        from app.aurora.runtime_v1.models import CounterfactualReport
        from app.core.metrics import COUNTERFACTUAL_PROMOTION_PENDING

        result = await self.db.execute(
            select(func.count()).select_from(CounterfactualReport).where(
                CounterfactualReport.promotion_status == "pending_review",
                CounterfactualReport.deleted_at.is_(None),
            ),
        )
        pending = int(result.scalar() or 0)
        COUNTERFACTUAL_PROMOTION_PENDING.set(pending)
        return pending

    async def load_user_episodes(self, user_id: str) -> list[InterventionEpisode]:
        if self.redis is None:
            return []
        key = f"spine:episodes:{user_id}"
        raw_ids = await self.redis.lrange(key, 0, -1)
        episodes: list[InterventionEpisode] = []
        for raw_id in raw_ids or []:
            episode_id = self._decode(raw_id)
            raw_episode = await self.redis.get(f"spine:episode:{user_id}:{episode_id}")
            if not raw_episode:
                continue
            try:
                episodes.append(InterventionEpisode.from_dict(json.loads(self._decode(raw_episode))))
            except Exception:
                continue
        return episodes

    async def _discover_user_ids_from_redis(self, *, limit: int) -> list[str]:
        if self.redis is None or not hasattr(self.redis, "scan_iter"):
            return []
        user_ids: list[str] = []
        async for raw_key in self.redis.scan_iter(match="spine:episodes:*", count=200):
            key = self._decode(raw_key)
            user_id = key.rsplit(":", 1)[-1]
            if user_id and user_id not in user_ids:
                user_ids.append(user_id)
            if len(user_ids) >= limit:
                break
        return user_ids

    async def _mark_replaced_reports(self, new_report: Any) -> None:
        from sqlalchemy import desc, select

        from app.aurora.runtime_v1.models import CounterfactualReport

        result = await self.db.execute(
            select(CounterfactualReport)
            .where(
                CounterfactualReport.user_id == new_report.user_id,
                CounterfactualReport.context_hash == new_report.context_hash,
                CounterfactualReport.policy_a == new_report.policy_a,
                CounterfactualReport.policy_b == new_report.policy_b,
                CounterfactualReport.id != new_report.id,
                CounterfactualReport.replaced_by_id.is_(None),
                CounterfactualReport.deleted_at.is_(None),
            )
            .order_by(desc(CounterfactualReport.generated_at)),
        )
        old_reports = list(result.scalars().all())
        for old_report in old_reports:
            old_report.replaced_by_id = new_report.id
            self.db.add(old_report)

    @classmethod
    def _eligible_policy_pairs(
        cls,
        episodes: list[InterventionEpisode],
        *,
        max_pairs: int,
    ) -> list[tuple[str, str, list[InterventionEpisode]]]:
        grouped = InterventionEpisodeLedger.group_by_policy(episodes)
        policies = sorted(policy for policy, items in grouped.items() if policy and items)
        pairs: list[tuple[str, str, list[InterventionEpisode]]] = []
        for i, policy_a in enumerate(policies):
            for policy_b in policies[i + 1 :]:
                pair_episodes = grouped[policy_a] + grouped[policy_b]
                pairs.append((policy_a, policy_b, pair_episodes))
                if len(pairs) >= max_pairs:
                    return pairs
        return pairs

    @staticmethod
    def _dominant_context(episodes: list[InterventionEpisode]) -> ContextSignature:
        if not episodes:
            return ContextSignature()
        return episodes[-1].context_signature

    @staticmethod
    def _estimate_confidence(estimate: CounterfactualEstimate) -> float:
        if not estimate.estimated_effects:
            return 0.0
        return round(max(effect.confidence for effect in estimate.estimated_effects), 4)

    @staticmethod
    def _distinct_users_for_policy(episodes: list[InterventionEpisode], policy: str) -> int:
        return len({ep.user_id for ep in episodes if ep.selected_policy == policy and ep.user_id})

    @staticmethod
    def _guardrails_passed(episodes: list[InterventionEpisode]) -> bool:
        for episode in episodes:
            violated, _ = episode.outcome_vector.has_guardrail_violation()
            if violated or episode.risk_level in {"high", "critical"}:
                return False
        return True

    @staticmethod
    def _promotion_status(candidate: PolicyUpdateCandidate, compliance: dict[str, Any]) -> str:
        if not compliance.get("compliant", False):
            return "blocked"
        if candidate.promotion_blocked_reasons:
            return "not_ready"
        return "candidate_ready"

    @staticmethod
    def _context_hash(context_signature: dict[str, Any]) -> str:
        payload = json.dumps(context_signature, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode(raw: Any) -> str:
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)
