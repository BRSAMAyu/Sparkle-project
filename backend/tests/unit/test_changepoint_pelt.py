from __future__ import annotations

from app.learning.changepoint_pelt import detect_change_points


def test_detect_change_points_returns_empty_for_short_series() -> None:
    assert detect_change_points([0.1] * 10, min_segment_size=6) == []


def test_detect_change_points_finds_known_mean_shift() -> None:
    values = [0.1] * 10 + [1.2] * 10

    results = detect_change_points(values, min_segment_size=5, penalty=0.3)

    assert results
    assert any(abs(item.index - 10) <= 1 for item in results)
    assert all(0.35 <= item.confidence <= 0.8 for item in results)
