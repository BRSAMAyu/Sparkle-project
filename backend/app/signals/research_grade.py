"""
Core: execution
Phase: adapt
Stage: P4 Research-Grade — Counterfactual evaluation + User Simulator + Domain Pack

Three research-grade capabilities:
1. CounterfactualEngine — "what would have happened without intervention?"
2. UserSimulator — synthetic user for strategy testing
3. DomainPackMarketplace — user-contributed domain strategy packs

All pure computation, no external I/O.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from app.signals.types import OutcomeRecord, _uid

# ═══════════════════════════════════════════════════════════════════════
# 1. Counterfactual Engine
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class CounterfactualResult:
    result_id: str
    trace_id: str
    actual_outcome: str        # "effective" | "insufficient"
    counterfactual_outcome: str  # estimated outcome without intervention
    intervention_impact: float  # -1.0 to +1.0 (positive = intervention helped)
    confidence: float           # confidence in the estimate
    reasoning: str
    method: str                 # "baseline_comparison" | "random_baseline" | "rule_based"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "trace_id": self.trace_id,
            "actual_outcome": self.actual_outcome,
            "counterfactual_outcome": self.counterfactual_outcome,
            "intervention_impact": self.intervention_impact,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "method": self.method,
        }


class CounterfactualEngine:
    """Estimate what would have happened without intervention.

    Uses three methods, selected by data availability:
    - baseline_comparison: compare to user's baseline rate
    - random_baseline: use population average
    - rule_based: simple heuristic rules
    """

    # Population average effectiveness (calibrated from aggregate data)
    POPULATION_BASELINE = 0.55

    def evaluate(
        self,
        outcome: OutcomeRecord,
        *,
        user_baseline_rate: float | None = None,
        similar_interventions: list[dict[str, Any]] | None = None,
    ) -> CounterfactualResult:
        """Estimate counterfactual outcome for a single intervention."""
        actual = outcome.attribution

        # Method selection based on data availability
        if user_baseline_rate is not None:
            method = "baseline_comparison"
            cf_outcome, confidence, reasoning = self._baseline_method(
                actual, user_baseline_rate,
            )
        elif similar_interventions and len(similar_interventions) >= 3:
            method = "rule_based"
            cf_outcome, confidence, reasoning = self._rule_based_method(
                actual, similar_interventions,
            )
        else:
            method = "random_baseline"
            cf_outcome, confidence, reasoning = self._random_baseline_method(actual)

        # Compute intervention impact
        impact = self._compute_impact(actual, cf_outcome)

        return CounterfactualResult(
            result_id=_uid("cf"),
            trace_id=outcome.causal_trace_id,
            actual_outcome=actual,
            counterfactual_outcome=cf_outcome,
            intervention_impact=impact,
            confidence=confidence,
            reasoning=reasoning,
            method=method,
        )

    def _baseline_method(
        self,
        actual: str,
        baseline_rate: float,
    ) -> tuple[str, float, str]:
        """Compare to user's own baseline rate."""
        # If baseline is low, counterfactual is likely "insufficient"
        if baseline_rate < 0.4:
            cf = "insufficient"
            confidence = 0.6 + (0.4 - baseline_rate)
        elif baseline_rate > 0.7:
            cf = "effective"
            confidence = 0.5  # hard to tell — user might have done well anyway
        else:
            cf = "effective" if random.random() < baseline_rate else "insufficient"
            confidence = 0.4

        reasoning = f"用户基线成功率 {baseline_rate:.0%}，无干预时估计{'成功' if cf == 'effective' else '不成功'}"
        return cf, min(confidence, 0.9), reasoning

    def _rule_based_method(
        self,
        actual: str,
        similar: list[dict[str, Any]],
    ) -> tuple[str, float, str]:
        """Use similar interventions' no-intervention outcomes."""
        # How often was outcome "insufficient" when similar situations had no intervention?
        no_interv = [s for s in similar if not s.get("had_intervention", False)]
        if not no_interv:
            return self._random_baseline_method(actual)

        insuff_rate = sum(1 for s in no_interv if s.get("outcome") == "insufficient") / len(no_interv)
        cf = "insufficient" if insuff_rate > 0.5 else "effective"
        confidence = min(0.5 + abs(insuff_rate - 0.5), 0.85)

        reasoning = f"相似场景（n={len(no_interv)}）无干预时失败率 {insuff_rate:.0%}"
        return cf, confidence, reasoning

    def _random_baseline_method(
        self,
        actual: str,
    ) -> tuple[str, float, str]:
        """Use population baseline."""
        cf = "effective" if random.random() < self.POPULATION_BASELINE else "insufficient"
        confidence = 0.3  # low confidence — just a baseline guess
        reasoning = f"使用总体基线成功率 {self.POPULATION_BASELINE:.0%} 估计"
        return cf, confidence, reasoning

    @staticmethod
    def _compute_impact(actual: str, counterfactual: str) -> float:
        """Compute intervention impact score."""
        if actual == "effective" and counterfactual == "insufficient":
            return 1.0   # intervention helped
        if actual == "insufficient" and counterfactual == "effective":
            return -1.0  # intervention made things worse
        if actual == counterfactual:
            return 0.0   # no difference
        return 0.0

    def batch_evaluate(
        self,
        outcomes: list[OutcomeRecord],
        *,
        user_baseline_rate: float | None = None,
    ) -> list[CounterfactualResult]:
        """Evaluate counterfactuals for a batch of outcomes."""
        return [
            self.evaluate(o, user_baseline_rate=user_baseline_rate)
            for o in outcomes
        ]

    def aggregate_impact(
        self,
        results: list[CounterfactualResult],
    ) -> dict[str, Any]:
        """Aggregate counterfactual results into summary statistics."""
        if not results:
            return {"total": 0, "avg_impact": 0.0}

        impacts = [r.intervention_impact for r in results]
        avg_impact = sum(impacts) / len(impacts)
        positive = sum(1 for i in impacts if i > 0)
        negative = sum(1 for i in impacts if i < 0)
        neutral = sum(1 for i in impacts if i == 0)

        return {
            "total": len(results),
            "avg_impact": round(avg_impact, 3),
            "positive_interventions": positive,
            "negative_interventions": negative,
            "neutral_interventions": neutral,
            "intervention_helped_rate": round(positive / max(len(results), 1), 3),
        }


