import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user_id, get_db
from app.api.v1.simulation import router as simulation_router
from app.api.v1.theater import router as theater_router
from app.core.cache import cache_service
from app.core.exceptions import AuthorizationError, NotFoundError
from app.main import sparkle_exception_handler
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.theater_candidate_bundle import TheaterCandidateBundle
from app.models.theater_prediction import TheaterPrediction
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
    _utcnow,
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

    async def fake_extract(target_user_id, *, scenario_key=None, limit=3, allow_llm_refine=True):
        assert target_user_id == user_id
        assert scenario_key == "study_group"
        assert limit == 2
        assert allow_llm_refine is True
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

    async def fake_extract(target_user_id, *, scenario_key=None, limit=3, allow_llm_refine=True):
        del target_user_id, scenario_key, limit, allow_llm_refine
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

    assert len(seeds) == 1
    assert seeds[0].topic == ""
    assert seeds[0].source_type == "user_input_required"
    assert seeds[0].relevance_score == 0.0
    assert seeds[0].suggested_scenario == "study_group"


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
    assert "回应对象：优等生" in captured["prompt"]


def test_simulation_engine_round_target_respects_scenario_cap():
    engine = SimulationEngine(db=None)

    assert (
        engine._normalize_round_target(
            20,
            current_rounds=2,
            scenario_key="knowledge_debate",
        )
        == 12
    )
    assert (
        engine._normalize_round_target(
            20,
            current_rounds=2,
            scenario_key="what_if_path",
        )
        == 10
    )


def test_simulation_engine_latest_exchange_uses_chinese_round_copy():
    exchange = SimulationEngine._latest_exchange(
        [
            {
                "round": 1,
                "speaker": "学习伙伴",
                "message": "先把问题拆开来看。",
            }
        ]
    )

    assert "第 1 轮" in exchange
    assert "Round" not in exchange


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
        return {"target_name": "特征值学习路径"}

    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.analysis_llm.json_call",
        fake_json_call,
    )

    context = await service._build_free_mode_target_context("帮我推演特征值")

    assert context.name == "特征值学习路径"
    assert context.description
    assert len(context.backbone) >= 8
    assert context.resolution_mode == "freeform_only"


@pytest.mark.asyncio
async def test_generate_prediction_requests_clarification_for_short_freeform_topic(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())
    monkeypatch.setattr(service, "_topic_graph_candidates", AsyncMock(return_value=[]))

    payload = await service.generate_prediction(
        user_id=uuid4(),
        topic="数学",
    )

    assert payload["status"] == "clarification_needed"
    assert payload["prediction"] is None
    assert len(payload["questions"]) == 4


