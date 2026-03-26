from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.services.simulation.seed_extractor import SeedExtractor, SimulationSeed
from app.services.theater.prediction_theater_service import PredictionAccuracyTracker


@pytest.fixture(autouse=True)
def _reset_local_cache():
    previous_redis = cache_service.redis
    previous_local_cache = dict(cache_service._local_cache)
    cache_service.redis = None
    cache_service._local_cache.clear()
    yield
    cache_service._local_cache.clear()
    cache_service._local_cache.update(previous_local_cache)
    cache_service.redis = previous_redis


def test_simulation_seed_round_trip():
    seed = SimulationSeed(
        topic="矩阵特征值",
        context="图谱显示特征值与行列式存在前置依赖。",
        tension_point="是否需要先补行列式展开熟练度。",
        source_type="galaxy",
        source_ids=["node-1", "node-2"],
        relevance_score=0.91,
        suggested_scenario="knowledge_debate",
        suggested_experts=["星图导航", "深度分析"],
    )

    reconstructed = SimulationSeed.from_dict(seed.to_dict())

    assert reconstructed == seed
    assert reconstructed.suggested_experts == ["星图导航", "深度分析"]


@pytest.mark.asyncio
async def test_prediction_accuracy_tracker_records_summary():
    tracker = PredictionAccuracyTracker()
    prediction_id = f"prediction-{uuid4()}"

    await tracker.record_prediction(
        {
            "prediction_id": prediction_id,
            "selected_prediction": {
                "estimated_completion_rate": 0.84,
                "estimated_mastery": 79.0,
            },
        }
    )

    summary = await tracker.record_actual(
        prediction_id,
        actual_completion_rate=0.76,
        actual_mastery=74.0,
    )

    assert summary is not None
    assert summary["prediction_id"] == prediction_id
    assert 0.0 <= summary["accuracy_score"] <= 1.0
    cached_summary = await tracker.get_summary(prediction_id)
    assert cached_summary == summary


@pytest.mark.asyncio
async def test_seed_extractor_reads_from_cache_before_regenerating(monkeypatch):
    extractor = SeedExtractor(db=None)  # type: ignore[arg-type]
    user_id = uuid4()
    generated_seed = SimulationSeed(
        topic="向量点乘",
        context="第一次生成",
        tension_point="容易把几何意义和代数计算混淆。",
        source_type="galaxy",
        source_ids=["seed-1"],
        relevance_score=0.8,
        suggested_scenario="study_group",
        suggested_experts=["数学专家"],
    )
    calls = {"count": 0}

    async def fake_extract(target_user_id, *, scenario_key=None, limit=3):
        assert target_user_id == user_id
        assert scenario_key == "study_group"
        assert limit == 2
        calls["count"] += 1
        return [generated_seed]

    monkeypatch.setattr(extractor, "extract_seeds", fake_extract)

    first = await extractor.get_cached_or_generate(
        user_id,
        scenario_key="study_group",
        limit=2,
    )
    second = await extractor.get_cached_or_generate(
        user_id,
        scenario_key="study_group",
        limit=2,
    )
    refreshed = await extractor.get_cached_or_generate(
        user_id,
        scenario_key="study_group",
        limit=2,
        force_refresh=True,
    )

    assert calls["count"] == 2
    assert first == [generated_seed]
    assert second == [generated_seed]
    assert refreshed == [generated_seed]
