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
        num_effects: int,
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
        max_distance: float,
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
