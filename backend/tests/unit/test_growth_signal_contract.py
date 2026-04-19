from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from app.aurora.growth_signal_contract import GrowthSignalContract


def test_growth_signal_contract_bounds_recent_items_and_serializes_cleanly() -> None:
    contract = GrowthSignalContract.from_service_data(
        user_id=uuid4(),
        sampled_at=datetime(2026, 4, 19, 9, 0, 0),
        streak_stats={"current_streak": 9},
        user_achievements=[
            {"achievement_id": f"ach-{index}", "achievement_name": f"Achievement {index}"}
            for index in range(7)
        ],
    )

    payload = contract.to_payload()

    assert payload["cold_start"] is False
    assert payload["growth_phase"] == "building"
    assert payload["streak_days"] == 9
    assert payload["achievement_count"] == 7
    assert len(payload["recent_achievement_ids"]) == 5
    assert len(payload["recent_achievement_labels"]) == 5
    assert len(payload["evidence"]) <= 4
    assert json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_growth_signal_contract_explicitly_marks_cold_start() -> None:
    contract = GrowthSignalContract.build_cold_start(
        user_id=uuid4(),
        sampled_at=datetime(2026, 4, 19, 9, 0, 0),
        fallback_reason="no_achievement_service",
    )

    payload = contract.to_payload()

    assert payload["cold_start"] is True
    assert payload["growth_phase"] == "cold_start"
    assert payload["fallback_reason"] == "no_achievement_service"
    assert payload["momentum_score"] == 0.0
    assert payload["evidence"][0]["kind"] == "fallback"
