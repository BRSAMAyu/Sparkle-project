from __future__ import annotations

from datetime import timezone, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import app.services.self_evolution_service as self_evolution_module
from app.services.self_evolution_service import (
    CohortPromotionService,
    MetricBaselineService,
    StrategyCalibrationService,
    UnderstandingDepthService,
    UnderstandingDepthSnapshot,
    _redis_json_get,
    _redis_json_set,
    _week_bucket,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str):
        self.values[key] = value

    async def setex(self, key: str, seconds: int, value: str):
        self.values[key] = value

    async def exists(self, key: str) -> int:
        return 1 if key in self.values else 0


class FakeDepthDb:
    def __init__(self, scalar_values: list[int]):
        self._scalar_values = list(scalar_values)

    async def scalar(self, _stmt):
        return self._scalar_values.pop(0)

    async def execute(self, _stmt):
        return SimpleNamespace(scalar=lambda: 0)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_strategy_calibration_marks_rule_as_weak_after_three_low_hit_weeks():
    redis = FakeRedis()
    service = StrategyCalibrationService(redis=redis)
    user_id = uuid4()

    weeks = [_week_bucket(_utcnow() - timedelta(days=offset * 7)) for offset in range(3)]
    for week in weeks:
        await _redis_json_set(
            redis,
            service._weekly_key(user_id, week),
            {"low_completion_rate": {"hit": 1, "miss": 4}},
            ttl_seconds=service.TTL_SECONDS,
        )

    calibration = await service.get_rule_calibration(user_id=user_id)
    assert "low_completion_rate" in calibration["weak_rules"]

    adjusted, _ = await service.apply_rule_calibration(
        user_id=user_id,
        mappings=[
            {
                "rule_key": "low_completion_rate",
                "signal_key": "low_completion_rate",
                "confidence_tier": "inferred",
            }
        ],
    )

    assert adjusted[0]["confidence_tier"] == "weak"
    assert "仅供参考" in adjusted[0]["calibration_note"]


@pytest.mark.asyncio
async def test_understanding_depth_only_notifies_upgrades():
    redis = FakeRedis()
    service = UnderstandingDepthService(db=SimpleNamespace(), redis=redis)
    service.updates.enqueue = AsyncMock(return_value=True)
    service.evaluate = AsyncMock(
        return_value=UnderstandingDepthSnapshot(level="L3", score=3, dimensions={})
    )

    user_id = uuid4()
    await _redis_json_set(
        redis,
        service._current_level_key(user_id),
        {"level": "L4"},
        ttl_seconds=service.TTL_SECONDS,
    )
    payload = await service.maybe_enqueue_upgrade(user_id=user_id)

    assert payload is None
    service.updates.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_understanding_depth_evaluate_reaches_l5_when_all_thresholds_match():
    redis = FakeRedis()
    service = UnderstandingDepthService(db=FakeDepthDb([3, 2]), redis=redis)
    service.calibration.recent_alignment_scores = AsyncMock(return_value=[0.71, 0.74, 0.79])
    service._insight_adoption_rate = AsyncMock(return_value=0.52)
    service._strategy_resonance_rate = AsyncMock(return_value=0.63)

    snapshot = await service.evaluate(user_id=uuid4())

    assert snapshot.level == "L5"
    assert snapshot.dimensions["active_preferences"] == 3
    assert snapshot.dimensions["active_patterns"] == 2
    assert snapshot.dimensions["strategy_resonance_rate"] == 0.63


@pytest.mark.asyncio
async def test_understanding_depth_upgrade_payload_contains_natural_hint():
    redis = FakeRedis()
    service = UnderstandingDepthService(db=SimpleNamespace(), redis=redis)
    service.updates.enqueue = AsyncMock(return_value=True)
    service.evaluate = AsyncMock(
        return_value=UnderstandingDepthSnapshot(level="L3", score=3, dimensions={})
    )

    payload = await service.maybe_enqueue_upgrade(user_id=uuid4())

    assert payload is not None
    assert payload["metadata"]["evolution_kind"] == "understanding_depth"
    assert "自然" in payload["metadata"]["natural_hint"]


@pytest.mark.asyncio
async def test_metric_baseline_service_flags_anomaly():
    redis = FakeRedis()
    service = MetricBaselineService(redis=redis)

    await _redis_json_set(
        redis,
        service.BASELINE_KEY,
        {
            "computed_at": _utcnow().isoformat(),
            "points": 14,
            "metrics": {
                "alignment_score": {
                    "p50": 0.72,
                    "p95": 0.83,
                    "mean": 0.7,
                    "std": 0.05,
                }
            },
        },
        ttl_seconds=service.TTL_SECONDS,
    )
    await _redis_json_set(
        redis,
        service.SNAPSHOT_KEY,
        [
            {"captured_at": _utcnow().isoformat(), "alignment_score": 0.86},
        ],
        ttl_seconds=service.TTL_SECONDS,
    )

    baseline, anomalies = await service.get_status_payload()

    assert baseline["metrics"]["alignment_score"]["mean"] == 0.7
    assert "alignment_score" in anomalies


@pytest.mark.asyncio
async def test_cohort_promotion_service_skips_off_week(monkeypatch):
    redis = FakeRedis()
    service = CohortPromotionService(redis=redis)

    monkeypatch.setattr(
        self_evolution_module,
        "_utcnow",
        lambda: datetime(2026, 3, 9, 10, 0, 0),
    )

    result = await service.evaluate_and_promote()

    assert result["status"] == "skipped"
    assert result["reason"] == "off_week"


@pytest.mark.asyncio
async def test_cohort_promotion_service_promotes_after_two_consistent_cycles(monkeypatch):
    redis = FakeRedis()
    service = CohortPromotionService(redis=redis)
    monkeypatch.setattr(
        self_evolution_module,
        "_utcnow",
        lambda: datetime(2026, 3, 10, 10, 0, 0),
    )

    recommendation = {
        "cohorts": {"A": {}, "B": {}, "C": {}},
        "recommendation": {
            "promotion_ready": True,
            "recommended_default": "B",
            "margin": 0.08,
        },
    }
    service._run_evaluator = AsyncMock(return_value=recommendation)

    first = await service.evaluate_and_promote()
    second = await service.evaluate_and_promote()
    baseline = await _redis_json_get(redis, service.BASELINE_KEY, None)

    assert first["recommendation"]["recommended_default"] == "B"
    assert second["recommendation"]["recommended_default"] == "B"
    assert baseline["baseline_strategy"] == "B"
