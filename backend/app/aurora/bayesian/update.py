"""Small Bayesian update helper used by Aurora runtime experiments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BayesianUpdate:
    prior: float
    likelihood: float
    posterior: float


def update_posterior(prior: float, likelihood: float) -> BayesianUpdate:
    """Compute a bounded posterior from a prior and likelihood."""

    clamped_prior = min(max(prior, 0.0), 1.0)
    clamped_likelihood = min(max(likelihood, 0.0), 1.0)
    numerator = clamped_prior * clamped_likelihood
    denominator = numerator + (1.0 - clamped_prior) * (1.0 - clamped_likelihood)
    posterior = numerator / denominator if denominator else clamped_prior
    return BayesianUpdate(prior=clamped_prior, likelihood=clamped_likelihood, posterior=posterior)