@pytest.mark.asyncio
async def test_generate_prediction_proceeds_when_freeform_context_is_sufficient(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())
    target_context = SimpleNamespace(
        name="特征值分解",
        description="围绕特征值分解的学习路径。",
        target_node_id=None,
        resolution_mode="freeform_only",
        backbone=[
            {
                "id": "step-1",
                "name": "矩阵乘法",
                "description": "已有前置",
                "mapped_galaxy_node_id": None,
                "is_target": False,
            },
            {
                "id": "step-2",
                "name": "特征值分解",
                "description": "目标",
                "mapped_galaxy_node_id": None,
                "is_target": True,
            },
        ],
        semantic_matches=[],
        disclaimer="仅供参考",
    )
    monkeypatch.setattr(service, "_resolve_target_context", AsyncMock(return_value=target_context))
    monkeypatch.setattr(service, "_get_mastery_map", AsyncMock(return_value={}))
    monkeypatch.setattr(
        service,
        "_build_user_learning_profile",
        AsyncMock(return_value={"average_session_minutes": 30}),
    )
    monkeypatch.setattr(service, "_top_pattern_names", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "_related_error_evidence", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        service,
        "_build_prediction_calibration",
        AsyncMock(return_value={"sample_count": 0, "data_sufficiency_score": 0.42}),
    )
    monkeypatch.setattr(
        service,
        "_topic_calibration_signal",
        AsyncMock(return_value={"sample_count": 0, "latest_pending_age_days": 4}),
    )
    monkeypatch.setattr(
        service,
        "_build_path_options",
        AsyncMock(
            return_value=[
                TheaterPathOption(
                    id="path-1",
                    title="约束优先路径",
                    summary="适合考试前快速补关键缺口。",
                    strategy_type="constraint_first",
                    expert_ids=["galaxy_guide"],
                    estimated_completion_rate=None,
                    estimated_mastery=None,
                    daily_minutes=30,
                    risks=["历史样本不足"],
                    steps=[
                        TheaterPathStep(
                            index=1,
                            node_id="step-1",
                            node_name="矩阵乘法",
                            rationale="先补前置。",
                            current_mastery=None,
                            predicted_mastery=None,
                            risk_level="medium",
                            estimated_minutes=30,
                            day_label="第 1 天",
                            source_type="ai_suggested",
                        )
                    ],
                    data_quality="low",
                    completion_range_low=0.6,
                    completion_range_high=0.8,
                    mastery_range_low=55.0,
                    mastery_range_high=72.0,
                )
            ]
        ),
    )
    monkeypatch.setattr(service, "_build_timeline", MagicMock(return_value=[]))
    monkeypatch.setattr(service.accuracy, "record_prediction", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_persist_prediction", AsyncMock(return_value=None))

    payload = await service.generate_prediction(
        user_id=uuid4(),
        topic="线性代数中的特征值分解",
        context="期末考试准备，我理解矩阵乘法，但不理解特征值的几何意义。",
        preview_mode=True,
    )

    assert payload["status"] == "ready"
    assert payload["target_name"] == "特征值分解"
    assert payload["paths"][0]["data_quality"] == "low"


@pytest.mark.asyncio
async def test_low_data_quality_routes_do_not_claim_precise_completion_rate(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())
    target_context = SimpleNamespace(
        name="现代诗阅读",
        description="自由主题",
        target_node_id=None,
        resolution_mode="freeform_only",
        backbone=[{"id": "step-1", "name": "意象分析", "description": "目标", "is_target": True}],
        semantic_matches=[],
        disclaimer="仅供参考",
    )
    monkeypatch.setattr(service, "_resolve_target_context", AsyncMock(return_value=target_context))
    monkeypatch.setattr(service, "_get_mastery_map", AsyncMock(return_value={}))
    monkeypatch.setattr(
        service,
        "_build_user_learning_profile",
        AsyncMock(return_value={"average_session_minutes": 25}),
    )
    monkeypatch.setattr(service, "_top_pattern_names", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "_related_error_evidence", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        service,
        "_build_prediction_calibration",
        AsyncMock(return_value={"sample_count": 0, "data_sufficiency_score": 0.42}),
    )
    monkeypatch.setattr(
        service,
        "_topic_calibration_signal",
        AsyncMock(return_value={"sample_count": 0, "latest_pending_age_days": 9}),
    )
    monkeypatch.setattr(
        service,
        "_build_path_options",
        AsyncMock(
            return_value=[
                TheaterPathOption(
                    id="path-1",
                    title="解释优先路径",
                    summary="先用例子建立直觉。",
                    strategy_type="custom",
                    expert_ids=["study_buddy"],
                    estimated_completion_rate=None,
                    estimated_mastery=None,
                    daily_minutes=25,
                    risks=["缺少真实样本"],
                    steps=[],
                    data_quality="low",
                    completion_range_low=0.55,
                    completion_range_high=0.75,
                    mastery_range_low=50.0,
                    mastery_range_high=68.0,
                )
            ]
        ),
    )
    monkeypatch.setattr(service, "_build_timeline", MagicMock(return_value=[]))
    monkeypatch.setattr(service.accuracy, "record_prediction", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_persist_prediction", AsyncMock(return_value=None))

    payload = await service.generate_prediction(
        user_id=uuid4(),
        topic="我想提高现代诗阅读的理解深度，用于选修课期末论文准备",
        preview_mode=True,
    )

    route = payload["paths"][0]
    assert route["data_quality"] == "low"
    assert route["estimated_completion_rate"] is None
    assert route["completion_range_low"] > 0
    assert route["completion_range_high"] > route["completion_range_low"]


def test_materialize_dynamic_steps_keeps_ai_suggested_mastery_unknown_without_data():
    service = PredictionTheaterService(db=AsyncMock())

    steps = service._materialize_dynamic_steps(
        plan={
            "strategy_type": "custom",
            "steps": [
                {
                    "node_name": "特征值的几何意义",
                    "rationale": "先澄清概念直觉。",
                    "estimated_minutes": 35,
                    "risk_level": "high",
                    "source_type": "ai_suggested",
                    "predicted_mastery": None,
                }
            ],
        },
        backbone=[],
        mastery_map={},
        checkpoint_days=[1, 3, 7],
        available_time_per_day=30,
        risk_overrides=None,
    )

    assert len(steps) == 1
    assert steps[0].source_type == "ai_suggested"
    assert steps[0].predicted_mastery is None


def test_route_score_and_rationale_use_current_strategy_names():
    service = PredictionTheaterService(db=AsyncMock())

    target_backtrack_score = service._route_score(
        completion_rate=0.72,
        estimated_mastery=74.0,
        risks=["需要接受先看目标再回补前置的节奏"],
        strategy_type="target_backtrack",
    )
    constraint_first_score = service._route_score(
        completion_rate=0.72,
        estimated_mastery=74.0,
        risks=["需要接受先看目标再回补前置的节奏"],
        strategy_type="constraint_first",
    )

    assert target_backtrack_score < constraint_first_score
    assert "小步节奏" in service._step_rationale(
        strategy_type="constraint_first",
        node_name="行列式",
        is_target=False,
    )
    assert "完整依赖链" in service._step_rationale(
        strategy_type="full_chain",
        node_name="线性变换",
        is_target=False,
    )
    assert "回补节点" in service._step_rationale(
        strategy_type="target_backtrack",
        node_name="特征多项式",
        is_target=False,
    )


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


@pytest.mark.asyncio
async def test_freeform_prediction_persists_candidate_bundle(db_session, test_user, monkeypatch):
    service = PredictionTheaterService(db_session)

    monkeypatch.setattr(service, "_get_mastery_map", AsyncMock(return_value={}))
    monkeypatch.setattr(
        service,
        "_build_user_learning_profile",
        AsyncMock(return_value={"average_session_minutes": 35}),
    )
    monkeypatch.setattr(service, "_top_pattern_names", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        service,
        "_build_discussion",
        AsyncMock(
            return_value=[
                {
                    "turn_index": 0,
                    "agent_id": "galaxy_guide",
                    "display_name": "星图导航",
                    "turn_type": "analysis",
                    "content": "先把核心概念铺开，再收束成目标。",
                    "related_node_ids": ["free-node-1"],
                }
            ]
        ),
    )
    monkeypatch.setattr(service.accuracy, "record_prediction", AsyncMock(return_value=None))
    enqueue_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.SystemUpdateService.enqueue",
        enqueue_mock,
    )
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.analysis_llm.json_call",
        AsyncMock(
            return_value={
                "target_name": "LLM 学习路径",
                "description": "围绕 LLM 的中文自由推演。",
                "prerequisites": ["Python 基础", "概率基础"],
                "core_concepts": ["Transformer", "预训练", "推理"],
                "milestones": ["完成一个中文问答 Demo"],
                "misconceptions": ["把提示词工程当成全部能力"],
                "applications": ["搭建学习助手"],
                "aliases": ["大语言模型"],
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "_semantic_enrich_freeform_nodes",
        AsyncMock(
            return_value=(
                [
                    {
                        "id": "free-node-1",
                        "name": "Transformer",
                        "description": "核心概念",
                        "node_type": "concept",
                        "is_target": False,
                        "source_type": "freeform",
                        "mapped_galaxy_node_id": None,
                        "candidate_status": "pending_review",
                        "aliases": [],
                    },
                    {
                        "id": "free-node-2",
                        "name": "LLM 学习路径",
                        "description": "目标",
                        "node_type": "target",
                        "is_target": True,
                        "source_type": "freeform",
                        "mapped_galaxy_node_id": None,
                        "candidate_status": "pending_review",
                        "aliases": ["大语言模型"],
                    },
                ],
                [],
            )
        ),
    )

    payload = await service.generate_prediction(
        user_id=test_user.id,
        topic="我想系统学习 LLM",
        preview_mode=False,
        simulation_session_id="sim-session-123",
        context="为了做一个问答 Demo，我想系统学习 LLM，目前只懂一点 Python。",
    )

    result = await db_session.execute(select(TheaterCandidateBundle))
    bundles = result.scalars().all()

    assert payload["candidate_bundle_id"]
    assert len(bundles) == 1
    assert bundles[0].status == "pending_review"
    assert bundles[0].prediction_id == payload["prediction_id"]
    assert bundles[0].nodes_payload
    assert bundles[0].edges_payload
    assert payload["simulation_session_id"] == "sim-session-123"
    update_payload = enqueue_mock.await_args.args[1]
    assert update_payload["metadata"]["simulation_session_id"] == "sim-session-123"
    assert "simulation_session_id=sim-session-123" in update_payload["metadata"]["deep_link"]


@pytest.mark.asyncio
async def test_promote_theater_node_to_galaxy_updates_bundle_and_cache(db_session, test_user):
    parent = KnowledgeNode(
        name="Transformer",
        description="现有星图节点",
        importance_level=4,
        is_seed=True,
        sector_weights={"TECH": 70, "WISDOM": 30},
        dominant_sector_code="TECH",
    )
    db_session.add(parent)
    await db_session.commit()
    await db_session.refresh(parent)

    bundle = TheaterCandidateBundle(
        user_id=test_user.id,
        prediction_id="prediction-promote-1",
        topic="LLM",
        target_name="LLM 学习路径",
        target_resolution_mode="hybrid_semantic",
        status="pending_review",
        nodes_payload=[],
        edges_payload=[],
        semantic_matches=[],
        source_metadata={},
    )
    db_session.add(bundle)
    await db_session.commit()
    await db_session.refresh(bundle)

    cached_prediction = {
        "prediction_id": "prediction-promote-1",
        "user_id": str(test_user.id),
        "topic": "LLM",
        "target_name": "LLM 学习路径",
        "target_node_id": None,
        "candidate_bundle_id": str(bundle.id),
        "graph": {
            "nodes": [
                {
                    "id": "free-node-1",
                    "name": "上下文工程",
                    "description": "围绕上下文整理、压缩和注入的能力。",
                    "source_type": "freeform",
                    "mapped_galaxy_node_id": None,
                    "candidate_status": "pending_review",
                    "aliases": ["上下文压缩"],
                    "sector_weights": {},
                },
                {
                    "id": "ref-parent",
                    "name": "Transformer",
                    "description": "现有参考节点",
                    "source_type": "hybrid_reference",
                    "mapped_galaxy_node_id": str(parent.id),
                    "candidate_status": None,
                    "aliases": [],
                    "sector_weights": {"TECH": 70, "WISDOM": 30},
                },
            ],
            "edges": [
                {
                    "id": "free-node-1_ref-parent_part_of",
                    "source_id": "free-node-1",
                    "target_id": "ref-parent",
                    "relation_type": "part_of",
                    "strength": 0.72,
                }
            ],
        },
        "paths": [
            {
                "id": "route-1",
                "steps": [
                    {
                        "node_id": "free-node-1",
                        "node_name": "上下文工程",
                        "mapped_galaxy_node_id": None,
                    }
                ],
            }
        ],
    }
    await cache_service.set(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}prediction-promote-1",
        cached_prediction,
        ttl=PredictionAccuracyTracker.TTL_SECONDS,
    )

    service = PredictionTheaterService(db_session)
    result = await service.promote_node_to_galaxy(
        user_id=test_user.id,
        prediction_id="prediction-promote-1",
        theater_node_id="free-node-1",
    )

    assert result["galaxy_node_id"]
    promoted_node = await db_session.get(KnowledgeNode, UUID(result["galaxy_node_id"]))
    assert promoted_node is not None
    assert promoted_node.name == "上下文工程"

    user_status = await db_session.get(UserNodeStatus, (test_user.id, promoted_node.id))
    assert user_status is not None

    await db_session.refresh(bundle)
    assert bundle.status == "partially_applied"
    assert "free-node-1" in dict(bundle.source_metadata or {}).get("promoted_nodes", {})

    cached = await cache_service.get(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}prediction-promote-1"
    )
    assert cached["graph"]["nodes"][0]["mapped_galaxy_node_id"] == str(promoted_node.id)
    assert cached["paths"][0]["steps"][0]["mapped_galaxy_node_id"] == str(promoted_node.id)


