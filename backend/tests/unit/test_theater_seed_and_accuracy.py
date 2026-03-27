import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

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
from app.services.simulation.simulation_engine import SimulationEngine
from app.services.theater.prediction_theater_service import (
    PredictionAccuracyTracker,
    PredictionTheaterService,
    TheaterPathOption,
    TheaterPathStep,
    TheaterNodeAccessError,
    TheaterTimeoutError,
    _normalized_topic_terms,
)
from app.services.simulation.simulation_engine import ModeratorDecision


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


def test_seed_extractor_extract_selected_topics_accepts_dict_and_list_payloads():
    extractor = SeedExtractor(db=None)  # type: ignore[arg-type]

    from_dict = extractor._extract_selected_topics(
        {
            "selected_topics": [
                "指针与内存",
                {"topic": "derivative 错因深挖"},
                {"selected_topic": "Python编程"},
            ]
        }
    )
    from_list = extractor._extract_selected_topics(
        [
            "指针与内存",
            {"topic": "derivative 错因深挖"},
            {"selected_topic": "Python编程"},
        ]
    )

    assert from_dict == {"指针与内存", "derivative 错因深挖", "Python编程"}
    assert from_list == {"指针与内存", "derivative 错因深挖", "Python编程"}


@pytest.mark.asyncio
async def test_seed_extractor_refine_with_llm_accepts_list_payload(monkeypatch):
    extractor = SeedExtractor(db=None)  # type: ignore[arg-type]
    seeds = [
        SimulationSeed(
            topic="指针与内存",
            context="",
            tension_point="",
            source_type="error_book",
            source_ids=["1"],
            relevance_score=0.9,
            suggested_scenario="study_group",
            suggested_experts=["错题教练"],
        ),
        SimulationSeed(
            topic="derivative 错因深挖",
            context="",
            tension_point="",
            source_type="error_book",
            source_ids=["2"],
            relevance_score=0.8,
            suggested_scenario="study_group",
            suggested_experts=["深度分析"],
        ),
    ]

    monkeypatch.setattr(
        "app.services.simulation.seed_extractor.analysis_llm.json_call",
        AsyncMock(return_value=["derivative 错因深挖"]),
    )

    refined = await extractor._refine_with_llm(
        seeds,
        scenario_key="study_group",
        limit=1,
    )

    assert [seed.topic for seed in refined] == ["derivative 错因深挖"]


@pytest.mark.asyncio
async def test_seed_extractor_prefers_cold_start_seeds_before_generic_fallback(monkeypatch):
    extractor = SeedExtractor(db=None)  # type: ignore[arg-type]
    user_id = uuid4()
    cold_start_seed = SimulationSeed(
        topic="把 特征值 变成第一轮可执行练习",
        context="来自任务或计划的冷启动种子。",
        tension_point="先说清第一步。",
        source_type="task_bootstrap",
        source_ids=["task-1"],
        relevance_score=0.74,
        suggested_scenario="study_group",
        suggested_experts=["学伴"],
    )

    for method_name in (
        "_galaxy_seeds",
        "_error_seeds",
        "_sprint_seeds",
        "_cognitive_seeds",
        "_timeline_seeds",
    ):
        monkeypatch.setattr(extractor, method_name, AsyncMock(return_value=[]))
    monkeypatch.setattr(extractor, "_cold_start_seeds", AsyncMock(return_value=[cold_start_seed]))

    seeds = await extractor.extract_seeds(user_id, scenario_key="study_group", limit=2)

    assert [seed.source_type for seed in seeds] == ["task_bootstrap"]


