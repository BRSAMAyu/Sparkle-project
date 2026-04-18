from __future__ import annotations

from app.aurora.schemas import DistilledStrategyLifecycle
from app.data.seed_content_initial import OFFICIAL_LIBRARIES
from app.learning.seed_bridge import export_seed_bridge_fingerprint, import_seed_library_content


def test_seed_bridge_imports_official_library_content() -> None:
    strategies = import_seed_library_content()

    expected_count = sum(len(library["items"]) for library in OFFICIAL_LIBRARIES)
    assert len(strategies) == expected_count
    assert len({strategy.id for strategy in strategies}) == expected_count
    assert all(strategy.source_trajectory_type == "human_authored" for strategy in strategies)
    assert all(strategy.status == DistilledStrategyLifecycle.DISTILLED for strategy in strategies)
    assert any(strategy.title == "一元二次方程求解示例" for strategy in strategies)

    fingerprint = export_seed_bridge_fingerprint(strategies)
    assert len(fingerprint) == 64