@pytest.mark.asyncio
async def test_promote_theater_node_rolls_back_when_bundle_update_fails(db_session, test_user, monkeypatch):
    parent = KnowledgeNode(
        name="Transformer",
        description="现有星图节点",
        importance_level=4,
        is_seed=True,
        sector_weights={"TECH": 70, "WISDOM": 30},
        dominant_sector_code="TECH",
    )
    db_session.add(parent)
    await db_session.commit()
    await db_session.refresh(parent)

    bundle = TheaterCandidateBundle(
        user_id=test_user.id,
        prediction_id="prediction-promote-rollback",
        topic="LLM",
        target_name="LLM 学习路径",
        target_resolution_mode="hybrid_semantic",
        status="pending_review",
        nodes_payload=[],
        edges_payload=[],
        semantic_matches=[],
        source_metadata={},
    )
    db_session.add(bundle)
    await db_session.commit()

    cached_prediction = {
        "prediction_id": "prediction-promote-rollback",
        "user_id": str(test_user.id),
        "topic": "LLM",
        "target_name": "LLM 学习路径",
        "target_node_id": None,
        "candidate_bundle_id": str(bundle.id),
        "graph": {
            "nodes": [
                {
                    "id": "free-node-rollback",
                    "name": "上下文工程",
                    "description": "围绕上下文整理、压缩和注入的能力。",
                    "source_type": "freeform",
                    "mapped_galaxy_node_id": None,
                    "candidate_status": "pending_review",
                    "aliases": ["上下文压缩"],
                    "sector_weights": {},
                },
                {
                    "id": "ref-parent",
                    "name": "Transformer",
                    "description": "现有参考节点",
                    "source_type": "hybrid_reference",
                    "mapped_galaxy_node_id": str(parent.id),
                    "candidate_status": None,
                    "aliases": [],
                    "sector_weights": {"TECH": 70, "WISDOM": 30},
                },
            ],
            "edges": [
                {
                    "id": "free-node-rollback_ref-parent_part_of",
                    "source_id": "free-node-rollback",
                    "target_id": "ref-parent",
                    "relation_type": "part_of",
                    "strength": 0.72,
                }
            ],
        },
        "paths": [
            {
                "id": "route-1",
                "steps": [
                    {
                        "node_id": "free-node-rollback",
                        "node_name": "上下文工程",
                        "mapped_galaxy_node_id": None,
                    }
                ],
            }
        ],
    }
    await cache_service.set(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}prediction-promote-rollback",
        cached_prediction,
        ttl=PredictionAccuracyTracker.TTL_SECONDS,
    )

    service = PredictionTheaterService(db_session)

    async def fail_record(*args, **kwargs):
        raise RuntimeError("bundle update failed")

    monkeypatch.setattr(service, "_record_candidate_bundle_promotion", fail_record)

    with pytest.raises(RuntimeError, match="bundle update failed"):
        await service.promote_node_to_galaxy(
            user_id=test_user.id,
            prediction_id="prediction-promote-rollback",
            theater_node_id="free-node-rollback",
        )

    node_result = await db_session.execute(
        select(KnowledgeNode).where(KnowledgeNode.name == "上下文工程")
    )
    assert node_result.scalars().all() == []

    cached = await cache_service.get(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}prediction-promote-rollback"
    )
    assert cached["graph"]["nodes"][0]["mapped_galaxy_node_id"] is None