@pytest.mark.asyncio
async def test_simulation_engine_generates_rounds_as_replies(monkeypatch):
    engine = SimulationEngine(db=None)
    captured: dict[str, str] = {}

    async def fake_json_call(messages, *, fallback=None, temperature=0.45):
        del temperature
        captured["prompt"] = str(messages[-1]["content"])
        return {
            "speaker": "提问者",
            "message": "回应优等生刚才的解释，我更想先确认为什么这一步不能直接跳过。",
            "reply_to_speaker": "优等生",
            "turn_goal": "extend",
        }

    monkeypatch.setattr(
        "app.services.simulation.simulation_engine.analysis_llm.json_call",
        fake_json_call,
    )

    participants = [
        {"name": "优等生", "role_hint": "先解释定义", "stance": "supportive", "persona": {}},
        {"name": "提问者", "role_hint": "持续追问", "stance": "challenging", "persona": {}},
    ]
    participant_objects = engine._build_agent_participants(
        participants,
        scenario_key="study_group",
    )

    fallback_decision = engine._fallback_moderator_decision(
        topic="特征值",
        scenario_key="study_group",
        participants=participant_objects,
        rounds=[{"round": 1, "speaker": "优等生", "message": "我建议先从定义和几何意义开始。"}],
        planned_round_count=3,
    )

    round_item = await engine._generate_agent_round(
        topic="特征值",
        scenario_key="study_group",
        participants=participant_objects,
        rounds=[
            {"round": 1, "speaker": "优等生", "message": "我建议先从定义和几何意义开始。"},
        ],
        moderator_decision=ModeratorDecision(
            speaker=str(fallback_decision["speaker"]),
            reply_target="优等生",
            turn_goal=str(fallback_decision["turn_goal"]),
            real_time_insight=str(fallback_decision["real_time_insight"]),
            round_target=int(fallback_decision["round_target"]),
        ),
    )

    assert round_item["speaker"] == "提问者"
    assert round_item["reply_to_speaker"] == "优等生"
    assert round_item["turn_goal"] == "extend"
    assert "Reply target: 优等生" in captured["prompt"]


def test_simulation_engine_round_target_respects_scenario_cap():
    engine = SimulationEngine(db=None)

    assert (
        engine._normalize_round_target(
            10,
            current_rounds=2,
            scenario_key="knowledge_debate",
        )
        == 8
    )
    assert (
        engine._normalize_round_target(
            10,
            current_rounds=2,
            scenario_key="what_if_path",
        )
        == 6
    )


@pytest.mark.asyncio
async def test_simulation_engine_load_checkpoint_falls_back_to_local_storage(monkeypatch):
    engine = SimulationEngine(db=None)
    session_id = "sim-local-fallback"
    engine._local_checkpoints[session_id] = {
        "id": session_id,
        "user_id": TEST_USER_ID,
        "scenario_key": "study_group",
        "participants": [{"name": "提问者"}],
        "participant_runtime": [{"name": "提问者", "memory": [{"message": "最近观点"}]}],
        "rounds": [],
    }

    async def broken_get(key):
        del key
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(cache_service, "get", broken_get)

    payload = await engine._load_checkpoint(
        session_id=session_id,
        user_id=UUID(TEST_USER_ID),
    )

    assert payload["id"] == session_id
    assert payload["participants"][0]["memory"][0]["message"] == "最近观点"


@pytest.mark.asyncio
async def test_free_mode_target_context_backfills_missing_required_fields(monkeypatch):
    service = PredictionTheaterService(db=None)  # type: ignore[arg-type]

    async def fake_json_call(messages, *, fallback=None, temperature=0.2):
        del messages, fallback, temperature
        return {"target_name": "特征值"}

    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.analysis_llm.json_call",
        fake_json_call,
    )

    context = await service._build_free_mode_target_context("帮我推演特征值")

    assert context.name == "特征值"
    assert context.description
    assert len(context.backbone) >= 3


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


def test_normalized_topic_terms_split_compound_chinese_topic():
    terms = _normalized_topic_terms("我想补一下指针与内存")

    assert "指针" in terms
    assert "内存" in terms


def test_normalized_topic_terms_expand_linear_algebra_alias():
    terms = _normalized_topic_terms("帮我推演特征值与特征向量")

    assert "线性代数" in terms


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
async def test_resolve_target_node_prefers_multi_term_match(db_session):
    target = KnowledgeNode(
        name="C/C++编程",
        description="C语言基础、指针、内存模型",
        importance_level=4,
        is_seed=True,
    )
    distractor = KnowledgeNode(
        name="操作系统",
        description="进程、内存管理、文件系统",
        importance_level=5,
        is_seed=True,
    )
    db_session.add_all([target, distractor])
    await db_session.commit()
    await db_session.refresh(target)

    service = PredictionTheaterService(db_session)
    resolved = await service._resolve_target_node(
        topic="我想补一下指针与内存",
        target_node_id=None,
    )

    assert resolved.id == target.id


