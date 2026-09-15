from __future__ import annotations

from app.learning.rolling_correlator import (
    benjamini_hochberg,
    correlate_dimensions,
    spearman_rank_correlation,
)


def test_spearman_handles_all_missing_values() -> None:
    r_value, p_value, sample_days = spearman_rank_correlation(
        [None, None, None],
        [None, None, None],
    )

    assert r_value == 0.0
    assert p_value == 1.0
    assert sample_days == 0


def test_spearman_detects_perfect_monotonic_alignment() -> None:
    r_value, p_value, sample_days = spearman_rank_correlation(
        [1, 2, 3, 4, 5],
        [10, 20, 30, 40, 50],
    )

    assert r_value == 1.0
    assert p_value == 0.0
    assert sample_days == 5


def test_benjamini_hochberg_preserves_monotonic_adjustment() -> None:
    adjusted = benjamini_hochberg([0.01, 0.02, 0.20])

    assert adjusted == [0.03, 0.03, 0.2]


def test_correlate_dimensions_marks_density_insufficient_when_window_sparse() -> None:
    results = correlate_dimensions(
        {
            "dim_a": [1.0, 2.0, None, None, None],
            "dim_b": [1.0, 2.0, None, None, None],
        },
        density_min_rank_pairs=10,
        density_min_coverage=0.8,
    )

    assert len(results) == 1
    assert results[0].density_insufficient is True