@pytest.mark.asyncio
async def test_theater_api_passes_simulation_session_id(monkeypatch):
    app = _build_test_app()
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db] = lambda: object()
    captured: dict[str, str | None] = {}

    async def fake_generate_prediction(
        self,
        *,
        user_id,
        topic,
        target_node_id=None,
        horizon_days=14,
        simulation_session_id=None,
    ):
        captured["simulation_session_id"] = simulation_session_id
        return {"prediction_id": "prediction-1", "topic": topic}

    monkeypatch.setattr(
        "app.api.v1.theater.PredictionTheaterService.generate_prediction",
        fake_generate_prediction,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/theater/predictions/generate",
            json={
                "topic": "两周掌握特征值",
                "simulation_session_id": "sim-session-123",
            },
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    assert captured["simulation_session_id"] == "sim-session-123"


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

    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14, **kwargs):
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

    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14, **kwargs):
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
                day_label="第 1 天",
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
                day_label="第 1 天",
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
                day_label="第 7 天",
            ),
        ],
    )

    timeline = service._build_timeline(
        [option],
        [{"turn_index": 0, "content": "先补前置。"}],
        available_time_per_day=40,
    )

    assert len(timeline) == 2
    assert timeline[0]["day_index"] == 1
    assert timeline[-1]["day_index"] == 2
    assert timeline[0]["label"] == "第 1 天 · 步骤 1"
    assert timeline[0]["route_id"] == "path_foundation"
    assert timeline[-1]["projected_mastery"] >= timeline[0]["projected_mastery"]
    assert timeline[0]["compare_label"] == "推荐基线"