@pytest.mark.asyncio
async def test_resolve_target_node_uses_character_overlap_fallback(db_session):
    target = KnowledgeNode(
        name="特征分解与谱分析",
        description="矩阵谱、相似对角化与不变子空间",
        importance_level=4,
        is_seed=True,
    )
    distractor = KnowledgeNode(
        name="操作系统",
        description="进程、调度与文件系统",
        importance_level=5,
        is_seed=True,
    )
    db_session.add_all([target, distractor])
    await db_session.commit()
    await db_session.refresh(target)

    service = PredictionTheaterService(db_session)
    resolved = await service._resolve_target_node(
        topic="帮我推演特征值与特征向量",
        target_node_id=None,
    )

    assert resolved.id == target.id


@pytest.mark.asyncio
async def test_resolve_target_node_uses_alias_expansion_for_linear_algebra(db_session):
    target = KnowledgeNode(
        name="线性代数",
        description="矩阵、向量、特征分解与线性变换",
        importance_level=4,
        is_seed=True,
    )
    distractor = KnowledgeNode(
        name="概率论与数理统计",
        description="随机变量、概率分布与统计推断",
        importance_level=5,
        is_seed=True,
    )
    db_session.add_all([target, distractor])
    await db_session.commit()
    await db_session.refresh(target)

    service = PredictionTheaterService(db_session)
    resolved = await service._resolve_target_node(
        topic="帮我推演特征值与特征向量",
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


def test_theater_timeline_builds_daily_frames():
    service = PredictionTheaterService(db=AsyncMock())
    option = TheaterPathOption(
        id="path_foundation",
        title="稳扎稳打",
        summary="先补前置。",
        strategy_type="foundation",
        expert_ids=["galaxy_guide"],
        estimated_completion_rate=0.82,
        estimated_mastery=78.0,
        daily_minutes=40,
        risks=["节奏稳，但需要连续性。"],
        steps=[
            TheaterPathStep(
                index=1,
                node_id="node-1",
                node_name="行列式",
                rationale="先补前置。",
                current_mastery=42.0,
                predicted_mastery=63.0,
                risk_level="high",
                estimated_minutes=35,
                day_label="Day 1",
            ),
            TheaterPathStep(
                index=2,
                node_id="node-2",
                node_name="特征值",
                rationale="推进目标节点。",
                current_mastery=55.0,
                predicted_mastery=78.0,
                risk_level="medium",
                estimated_minutes=45,
                day_label="Day 7",
            ),
        ],
    )

    timeline = service._build_timeline(
        [option],
        [{"turn_index": 0, "content": "先补前置。"}],
        horizon_days=7,
    )

    assert len(timeline) == 7
    assert timeline[0]["day_index"] == 1
    assert timeline[-1]["day_index"] == 7
    assert timeline[0]["route_id"] == "path_foundation"
    assert timeline[-1]["projected_mastery"] >= timeline[0]["projected_mastery"]
    assert timeline[0]["compare_label"] == "推荐基线"


@pytest.mark.asyncio
async def test_simulate_what_if_accepts_multiple_skips(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())
    monkeypatch.setattr(
        service,
        "_get_prediction_or_raise",
        AsyncMock(
            return_value={
                "target_name": "线性代数",
                "paths": [
                    {
                        "id": "route-a",
                        "estimated_mastery": 82.0,
                        "estimated_completion_rate": 0.88,
                        "steps": [
                            {
                                "index": 1,
                                "node_id": "node-1",
                                "node_name": "行列式",
                                "risk_level": "high",
                                "current_mastery": 38.0,
                                "estimated_minutes": 35,
                            },
                            {
                                "index": 2,
                                "node_id": "node-2",
                                "node_name": "特征值",
                                "risk_level": "medium",
                                "current_mastery": 48.0,
                                "estimated_minutes": 40,
                            },
                            {
                                "index": 3,
                                "node_id": "node-3",
                                "node_name": "特征向量",
                                "risk_level": "medium",
                                "current_mastery": 61.0,
                                "estimated_minutes": 45,
                            },
                        ],
                    }
                ],
            }
        ),
    )

    result = await service.simulate_what_if(
        user_id=uuid4(),
        prediction_id="prediction-1",
        route_id="route-a",
        skip_node_ids=["node-1", "node-2"],
    )

    assert result["skip_node_names"] == ["行列式", "特征值"]
    assert len(result["branch_timeline"]) >= 4
    assert len(result["remaining_path"]) == 1
    assert result["predicted_mastery"] < result["original_mastery"]


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


@pytest.mark.asyncio
async def test_simulation_engine_waits_for_user_and_continues(monkeypatch):
    engine = SimulationEngine(db=None)
    decisions = iter(
        [
            SimpleNamespace(
                speaker="优等生",
                reply_target="",
                turn_goal="open",
                real_time_insight="先建立一个共同框架。",
                round_target=4,
                should_pause_for_user=True,
                should_end=False,
                interaction_type="choice",
                interaction_prompt="你会先支持哪种拆解方式？",
                interaction_options=["优等生", "提问者"],
                suggested_replies=["我会先画出前置依赖，再做一道题。"],
            ),
            SimpleNamespace(
                speaker="提问者",
                reply_target="你",
                turn_goal="synthesize",
                real_time_insight="用户已经给出判断，现在适合把讨论收束成行动。",
                round_target=5,
                should_pause_for_user=False,
                should_end=True,
                interaction_type="choice",
                interaction_prompt="",
                interaction_options=[],
                suggested_replies=[],
            ),
        ]
    )

    async def fake_generate_participants(**kwargs):
        del kwargs
        return [
            {"name": "优等生", "role_hint": "先搭框架", "stance": "supportive", "persona": {}},
            {"name": "提问者", "role_hint": "追问盲点", "stance": "challenging", "persona": {}},
        ]

    async def fake_moderate_next_turn(**kwargs):
        del kwargs
        return next(decisions)

    async def fake_generate_agent_round(**kwargs):
        moderator_decision = kwargs["moderator_decision"]
        return {
            "round": len(kwargs["rounds"]) + 1,
            "speaker": moderator_decision.speaker,
            "message": f"{moderator_decision.speaker} 围绕当前思路继续推进。",
            "reply_to_speaker": moderator_decision.reply_target,
            "turn_goal": moderator_decision.turn_goal,
            "speaker_type": "agent",
        }

    monkeypatch.setattr(
        "app.services.simulation.simulation_engine.generate_participants",
        fake_generate_participants,
    )
    monkeypatch.setattr(engine, "_moderate_next_turn", fake_moderate_next_turn)
    monkeypatch.setattr(engine, "_generate_agent_round", fake_generate_agent_round)

    first_pass_events = [
        event
        async for event in engine.stream(
            topic="特征值与特征向量",
            scenario_key="study_group",
            await_user_input=True,
        )
    ]

    interaction_event = next(payload for event_name, payload in first_pass_events if event_name == "interaction")
    waiting_session = next(payload["session"] for event_name, payload in first_pass_events if event_name == "complete")

    assert interaction_event["state"] == "WAITING_FOR_USER"
    assert waiting_session["pending_interaction"]["prompt"] == "你会先支持哪种拆解方式？"

    second_pass_events = [
        event
        async for event in engine.continue_stream(
            session_id=waiting_session["id"],
            user_response="我会先画出前置依赖，再做一道题。",
            await_user_input=True,
        )
    ]

    user_round_payload = next(payload for event_name, payload in second_pass_events if event_name == "round")
    completed_session = next(payload["session"] for event_name, payload in second_pass_events if event_name == "complete")

    assert user_round_payload["round"]["speaker"] == "你"
    assert completed_session["state"] == "COMPLETED"
    assert any(item["speaker"] == "你" for item in completed_session["rounds"])


@pytest.mark.asyncio
async def test_simulation_continue_api_returns_404_when_session_missing():
    app = _build_test_app()
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db] = lambda: object()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/sessions/missing-session/continue",
            json={"user_response": "我会先画图再推导"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 404
    assert "not found or expired" in response.json()["detail"]
