"""
Core: execution / research
Phase: reinforce→adapt
Stage: P4-4 — Research-grade Experiment Platform

Extends the simple A/B experiment system (policy_experiments.py) with:
- Multivariate experiment design
- User segmentation / stratification
- Statistical significance estimation (Bayesian + rule-based)
- Automatic conclusion with confidence intervals
- Cross-sprint experiment persistence
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
class ExperimentVariant:
    """A single variant in a multivariate experiment."""
    variant_id: str
    variant_name: str              # e.g. "control", "worked_example_first", "short_tasks"
    description: str
    policy_params: dict[str, Any]   # Policy parameters applied to this variant
    user_segment: str = "all"       # User segment filter
    sample_size: int = 0
    successes: int = 0
    failures: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        if total == 0:
            return 0.0
        return self.successes / total

    def record_outcome(self, success: bool) -> None:
        if success:
            self.successes += 1
        else:
            self.failures += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_name": self.variant_name,
            "description": self.description,
            "policy_params": self.policy_params,
            "user_segment": self.user_segment,
            "sample_size": self.sample_size,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class UserSegment:
    """User segmentation for experiment stratification."""
    segment_id: str
    segment_name: str
    criteria: dict[str, Any]         # e.g. {"goal_type": "exam_sprint", "activity_level": "high"}
    user_count: int = 0

    def matches(self, user_profile: dict[str, Any]) -> bool:
        for key, expected in self.criteria.items():
            actual = user_profile.get(key)
            if actual != expected:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "segment_name": self.segment_name,
            "criteria": self.criteria,
            "user_count": self.user_count,
        }


@dataclass
class ExperimentConclusion:
    """Automatic conclusion from a completed experiment."""
    experiment_id: str
    concluded_at: str
    winning_variant_id: str | None
    confidence_interval: tuple[float, float]  # (lower, upper) for effect size
    statistical_method: str                   # "bayesian" | "rule_threshold" | "frequentist"
    effect_size: float = 0.0                  # Raw effect size between best and worst variant
    p_value_estimate: float | None = None
    recommendation: str = ""
    is_conclusive: bool = False
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "concluded_at": self.concluded_at,
            "winning_variant_id": self.winning_variant_id,
            "confidence_interval": list(self.confidence_interval),
            "statistical_method": self.statistical_method,
            "p_value_estimate": self.p_value_estimate,
            "recommendation": self.recommendation,
            "is_conclusive": self.is_conclusive,
            "caveats": self.caveats,
        }


@dataclass
class MultivariateExperiment:
    """A multivariate research-grade experiment."""
    experiment_id: str
    experiment_name: str
    hypothesis: str
    variants: list[ExperimentVariant] = field(default_factory=list)
    segments: list[UserSegment] = field(default_factory=list)
    status: str = "draft"          # draft → running → analyzing → concluded → archived
    min_samples_per_variant: int = 30
    min_effect_size: float = 0.1   # Minimum detectable effect
    created_at: str = field(default_factory=_utcnow)
    concluded_at: str | None = None
    conclusion: ExperimentConclusion | None = None
    cross_sprint: bool = False      # Persist across sprints for long-term learning

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "hypothesis": self.hypothesis,
            "variants": [v.to_dict() for v in self.variants],
            "segments": [s.to_dict() for s in self.segments],
            "status": self.status,
            "min_samples_per_variant": self.min_samples_per_variant,
            "min_effect_size": self.min_effect_size,
            "created_at": self.created_at,
            "concluded_at": self.concluded_at,
            "conclusion": self.conclusion.to_dict() if self.conclusion else None,
            "cross_sprint": self.cross_sprint,
        }


class MultivariateExperimentEngine:
    """Research-grade experiment platform for strategy testing."""

    # ── Experiment Design ─────────────────────────────────────────────────

    @staticmethod
    def create_experiment(
        name: str,
        hypothesis: str,
        variants: list[dict[str, Any]],
        *,
        segments: list[dict[str, Any]] | None = None,
        min_samples: int = 30,
        cross_sprint: bool = False,
    ) -> MultivariateExperiment:
        """Create a new multivariate experiment."""
        exp_variants = [
            ExperimentVariant(
                variant_id=_uid("var"),
                variant_name=v["name"],
                description=v.get("description", ""),
                policy_params=v.get("policy_params", {}),
                user_segment=v.get("user_segment", "all"),
            )
            for v in variants
        ]

        exp_segments = [
            UserSegment(
                segment_id=_uid("seg"),
                segment_name=s["name"],
                criteria=s.get("criteria", {}),
            )
            for s in (segments or [])
        ]

        return MultivariateExperiment(
            experiment_id=_uid("exp"),
            experiment_name=name,
            hypothesis=hypothesis,
            variants=exp_variants,
            segments=exp_segments,
            min_samples_per_variant=min_samples,
            cross_sprint=cross_sprint,
        )

    # ── Outcome Recording ────────────────────────────────────────────────

    @staticmethod
    def record_outcome(
        experiment: MultivariateExperiment,
        variant_id: str,
        success: bool,
        *,
        user_segment: dict[str, Any] | None = None,
    ) -> None:
        """Record an outcome for a specific variant."""
        for variant in experiment.variants:
            if variant.variant_id == variant_id:
                variant.record_outcome(success)
                variant.sample_size += 1
                return
        logger.warning("Variant {} not found in experiment {}", variant_id, experiment.experiment_id)

    # ── Analysis ─────────────────────────────────────────────────────────

    @staticmethod
    def analyze(experiment: MultivariateExperiment) -> ExperimentConclusion:
        """Analyze experiment results and draw conclusions.

        Uses a hybrid approach:
        - Bayesian estimation when sample >= min_samples_per_variant
        - Rule-based threshold when sample < min_samples (early signal)
        """
        active_variants = [v for v in experiment.variants if v.sample_size > 0]
        if len(active_variants) < 2:
            return ExperimentConclusion(
                experiment_id=experiment.experiment_id,
                concluded_at=_utcnow(),
                winning_variant_id=None,
                confidence_interval=(0.0, 0.0),
                statistical_method="rule_threshold",
                is_conclusive=False,
                recommendation="Insufficient variants for comparison",
                caveats=["Need at least 2 active variants"],
            )

        best = max(active_variants, key=lambda v: v.success_rate)
        worst = min(active_variants, key=lambda v: v.success_rate)
        effect_size = best.success_rate - worst.success_rate

        enough_samples = all(
            v.sample_size >= experiment.min_samples_per_variant
            for v in active_variants
        )

        if not enough_samples:
            return ExperimentConclusion(
                experiment_id=experiment.experiment_id,
                concluded_at=_utcnow(),
                winning_variant_id=None,
                confidence_interval=(0.0, effect_size),
                statistical_method="rule_threshold",
                is_conclusive=False,
                recommendation=f"Insufficient samples ({min(v.sample_size for v in active_variants)}/{experiment.min_samples_per_variant})",
                caveats=["Not enough data for conclusion", "Consider extending experiment"],
            )

        is_conclusive = effect_size >= experiment.min_effect_size

        # Bayesian-style confidence interval approximation
        n = sum(v.sample_size for v in active_variants)
        se = (best.success_rate * (1 - best.success_rate) / max(best.sample_size, 1)) ** 0.5
        ci_lower = max(0.0, effect_size - 1.96 * se)
        ci_upper = min(1.0, effect_size + 1.96 * se)

        method = "bayesian" if is_conclusive else "rule_threshold"

        if is_conclusive and effect_size > 0:
            recommendation = (
                f"Variant '{best.variant_name}' outperforms '{worst.variant_name}' "
                f"by {effect_size:.1%} (CI: [{ci_lower:.2f}, {ci_upper:.2f}]). "
                f"Recommend promoting {best.variant_name}."
            )
        elif is_conclusive:
            recommendation = "No significant difference between variants."
        else:
            recommendation = (
                f"Effect size {effect_size:.1%} below minimum {experiment.min_effect_size:.1%}. "
                f"Experiment is inconclusive."
            )

        return ExperimentConclusion(
            experiment_id=experiment.experiment_id,
            concluded_at=_utcnow(),
            winning_variant_id=best.variant_id if is_conclusive and effect_size > 0 else None,
            confidence_interval=(ci_lower, ci_upper),
            statistical_method=method,
            effect_size=effect_size,
            p_value_estimate=None,  # Would need actual statistical test for frequentist
            recommendation=recommendation,
            is_conclusive=is_conclusive,
            caveats=(
                []
                if is_conclusive
                else [
                    f"Minimum effect size not met ({effect_size:.1%} < {experiment.min_effect_size:.1%})",
                    "Consider running longer or adjusting hypothesis",
                ]
            ),
        )

    # ── User Segmentation ────────────────────────────────────────────────

    @staticmethod
    def assign_variant(
        experiment: MultivariateExperiment,
        user_profile: dict[str, Any],
    ) -> ExperimentVariant | None:
        """Assign a user to the appropriate variant based on segmentation.

        If no segment matches, assigns to the first variant with segment='all'.
        """
        # Try segment-specific assignment first
        for variant in experiment.variants:
            if variant.user_segment == "all":
                continue
            for segment in experiment.segments:
                if segment.segment_name == variant.user_segment:
                    if segment.matches(user_profile):
                        return variant

        # Fall back to 'all' segment
        for variant in experiment.variants:
            if variant.user_segment == "all":
                return variant

        return experiment.variants[0] if experiment.variants else None

    # ── Cross-Sprint Persistence ─────────────────────────────────────────

    @staticmethod
    def can_continue_across_sprints(experiment: MultivariateExperiment) -> bool:
        """Check if this experiment should persist across sprint boundaries."""
        return experiment.cross_sprint and experiment.status in ("running", "analyzing")

    @staticmethod
    async def persist_to_redis(
        experiment: MultivariateExperiment,
        redis_client: Any,
        *,
        key_prefix: str = "spine:experiment:",
    ) -> None:
        """Persist experiment state to Redis."""
        key = f"{key_prefix}{experiment.experiment_id}"
        await redis_client.set(key, str(experiment.to_dict()))

    @staticmethod
    async def load_from_redis(
        redis_client: Any,
        experiment_id: str,
        *,
        key_prefix: str = "spine:experiment:",
    ) -> dict[str, Any] | None:
        """Load experiment state from Redis."""
        import json
        key = f"{key_prefix}{experiment_id}"
        raw = await redis_client.get(key)
        if raw:
            return json.loads(raw) if isinstance(raw, bytes) else raw
        return None