@pytest.mark.asyncio
async def test_get_accuracy_summary_includes_recent_comparison_pairs(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())
    user_id = uuid4()

    monkeypatch.setattr(
        service,
        "_get_prediction_for_user_or_raise",
        AsyncMock(return_value={"prediction_id": "pred-1"}),
    )
    monkeypatch.setattr(
        service.accuracy,
        "get_summary",
        AsyncMock(
            return_value={
                "prediction_id": "pred-1",
                "predicted_completion_rate": 0.72,
                "actual_completion_rate": 0.55,
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "_recent_comparison_pairs",
        AsyncMock(
            return_value=[
                {
                    "predicted_completion": 0.72,
                    "actual_completion": 0.55,
                    "predicted_mastery": 68.0,
                    "actual_mastery": 52.0,
                    "topic": "线性代数",
                    "date": "2026-03-25",
                }
            ]
        ),
    )

    summary = await service.get_accuracy_summary(user_id=user_id, prediction_id="pred-1")

    assert summary is not None
    assert summary["comparison_pairs"][0]["topic"] == "线性代数"
    assert summary["comparison_pairs"][0]["actual_mastery"] == 52.0


@pytest.mark.asyncio
async def test_simulate_what_if_accepts_multiple_skips(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())
    user_id = uuid4()
    monkeypatch.setattr(
        service,
        "_get_prediction_for_user_or_raise",
        AsyncMock(
            return_value={
                "user_id": str(user_id),
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
        user_id=user_id,
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


@pytest.mark.asyncio
async def test_seed_extractor_onboarding_survives_missing_learning_profile_table():
    db = AsyncMock()
    profile_error = RuntimeError('relation "user_learning_profiles" does not exist')

    user_result = MagicMock()
    user_result.first.return_value = ("小宇", None, 0.55, 0.82)

    plan_result = MagicMock()
    plan_result.all.return_value = [("线性代数", "线代入门")]

    db.execute = AsyncMock(side_effect=[profile_error, user_result, plan_result])
    db.rollback = AsyncMock()

    extractor = SeedExtractor(db=db)

    seeds = await extractor._onboarding_seeds(uuid4())

    assert seeds
    assert any("线性代数" in seed.topic for seed in seeds)
    db.rollback.assert_awaited_once()


# ------------------------------------------------------------------
# P1-C: DB persistence tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_prediction_writes_to_db(db_session, test_user, monkeypatch):
    """_persist_prediction should create a TheaterPrediction row."""
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.SystemUpdateService",
        MagicMock(),
    )
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-persist-1",
    )
    await service._persist_prediction(payload)

    result = await db_session.execute(
        select(TheaterPrediction).where(
            TheaterPrediction.prediction_id == "pred-persist-1"
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.topic == payload["topic"]
    assert row.user_id == test_user.id
    assert row.accuracy_status == "pending_feedback"
    assert row.paths == payload["paths"]


@pytest.mark.asyncio
async def test_get_prediction_or_raise_falls_back_to_db(
    db_session, test_user, monkeypatch
):
    """When Redis misses, _get_prediction_or_raise should read from DB."""
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.SystemUpdateService",
        MagicMock(),
    )
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-fallback-1",
    )
    await service._persist_prediction(payload)
    await db_session.commit()

    # Ensure Redis is empty for this key (the autouse fixture disables Redis)
    result = await service._get_prediction_or_raise("pred-fallback-1")
    assert result["prediction_id"] == "pred-fallback-1"
    assert result["topic"] == payload["topic"]


@pytest.mark.asyncio
async def test_adopt_prediction_updates_db_row(db_session, test_user, monkeypatch):
    """adopt_prediction should set adopted_plan_id on the DB row."""
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-adopt-1",
    )
    await service._persist_prediction(payload)
    await db_session.commit()

    # Set up cached prediction for adopt_prediction to read
    await cache_service.set(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}pred-adopt-1",
        payload,
        ttl=60,
    )
    # Provide a selected route in payload
    payload["paths"] = [
        {
            "id": "route-1",
            "title": "稳扎稳打",
            "summary": "test route",
            "steps": [],
            "daily_minutes": 30,
            "estimated_completion_rate": 0.8,
            "estimated_mastery": 75.0,
        }
    ]
    await cache_service.set(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}pred-adopt-1",
        payload,
        ttl=60,
    )

    # Mock PlanService.create to avoid real plan creation complexity
    from app.models.plan import Plan
    mock_plan = Plan(
        id=uuid4(),
        name="Test Plan",
        type="sprint",
        description="",
        subject="test",
        user_id=test_user.id,
    )
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.PlanService.create",
        AsyncMock(return_value=mock_plan),
    )
    monkeypatch.setattr(service, "_create_week_one_tasks", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "_build_checkpoint_schedule", MagicMock(return_value=[]))
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.CognitiveService",
        MagicMock(),
    )

    await service.adopt_prediction(
        user_id=test_user.id,
        prediction_id="pred-adopt-1",
        route_id="route-1",
    )

    result = await db_session.execute(
        select(TheaterPrediction).where(
            TheaterPrediction.prediction_id == "pred-adopt-1"
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.adopted_plan_id == mock_plan.id
    assert row.adopted_at is not None


@pytest.mark.asyncio
async def test_record_actual_outcome_updates_db_row(
    db_session, test_user, monkeypatch
):
    """record_actual_outcome should set accuracy_status='recorded' on the DB row."""
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-actual-1",
    )
    payload["selected_prediction"] = {
        "estimated_completion_rate": 0.8,
        "estimated_mastery": 75.0,
    }
    await service._persist_prediction(payload)
    await db_session.commit()

    # Cache the prediction so record_actual_outcome can read it
    await cache_service.set(
        f"{PredictionAccuracyTracker.PREDICTION_KEY_PREFIX}pred-actual-1",
        payload,
        ttl=60,
    )

    await service.record_actual_outcome(
        user_id=test_user.id,
        prediction_id="pred-actual-1",
        actual_completion_rate=0.75,
        actual_mastery=70.0,
    )

    result = await db_session.execute(
        select(TheaterPrediction).where(
            TheaterPrediction.prediction_id == "pred-actual-1"
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.accuracy_status == "recorded"
    assert row.accuracy_summary is not None
    assert row.accuracy_summary["actual_completion_rate"] == 0.75


@pytest.mark.asyncio
async def test_get_accuracy_summary_requires_prediction_owner(db_session, test_user):
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-accuracy-owner-1",
    )
    summary = {
        "prediction_id": "pred-accuracy-owner-1",
        "accuracy_score": 0.88,
    }
    await service._persist_prediction(payload)
    await db_session.commit()
    await cache_service.set(
        f"{PredictionAccuracyTracker.SUMMARY_KEY_PREFIX}pred-accuracy-owner-1",
        summary,
        ttl=60,
    )

    owned_summary = await service.get_accuracy_summary(
        user_id=test_user.id,
        prediction_id="pred-accuracy-owner-1",
    )

    assert owned_summary["prediction_id"] == summary["prediction_id"]
    assert owned_summary["accuracy_score"] == summary["accuracy_score"]
    assert owned_summary["comparison_pairs"] == []

    with pytest.raises(AuthorizationError):
        await service.get_accuracy_summary(
            user_id=uuid4(),
            prediction_id="pred-accuracy-owner-1",
        )


@pytest.mark.asyncio
async def test_persist_prediction_failure_keeps_outer_transaction_alive(db_session, test_user):
    """A best-effort prediction write must not roll back outer staged writes."""
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-savepoint-1",
    )

    outer_bundle = TheaterCandidateBundle(
        user_id=test_user.id,
        prediction_id="bundle-savepoint-1",
        topic="外层事务主题",
        target_name="外层事务目标",
        target_resolution_mode="freeform_only",
        status="pending_review",
        nodes_payload=[],
        edges_payload=[],
        semantic_matches=[],
        source_metadata={},
    )
    db_session.add(outer_bundle)

    await service._persist_prediction(payload)
    await service._persist_prediction(payload)
    await db_session.commit()

    persisted_bundle = (
        await db_session.execute(
            select(TheaterCandidateBundle).where(
                TheaterCandidateBundle.prediction_id == "bundle-savepoint-1"
            )
        )
    ).scalar_one_or_none()
    assert persisted_bundle is not None

    persisted_predictions = (
        await db_session.execute(
            select(TheaterPrediction).where(
                TheaterPrediction.prediction_id == "pred-savepoint-1"
            )
        )
    ).scalars().all()
    assert len(persisted_predictions) == 1


@pytest.mark.asyncio
async def test_update_prediction_failure_keeps_outer_transaction_alive(db_session, test_user):
    """A failed best-effort update must not roll back caller-owned writes."""
    service = PredictionTheaterService(db_session)
    payload = await _generate_minimal_prediction_payload(
        service=service,
        user_id=test_user.id,
        prediction_id="pred-savepoint-update-1",
    )
    await service._persist_prediction(payload)
    await db_session.commit()

    outer_bundle = TheaterCandidateBundle(
        user_id=test_user.id,
        prediction_id="bundle-savepoint-2",
        topic="外层事务主题",
        target_name="外层事务目标",
        target_resolution_mode="freeform_only",
        status="pending_review",
        nodes_payload=[],
        edges_payload=[],
        semantic_matches=[],
        source_metadata={},
    )
    db_session.add(outer_bundle)

    await service._update_prediction_db(
        user_id=test_user.id,
        prediction_id="pred-savepoint-update-1",
        updates={"topic": None},
    )
    await db_session.commit()

    persisted_bundle = (
        await db_session.execute(
            select(TheaterCandidateBundle).where(
                TheaterCandidateBundle.prediction_id == "bundle-savepoint-2"
            )
        )
    ).scalar_one_or_none()
    assert persisted_bundle is not None

    persisted_prediction = (
        await db_session.execute(
            select(TheaterPrediction).where(
                TheaterPrediction.prediction_id == "pred-savepoint-update-1"
            )
        )
    ).scalar_one()
    assert persisted_prediction.topic == "测试主题"


async def _generate_minimal_prediction_payload(
    *,
    service: PredictionTheaterService,
    user_id: UUID,
    prediction_id: str,
) -> dict[str, Any]:
    """Helper to build a minimal prediction payload for testing."""
    from datetime import date, timedelta

    return {
        "prediction_id": prediction_id,
        "user_id": str(user_id),
        "topic": "测试主题",
        "simulation_session_id": None,
        "target_node_id": None,
        "target_name": "测试目标",
        "candidate_bundle_id": None,
        "horizon_days": 14,
        "generated_at": _utcnow().isoformat(),
        "paths": [
            {
                "id": "route-1",
                "title": "稳扎稳打",
                "summary": "test",
                "steps": [],
                "estimated_completion_rate": 0.8,
                "estimated_mastery": 75.0,
            }
        ],
        "discussion_turns": [],
        "timeline": [],
        "selected_prediction": {},
        "recommended_route_id": "route-1",
        "target_resolution_mode": "freeform_only",
        "accuracy_tracking": {
            "status": "pending_feedback",
            "due_on": (date.today() + timedelta(days=7)).isoformat(),
            "summary_hint": "test",
        },
        "routing_notes": {"patterns": [], "recommended_entry": "稳扎稳打"},
        "preview_mode": False,
        "graph": {"nodes": [], "edges": []},
    }
