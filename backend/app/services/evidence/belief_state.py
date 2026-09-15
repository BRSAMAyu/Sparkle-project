from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.evidence.unified_evidence import EvidenceTarget


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


MIN_VARIANCE = 0.01
MAX_VARIANCE = 0.25
DEFAULT_MEAN = 0.5
DEFAULT_VARIANCE = 0.25
NEUTRAL_MEAN = 0.5


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return _utcnow()
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


class BeliefVariable(BaseModel):
    """
    Represents the probabilistic belief of a single latent variable.
    V1: Independent Gaussian distribution defined by mean and variance.

    ``mean`` is the projected value used by routing/UI and is kept in [0, 1].
    ``unbounded_mean`` preserves the internal Gaussian posterior mean before
    projection. Keeping both values prevents the output clamp from silently
    breaking the Gaussian update algebra used by the evidence fusion model.
    """

    target: EvidenceTarget
    mean: float = Field(default=DEFAULT_MEAN, ge=0.0, le=1.0, description="The estimated value (0.0 to 1.0)")
    unbounded_mean: float | None = Field(
        default=None,
        description="Unconstrained Gaussian posterior mean before projection to [0, 1]",
    )
    variance: float = Field(default=DEFAULT_VARIANCE, ge=MIN_VARIANCE, le=MAX_VARIANCE)
    last_updated: datetime = Field(default_factory=_utcnow)
    evidence_count: int = Field(default=0, ge=0)
    source_breakdown: dict[str, int] = Field(default_factory=dict)
    last_evidence_ids: list[str] = Field(default_factory=list)

    @staticmethod
    def _project_mean(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _latent_mean(self) -> float:
        return float(self.unbounded_mean if self.unbounded_mean is not None else self.mean)

    @property
    def projection_applied(self) -> bool:
        """Whether the public mean differs from the internal Gaussian mean."""
        return abs(self._latent_mean() - self.mean) > 1e-6

    @property
    def confidence(self) -> float:
        """Belief confidence implied by uncertainty, separate from extractor confidence."""
        return round(max(0.0, min(1.0, 1.0 - (self.variance / MAX_VARIANCE))), 4)

    def apply_temporal_decay(
        self,
        *,
        now: datetime | None = None,
        mean_anchor: float = NEUTRAL_MEAN,
        uncertainty_half_life_hours: float = 12.0,
        mean_reversion_strength: float = 0.35,
    ) -> None:
        """
        Let stale short-term beliefs become less certain and gently drift toward neutral.

        V1 deliberately decays to a neutral state because we have not introduced a
        separate Regime/Trait prior yet. Later versions can replace mean_anchor with
        a user-specific medium/long-term prior.
        """
        observed_at = _normalize_datetime(now)
        previous = _normalize_datetime(self.last_updated)
        elapsed_hours = max(0.0, (observed_at - previous).total_seconds() / 3600.0)
        if elapsed_hours <= 0.0:
            return

        decay_fraction = 1.0 - 0.5 ** (elapsed_hours / max(0.1, uncertainty_half_life_hours))
        self.variance = min(MAX_VARIANCE, self.variance + (MAX_VARIANCE - self.variance) * decay_fraction)

        bounded_anchor = self._project_mean(mean_anchor)
        latent_mean = self._latent_mean()
        self.unbounded_mean = latent_mean + (bounded_anchor - latent_mean) * decay_fraction * mean_reversion_strength
        self.mean = self._project_mean(self.unbounded_mean)
        self.last_updated = observed_at

    def update_from_evidence(
        self,
        *,
        observed_mean: float,
        confidence: float,
        min_observation_variance: float = MIN_VARIANCE,
        observed_at: datetime | None = None,
        evidence_id: str | None = None,
        source_type: str | None = None,
    ) -> None:
        """
        Applies a Bayesian update (Kalman-like 1D update) based on new evidence.
        Confidence is mapped to observation precision (1/variance).
        """
        observed_at = _normalize_datetime(observed_at)
        self.apply_temporal_decay(now=observed_at)

        # Map confidence [0, 1] to observation variance.
        # High confidence -> Low variance. Low confidence -> High variance.
        # Avoid division by zero by clamping confidence.
        clamped_conf = max(0.01, min(0.99, float(confidence)))
        variance_floor = max(MIN_VARIANCE, min(MAX_VARIANCE, float(min_observation_variance)))
        obs_variance = max(variance_floor, min(MAX_VARIANCE, (1.0 - clamped_conf) ** 2))
        prior_variance = max(MIN_VARIANCE, min(MAX_VARIANCE, self.variance))

        # Calculate Kalman Gain
        total_variance = prior_variance + obs_variance
        kalman_gain = prior_variance / total_variance if total_variance > 0 else 0.0

        # Update the internal Gaussian mean first, then project only for
        # downstream routing/UI surfaces. This keeps the mathematical belief
        # update self-consistent even when a posterior temporarily crosses
        # the natural [0, 1] application range.
        bounded_observation = self._project_mean(observed_mean)
        prior_mean = self._latent_mean()
        self.unbounded_mean = prior_mean + kalman_gain * (bounded_observation - prior_mean)
        self.mean = self._project_mean(self.unbounded_mean)

        # Update Variance
        self.variance = max(MIN_VARIANCE, min(MAX_VARIANCE, (1.0 - kalman_gain) * prior_variance))
        self.last_updated = observed_at
        self.evidence_count += 1
        if source_type:
            self.source_breakdown[source_type] = self.source_breakdown.get(source_type, 0) + 1
        if evidence_id:
            self.last_evidence_ids = [evidence_id, *self.last_evidence_ids[:9]]


class BeliefState(BaseModel):
    """
    The unified probabilistic state of the user, derived from multi-source evidence.
    This serves as the input to the Contextual Bandit and RL policies.
    """

    state_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    variables: dict[str, BeliefVariable] = Field(default_factory=dict)
    last_fused_at: datetime = Field(default_factory=_utcnow)
    scope_metadata: dict[str, Any] = Field(default_factory=dict)

    # Track the raw RL-ready state vector for serialization
    def to_rl_vector(self) -> dict[str, float]:
        """Flattens the belief state into a numerical vector suitable for ML models."""
        vec: dict[str, float] = {}
        for key, belief in sorted(self.variables.items()):
            vec[f"{key}_mean"] = round(belief.mean, 4)
            vec[f"{key}_variance"] = round(belief.variance, 4)
            vec[f"{key}_belief_confidence"] = belief.confidence
        return vec

    def uncertainty_vector(self) -> dict[str, float]:
        """Return only uncertainty terms for observability and active elicitation."""
        return {key: round(value.variance, 4) for key, value in sorted(self.variables.items())}

    def get_variable(self, target: EvidenceTarget) -> BeliefVariable:
        key = target.value
        if key not in self.variables:
            # Initialize with maximum uncertainty (mean 0.5, variance 0.25)
            self.variables[key] = BeliefVariable(
                target=target,
                mean=DEFAULT_MEAN,
                unbounded_mean=DEFAULT_MEAN,
                variance=DEFAULT_VARIANCE,
            )
        return self.variables[key]

    def peek_variable(self, target: EvidenceTarget) -> BeliefVariable | None:
        return self.variables.get(target.value)

    def apply_temporal_decay(self, *, now: datetime | None = None) -> None:
        observed_at = _normalize_datetime(now)
        for variable in self.variables.values():
            variable.apply_temporal_decay(now=observed_at)
        self.last_fused_at = observed_at

    def projection_diagnostics(self) -> dict[str, Any]:
        projected_targets = {
            key: {
                "projected_mean": round(variable.mean, 4),
                "unbounded_mean": round(variable._latent_mean(), 4),
            }
            for key, variable in sorted(self.variables.items())
            if variable.projection_applied
        }
        return {
            "schema_version": "belief_projection_diagnostics.v1",
            "projected_target_count": len(projected_targets),
            "projected_targets": projected_targets,
        }

    def to_shadow_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "belief_state.v1",
            "state_id": self.state_id,
            "user_id": self.user_id,
            "last_fused_at": self.last_fused_at.isoformat(),
            "state_vector": self.to_rl_vector(),
            "uncertainty_vector": self.uncertainty_vector(),
            "variables": {
                key: {
                    "target": value.target.value,
                    "mean": round(value.mean, 4),
                    "unbounded_mean": round(value._latent_mean(), 4),
                    "projection_applied": value.projection_applied,
                    "variance": round(value.variance, 4),
                    "belief_confidence": value.confidence,
                    "last_updated": value.last_updated.isoformat(),
                    "evidence_count": value.evidence_count,
                    "source_breakdown": dict(value.source_breakdown),
                    "last_evidence_ids": list(value.last_evidence_ids),
                }
                for key, value in sorted(self.variables.items())
            },
        }
