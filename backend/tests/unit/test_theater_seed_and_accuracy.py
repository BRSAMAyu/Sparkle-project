import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user_id, get_db
from app.api.v1.simulation import router as simulation_router
from app.api.v1.theater import router as theater_router
from app.core.cache import cache_service
from app.main import sparkle_exception_handler
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.simulation.seed_extractor import SeedExtractor, SimulationSeed
from app.services.theater.prediction_theater_service import (
    PredictionAccuracyTracker,
    PredictionTheaterService,
    TheaterPathOption,
    TheaterPathStep,
    TheaterNodeAccessError,
    TheaterTimeoutError,
    _normalized_topic_terms,
)


TEST_USER_ID = str(uuid4())


def _build_test_app():
    app = FastAPI()
    app.include_router(theater_router, prefix="/api/v1")
    app.include_router(simulation_router, prefix="/api/v1")
    app.add_exception_handler(TheaterTimeoutError, sparkle_exception_handler)
    app.add_exception_handler(TheaterNodeAccessError, sparkle_exception_handler)
    return app


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


@pytest.mark.asyncio
async def test_seed_extractor_treats_cached_empty_list_as_cache_hit(monkeypatch):
    extractor = SeedExtractor(db=None)  # type: ignore[arg-type]
    user_id = uuid4()
    cache_key = extractor._cache_key(user_id, scenario_key="study_group", limit=2)
    await cache_service.set(cache_key, [], ttl=60)
    calls = {"count": 0}

    async def fake_extract(target_user_id, *, scenario_key=None, limit=3):
        calls["count"] += 1
        return [
            SimulationSeed(
                topic="不该被生成",
                context="",
                tension_point="",
                source_type="fallback",
                source_ids=[],
                relevance_score=0.0,
                suggested_scenario="study_group",
                suggested_experts=[],
            )
        ]

    monkeypatch.setattr(extractor, "extract_seeds", fake_extract)

    seeds = await extractor.get_cached_or_generate(
        user_id,
        scenario_key="study_group",
        limit=2,
    )

    assert seeds == []
    assert calls["count"] == 0


@pytest.mark.asyncio
async def test_seed_extractor_fallback_seeds_are_stable_for_empty_user():
    extractor = SeedExtractor(db=None)  # type: ignore[arg-type]

    seeds = extractor._fallback_seeds(scenario_key="study_group", limit=3)

    assert len(seeds) == 3
    assert all(seed.topic for seed in seeds)
    assert all(seed.suggested_scenario for seed in seeds)