# ═══════════════════════════════════════════════════════════════════════
# 2. User Simulator
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SimulatedUserProfile:
    """A synthetic user for testing strategy effectiveness."""
    profile_id: str
    baseline_ability: float      # 0-1
    consistency: float           # 0-1 (how predictable)
    responsiveness: float        # 0-1 (how much interventions help)
    fatigue_rate: float          # 0-1 (how quickly they tire)
    goal_type: str = "exam"
    subject: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "baseline_ability": self.baseline_ability,
            "consistency": self.consistency,
            "responsiveness": self.responsiveness,
            "fatigue_rate": self.fatigue_rate,
            "goal_type": self.goal_type,
            "subject": self.subject,
        }


class UserSimulator:
    """Simulate user responses to test strategy effectiveness."""

    def simulate_outcome(
        self,
        profile: SimulatedUserProfile,
        intervention: str,
        *,
        task_number: int = 1,
        previous_outcomes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Simulate a user's response to an intervention.

        Returns: {"outcome": str, "confidence": float, "factors": dict}
        """
        # Base success rate from ability
        base_rate = profile.baseline_ability

        # Intervention boost
        intervention_boost = profile.responsiveness * 0.3
        effective_rate = base_rate + intervention_boost

        # Fatigue penalty
        fatigue = min(task_number * profile.fatigue_rate * 0.05, 0.3)
        effective_rate -= fatigue

        # Consistency noise
        noise = (1 - profile.consistency) * (random.random() - 0.5) * 0.3
        effective_rate += noise

        # Clamp
        effective_rate = max(0.05, min(0.95, effective_rate))

        outcome = "effective" if random.random() < effective_rate else "insufficient"

        return {
            "outcome": outcome,
            "simulated_success_rate": round(effective_rate, 3),
            "confidence": round(profile.consistency * 0.5 + 0.3, 3),
            "factors": {
                "base_ability": profile.baseline_ability,
                "intervention_boost": round(intervention_boost, 3),
                "fatigue_penalty": round(fatigue, 3),
                "noise": round(noise, 3),
                "task_number": task_number,
            },
        }

    def simulate_intervention_sequence(
        self,
        profile: SimulatedUserProfile,
        interventions: list[str],
        *,
        max_tasks: int = 10,
    ) -> list[dict[str, Any]]:
        """Simulate a sequence of interventions and their outcomes."""
        results = []
        previous: list[str] = []

        for i, intervention in enumerate(interventions[:max_tasks]):
            result = self.simulate_outcome(
                profile, intervention,
                task_number=i + 1,
                previous_outcomes=previous,
            )
            result["intervention"] = intervention
            result["task_number"] = i + 1
            results.append(result)
            previous.append(result["outcome"])

        return results

    def compare_strategies(
        self,
        profile: SimulatedUserProfile,
        strategy_a: list[str],
        strategy_b: list[str],
        *,
        trials: int = 100,
    ) -> dict[str, Any]:
        """Compare two strategies using Monte Carlo simulation."""
        a_wins = 0
        b_wins = 0
        ties = 0

        for _ in range(trials):
            results_a = self.simulate_intervention_sequence(profile, strategy_a)
            results_b = self.simulate_intervention_sequence(profile, strategy_b)

            rate_a = sum(1 for r in results_a if r["outcome"] == "effective") / max(len(results_a), 1)
            rate_b = sum(1 for r in results_b if r["outcome"] == "effective") / max(len(results_b), 1)

            if rate_a > rate_b + 0.05:
                a_wins += 1
            elif rate_b > rate_a + 0.05:
                b_wins += 1
            else:
                ties += 1

        return {
            "trials": trials,
            "strategy_a": strategy_a[0] if strategy_a else "",
            "strategy_b": strategy_b[0] if strategy_b else "",
            "a_wins": a_wins,
            "b_wins": b_wins,
            "ties": ties,
            "a_win_rate": round(a_wins / max(trials, 1), 3),
            "b_win_rate": round(b_wins / max(trials, 1), 3),
            "winner": "a" if a_wins > b_wins else ("b" if b_wins > a_wins else "tie"),
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. Domain Pack Marketplace
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DomainPack:
    pack_id: str
    name: str
    description: str
    goal_type: str            # "exam" | "project" | "job_search" | ...
    domain: str               # "computer_science" | "mathematics" | ...
    author_id: str
    strategy_templates: list[dict[str, Any]]  # reusable strategy patterns
    rating: float = 0.0
    download_count: int = 0
    review_count: int = 0
    status: str = "active"    # "active" | "deprecated" | "under_review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "description": self.description,
            "goal_type": self.goal_type,
            "domain": self.domain,
            "author_id": self.author_id,
            "strategy_templates": self.strategy_templates,
            "rating": self.rating,
            "download_count": self.download_count,
            "review_count": self.review_count,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DomainPack:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class DomainPackMarketplace:
    """Manage user-contributed domain strategy packs."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    @staticmethod
    def validate_pack(pack: DomainPack) -> dict[str, Any]:
        """Validate a domain pack before publishing."""
        issues = []

        if not pack.name or len(pack.name) < 3:
            issues.append("name_too_short")
        if not pack.description or len(pack.description) < 10:
            issues.append("description_too_short")
        if not pack.strategy_templates:
            issues.append("no_strategy_templates")
        else:
            for i, tmpl in enumerate(pack.strategy_templates):
                if not tmpl.get("strategy_key"):
                    issues.append(f"template_{i}_missing_strategy_key")
                if not tmpl.get("applicable_when"):
                    issues.append(f"template_{i}_missing_applicable_when")
        if not pack.author_id:
            issues.append("no_author")
        if pack.rating < 0 or pack.rating > 5:
            issues.append("invalid_rating")

        return {"valid": len(issues) == 0, "issues": issues}

    @staticmethod
    def compute_pack_score(pack: DomainPack) -> float:
        """Compute a marketplace score for ranking.

        Factors: rating (60%) + downloads normalized (20%) + reviews (20%)
        """
        rating_score = min(pack.rating / 5.0, 1.0) * 0.6
        download_score = min(pack.download_count / 100, 1.0) * 0.2
        review_score = min(pack.review_count / 20, 1.0) * 0.2
        return round(rating_score + download_score + review_score, 3)

    def rank_packs(
        self,
        packs: list[DomainPack],
        *,
        goal_type: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Rank packs by marketplace score, optionally filtered."""
        filtered = packs
        if goal_type:
            filtered = [p for p in filtered if p.goal_type == goal_type]
        if domain:
            filtered = [p for p in filtered if p.domain == domain]

        # Only active packs
        filtered = [p for p in filtered if p.status == "active"]

        ranked = sorted(
            filtered,
            key=lambda p: self.compute_pack_score(p),
            reverse=True,
        )

        return [
            {
                "pack_id": p.pack_id,
                "name": p.name,
                "score": self.compute_pack_score(p),
                "rating": p.rating,
                "download_count": p.download_count,
            }
            for p in ranked
        ]
