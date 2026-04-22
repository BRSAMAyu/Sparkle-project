from __future__ import annotations

import random

import pytest

from app.aurora.privacy import laplace_noise


def test_laplace_noise_rejects_non_positive_epsilon() -> None:
    with pytest.raises(ValueError):
        laplace_noise(10.0, epsilon=0.0)


def test_laplace_noise_is_finite_and_seed_stable() -> None:
    rng = random.Random(7)

    value = laplace_noise(10.0, epsilon=0.3, rng=rng)

    assert isinstance(value, float)
    assert round(value, 4) == round(value, 4)


def test_laplace_noise_sample_mean_stays_near_original_value() -> None:
    rng = random.Random(11)
    samples = [laplace_noise(25.0, epsilon=0.3, rng=rng) for _ in range(500)]
    mean = sum(samples) / len(samples)

    assert abs(mean - 25.0) < 1.0