@pytest.mark.asyncio
async def test_resolve_target_node_for_user_rejects_inaccessible_explicit_node(db_session, test_user):
    node = KnowledgeNode(
        name="Private target node",
        description="Only explicit user access should allow this node.",
        importance_level=1,
        is_seed=False,
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    service = PredictionTheaterService(db_session)

    with pytest.raises(TheaterNodeAccessError):
        await service._resolve_target_node_for_user(
            user_id=test_user.id,
            topic="ignored",
            target_node_id=node.id,
        )


@pytest.mark.asyncio
async def test_resolve_target_node_for_user_accepts_user_status_node(db_session, test_user):
    node = KnowledgeNode(
        name="Unlocked target node",
        description="This node is available via user status.",
        importance_level=1,
        is_seed=False,
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    db_session.add(
        UserNodeStatus(
            user_id=test_user.id,
            node_id=node.id,
            is_unlocked=True,
            mastery_score=42.0,
        )
    )
    await db_session.commit()

    service = PredictionTheaterService(db_session)
    resolved = await service._resolve_target_node_for_user(
        user_id=test_user.id,
        topic="ignored",
        target_node_id=node.id,
    )

    assert resolved.id == node.id


def test_normalized_topic_terms_extracts_keywords_from_natural_language():
    terms = _normalized_topic_terms("帮我推演一下学 Python 的路径")

    assert "python" in terms
    assert "帮我推演一下学 python 的路径" in terms
    assert all(term.strip() for term in terms)


@pytest.mark.asyncio
async def test_resolve_target_node_matches_natural_language_topic(db_session):
    target = KnowledgeNode(
        name="Python编程",
        description="Python语法、数据结构、面向对象",
        importance_level=4,
        is_seed=True,
    )
    distractor = KnowledgeNode(
        name="程序设计基础",
        description="变量、控制流、函数、基本算法",
        importance_level=3,
        is_seed=True,
    )
    db_session.add_all([target, distractor])
    await db_session.commit()
    await db_session.refresh(target)

    service = PredictionTheaterService(db_session)
    resolved = await service._resolve_target_node(
        topic="学 Python 的路径",
        target_node_id=None,
    )

    assert resolved.id == target.id


@pytest.mark.asyncio
async def test_theater_api_returns_timeout_payload(monkeypatch):
    app = _build_test_app()
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db] = lambda: object()

    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14):
        raise TheaterTimeoutError()

    monkeypatch.setattr(
        "app.api.v1.theater.PredictionTheaterService.generate_prediction",
        fake_generate_prediction,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/theater/predictions/generate",
            json={"topic": "两周掌握特征值"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 504
    payload = response.json()
    assert payload["message"].startswith("这次推演花的时间有点长")
    assert payload["detail"]["error_code"] == "THEATER_TIMEOUT"


@pytest.mark.asyncio
async def test_theater_api_returns_404_for_inaccessible_target(monkeypatch):
    app = _build_test_app()
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db] = lambda: object()

    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14):
        raise TheaterNodeAccessError()

    monkeypatch.setattr(
        "app.api.v1.theater.PredictionTheaterService.generate_prediction",
        fake_generate_prediction,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/theater/predictions/generate",
            json={"topic": "两周掌握特征值", "target_node_id": str(uuid4())},
        )

    app.dependency_overrides = {}

    assert response.status_code == 404
    payload = response.json()
    assert payload["message"] == "未找到可访问的知识节点"


@pytest.mark.asyncio
async def test_build_discussion_accepts_list_payload(monkeypatch, db_session):
    service = PredictionTheaterService(db_session)
    option = TheaterPathOption(
        id="path_foundation",
        title="稳扎稳打",
        summary="先补前置，再推进目标。",
        strategy_type="foundation",
        expert_ids=["galaxy_guide"],
        estimated_completion_rate=0.8,
        estimated_mastery=76.0,
        daily_minutes=40,
        risks=["后期任务较密"],
        steps=[
            TheaterPathStep(
                index=1,
                node_id="node-1",
                node_name="Python编程",
                rationale="先打通语法和基本数据结构。",
                current_mastery=48.0,
                predicted_mastery=71.0,
                risk_level="medium",
                estimated_minutes=40,
                day_label="Day 1",
            )
        ],
    )

    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.analysis_llm.json_call",
        AsyncMock(
            return_value=[
                {
                    "agent_id": "galaxy_guide",
                    "display_name": "星图导航",
                    "turn_type": "analysis",
                    "content": "先把依赖链补齐，再推目标节点。",
                    "related_node_ids": ["node-1"],
                }
            ]
        ),
    )

    turns = await service._build_discussion(
        topic="学 Python 的路径",
        target_name="Python编程",
        options=[option],
        graph_bundle={"nodes": [], "edges": []},
        pattern_names=[],
    )

    assert len(turns) == 1
    assert turns[0]["agent_id"] == "galaxy_guide"
    assert turns[0]["related_node_ids"] == ["node-1"]


@pytest.mark.asyncio
async def test_simulation_api_rejects_invalid_scenario_key():
    app = _build_test_app()
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db] = lambda: object()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={"topic": "矩阵特征值", "scenario_key": "not_real"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 422
    assert "Unsupported simulation scenario" in response.json()["detail"]
