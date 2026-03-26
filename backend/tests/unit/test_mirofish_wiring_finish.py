from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.plan import Plan, PlanType
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.execution_engine import ExecutionEngineMixin
from app.orchestration.orchestrator import ChatOrchestrator
from app.services.report.learning_report_agent import LearningReportAgent
from app.services.theater.prediction_theater_service import TheaterNodeAccessError
from app.services.simulation.seed_extractor import SimulationSeed
from app.services.theater.prediction_theater_service import PredictionTheaterService
from app.tools.simulation_tool import QuickSimulationParams, QuickSimulationTool
from app.tools.theater_tool import LaunchPredictionParams, LaunchPredictionTool


class _DummyContextBuilder(ContextBuilderMixin):
    pass


class _DummyExecutionEngine(ExecutionEngineMixin):
    pass


@pytest.mark.asyncio
async def test_launch_prediction_tool_returns_preview_payload(monkeypatch):
    prediction_id = str(uuid4())
    target_node_id = str(uuid4())

    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14):
        assert topic == "两周掌握特征值"
        return {
            "prediction_id": prediction_id,
            "target_node_id": target_node_id,
            "paths": [
                {
                    "id": "route-a",
                    "title": "稳扎稳打",
                    "estimated_mastery": 78,
                    "estimated_completion_rate": 0.92,
                },
                {
                    "id": "route-b",
                    "title": "重点突破",
                    "estimated_mastery": 83,
                    "estimated_completion_rate": 0.71,
                },
            ],
        }

    monkeypatch.setattr(
        "app.tools.theater_tool.PredictionTheaterService.generate_prediction",
        fake_generate_prediction,
    )

    result = await LaunchPredictionTool().execute(
        LaunchPredictionParams(
            topic="两周掌握特征值",
            source_chat_session_id="chat-123",
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-1",
    )

    assert result.success is True
    assert result.data is not None
    assert result.data["prediction_id"] == prediction_id
    assert result.data["open_theater"] is True
    assert result.data["source_chat_session_id"] == "chat-123"
    assert result.data["paths"][0]["title"] == "稳扎稳打"
    assert "source_chat_session_id=chat-123" in result.data["deep_link"]


@pytest.mark.asyncio
async def test_quick_simulation_tool_returns_preview_payload(monkeypatch):
    fake_session = SimpleNamespace(
        id="sim-001",
        scenario_key="study_group",
        topic="矩阵特征值",
        participants=["优等生", "提问者", "主持人"],
        rounds=[
            {"round": 1, "summary": "先梳理前置概念"},
            {"round": 2, "summary": "对比特征值与行列式"},
            {"round": 3, "summary": "总结最易错点"},
            {"round": 4, "summary": "这一轮不会返回"},
        ],
        insight_summary="先补行列式，再学特征值更稳。",
    )

    async def fake_run(self, *, topic, scenario_key, user_id):
        assert topic == "矩阵特征值"
        assert scenario_key == "study_group"
        return fake_session

    monkeypatch.setattr(
        "app.tools.simulation_tool.SimulationEngine.run",
        fake_run,
    )

    result = await QuickSimulationTool().execute(
        QuickSimulationParams(
            scenario_key="study_group",
            seed_topic="矩阵特征值",
            source_chat_session_id="chat-456",
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-2",
    )

    assert result.success is True
    assert result.data is not None
    assert result.data["session_id"] == "sim-001"
    assert result.data["open_simulation"] is True
    assert len(result.data["round_preview"]) == 3
    assert result.data["participants"] == ["优等生", "提问者", "主持人"]
    assert "scenario_key=study_group" in result.data["deep_link"]


@pytest.mark.asyncio
async def test_launch_prediction_tool_rejects_invalid_target_node_uuid():
    result = await LaunchPredictionTool().execute(
        LaunchPredictionParams(
            topic="两周掌握特征值",
            target_node_id="not-a-uuid",
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-invalid-node",
    )

    assert result.success is False
    assert result.error_type == "invalid_target_node_id"
    assert result.error_message == "目标知识节点格式不正确"


@pytest.mark.asyncio
async def test_launch_prediction_tool_rejects_inaccessible_target_node(monkeypatch):
    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14):
        raise TheaterNodeAccessError()

    monkeypatch.setattr(
        "app.tools.theater_tool.PredictionTheaterService.generate_prediction",
        fake_generate_prediction,
    )

    result = await LaunchPredictionTool().execute(
        LaunchPredictionParams(
            topic="两周掌握特征值",
            target_node_id=str(uuid4()),
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-no-access",
    )

    assert result.success is False
    assert result.error_type == "target_node_not_accessible"
    assert result.error_message == "未找到可访问的知识节点"


@pytest.mark.asyncio
async def test_quick_simulation_tool_rejects_invalid_scenario():
    result = await QuickSimulationTool().execute(
        QuickSimulationParams(
            scenario_key="made_up_scenario",
            seed_topic="矩阵特征值",
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-invalid-scenario",
    )

    assert result.success is False
    assert result.error_type == "invalid_simulation_scenario"
    assert "Unsupported simulation scenario" in (result.error_message or "")


@pytest.mark.asyncio
async def test_build_learning_gaps_summary_uses_cached_seeds(monkeypatch):
    builder = _DummyContextBuilder()
    user_id = str(uuid4())

    async def fake_get_cached_or_generate(self, target_user_id, *, scenario_key=None, limit=3, force_refresh=False):
        assert str(target_user_id) == user_id
        assert scenario_key == "chat_context"
        assert limit == 3
        return [
            SimulationSeed(
                topic="特征值",
                context="图谱显示前置依赖缺口",
                tension_point="总把特征多项式和行列式展开混淆",
                source_type="galaxy",
                source_ids=["node-a"],
                relevance_score=0.94,
                suggested_scenario="knowledge_debate",
                suggested_experts=["星图导航"],
            ),
            SimulationSeed(
                topic="向量点乘",
                context="错题本集中出现几何意义误判",
                tension_point="代数运算会做，但几何解释不稳定",
                source_type="error_book",
                source_ids=["error-a"],
                relevance_score=0.88,
                suggested_scenario="study_group",
                suggested_experts=["数学专家"],
            ),
        ]

    monkeypatch.setattr(
        "app.orchestration.context_builder.SeedExtractor.get_cached_or_generate",
        fake_get_cached_or_generate,
    )

    summary = await builder._build_learning_gaps_summary(user_id, AsyncMock())

    assert summary is not None
    assert "特征值: 总把特征多项式和行列式展开混淆" in summary
    assert "向量点乘: 代数运算会做，但几何解释不稳定" in summary
    assert len(summary) <= 300


@pytest.mark.asyncio
async def test_build_learning_gaps_summary_gracefully_handles_seed_failures(monkeypatch):
    builder = _DummyContextBuilder()

    async def fake_get_cached_or_generate(self, target_user_id, *, scenario_key=None, limit=3, force_refresh=False):
        raise RuntimeError("cache offline")

    monkeypatch.setattr(
        "app.orchestration.context_builder.SeedExtractor.get_cached_or_generate",
        fake_get_cached_or_generate,
    )

    summary = await builder._build_learning_gaps_summary(str(uuid4()), AsyncMock())

    assert summary is None


@pytest.mark.asyncio
async def test_roundtable_graph_updates_create_weak_edge_only_for_explicit_references(monkeypatch):
    engine = _DummyExecutionEngine()
    node_a = str(uuid4())
    node_b = str(uuid4())
    engagement_calls: list[tuple[str, int]] = []
    relation_calls: list[dict[str, object]] = []

    class FakeGraphStructureEvolutionService:
        def __init__(self, db):
            self.db = db

        async def record_engagement(self, *, user_id, node_id, minutes=0):
            engagement_calls.append((str(node_id), minutes))

        async def tag_node_signal(self, node_id, signal_tag, *, active):
            return True

        async def upsert_relation(self, **kwargs):
            relation_calls.append(kwargs)

    monkeypatch.setattr(
        "app.orchestration.execution_engine.GraphStructureEvolutionService",
        FakeGraphStructureEvolutionService,
    )

    await engine._write_roundtable_graph_updates(
        active_db=AsyncMock(),
        user_id=str(uuid4()),
        turns=[
            {
                "references": [node_a, node_b],
                "content": "这两个概念存在明确的前置依赖。",
            }
        ],
        executable_plan=SimpleNamespace(context={}),
        state=SimpleNamespace(context_data={}),
    )

    assert engagement_calls == [(node_a, 1), (node_b, 1)]
    assert len(relation_calls) == 1
    assert relation_calls[0]["relation_type"] == "prerequisite"
    assert relation_calls[0]["default_strength"] == 0.18


@pytest.mark.asyncio
async def test_roundtable_graph_updates_do_not_create_weak_edge_from_context_only(monkeypatch):
    engine = _DummyExecutionEngine()
    node_a = str(uuid4())
    node_b = str(uuid4())
    relation_calls: list[dict[str, object]] = []

    class FakeGraphStructureEvolutionService:
        def __init__(self, db):
            self.db = db

        async def record_engagement(self, *, user_id, node_id, minutes=0):
            return None

        async def tag_node_signal(self, node_id, signal_tag, *, active):
            return True

        async def upsert_relation(self, **kwargs):
            relation_calls.append(kwargs)

    monkeypatch.setattr(
        "app.orchestration.execution_engine.GraphStructureEvolutionService",
        FakeGraphStructureEvolutionService,
    )

    await engine._write_roundtable_graph_updates(
        active_db=AsyncMock(),
        user_id=str(uuid4()),
        turns=[
            {
                "references": [],
                "content": "虽然这里也提到了前置依赖，但并没有明确回合引用。",
            }
        ],
        executable_plan=SimpleNamespace(context={}),
        state=SimpleNamespace(
            context_data={
                "plan_context": {
                    "focus_node_ids": [node_a, node_b],
                }
            }
        ),
    )

    assert relation_calls == []


@pytest.mark.asyncio
async def test_adopt_prediction_enqueues_update_and_writes_back_to_chat(db_session, test_user, monkeypatch):
    session = ChatSession(user_id=test_user.id)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    service = PredictionTheaterService(db_session)
    prediction_id = str(uuid4())
    route_id = "route-steady"
    target_node_id = str(uuid4())
    plan_id = uuid4()
    fake_plan = Plan(
        id=plan_id,
        user_id=test_user.id,
        name="特征值 · 稳扎稳打",
        type=PlanType.SPRINT,
        description="按推演路径推进",
        subject="特征值",
        target_date=date.today(),
        daily_available_minutes=40,
        total_estimated_hours=6.0,
    )

    monkeypatch.setattr(
        service,
        "_get_prediction_or_raise",
        AsyncMock(
            return_value={
                "prediction_id": prediction_id,
                "topic": "特征值",
                "target_name": "特征值",
                "target_node_id": target_node_id,
                "horizon_days": 14,
                "paths": [
                    {
                        "id": route_id,
                        "title": "稳扎稳打",
                        "summary": "先补前置，再做练习。",
                        "daily_minutes": 40,
                        "estimated_mastery": 78,
                        "estimated_completion_rate": 0.9,
                        "risks": ["第二周任务密集"],
                        "steps": [
                            {
                                "node_id": target_node_id,
                                "node_name": "特征值",
                                "risk_level": "high",
                                "estimated_minutes": 30,
                            }
                        ],
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.PlanService.create",
        AsyncMock(return_value=fake_plan),
    )
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.cache_service.set",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.CognitiveService.create_fragment",
        AsyncMock(return_value={"ok": True}),
    )
    service.structure.tag_node_signal = AsyncMock(return_value=True)
    enqueue_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.SystemUpdateService.enqueue",
        enqueue_mock,
    )

    result = await service.adopt_prediction(
        user_id=test_user.id,
        prediction_id=prediction_id,
        route_id=route_id,
        source_chat_session_id=str(session.id),
    )

    persisted_messages = (
        await db_session.execute(select(ChatMessage).where(ChatMessage.session_id == session.id))
    ).scalars().all()

    assert result["plan_id"] == str(plan_id)
    assert any(message.role == MessageRole.SYSTEM for message in persisted_messages)
    assert any("已根据推演创建计划" in message.content for message in persisted_messages)
    update_payload = enqueue_mock.await_args.args[1]
    assert update_payload["type"] == "theater_route_adopted"
    assert update_payload["metadata"]["plan_id"] == str(plan_id)
    assert update_payload["metadata"]["route_id"] == route_id


@pytest.mark.asyncio
async def test_learning_report_generate_enqueues_ready_update(monkeypatch):
    agent = LearningReportAgent(db=AsyncMock())
    user_id = uuid4()

    monkeypatch.setattr(
        agent.tools,
        "query_mastery_scores",
        AsyncMock(return_value=[{"node_name": "特征值", "score": 0.72}]),
    )
    monkeypatch.setattr(
        agent.tools,
        "query_error_patterns",
        AsyncMock(return_value=[{"pattern_name": "符号方向混淆"}]),
    )
    monkeypatch.setattr(
        agent.tools,
        "query_study_timeline",
        AsyncMock(return_value=[{"date": "2026-03-25", "minutes": 40}]),
    )
    monkeypatch.setattr(
        agent.tools,
        "interview_learner",
        AsyncMock(return_value={"summary": "最近更想要清晰的步骤拆解。"}),
    )
    monkeypatch.setattr(agent, "_compose_markdown", AsyncMock(return_value="# 学习分析报告"))
    monkeypatch.setattr(
        agent,
        "_reflect_on_markdown",
        AsyncMock(
            return_value={
                "needs_revision": False,
                "missing_sections": [],
                "focus_areas": [],
                "revision_brief": "",
                "query_expansion": [],
            }
        ),
    )
    monkeypatch.setattr(agent, "_expand_context", AsyncMock(return_value={}))
    agent.logger.log_jsonl = lambda *args, **kwargs: None
    agent.logger.log_text = lambda *args, **kwargs: None
    enqueue_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.report.learning_report_agent.SystemUpdateService.enqueue",
        enqueue_mock,
    )

    payload = await agent.generate_report(user_id)

    assert payload["markdown"] == "# 学习分析报告"
    update_payload = enqueue_mock.await_args.args[1]
    assert update_payload["type"] == "learning_report_ready"
    assert update_payload["metadata"]["report_payload"]["report_id"] == payload["report_id"]


def test_infer_bridge_tool_names_matches_prediction_and_simulation_intents():
    orchestrator = object.__new__(ChatOrchestrator)

    prediction_tools = orchestrator._infer_bridge_tool_names("如果我两周学完特征值会怎样？")
    simulation_tools = orchestrator._infer_bridge_tool_names("帮我模拟一个学习小组讨论这个概念")
    plain_tools = orchestrator._infer_bridge_tool_names("解释一下什么是特征值")

    assert "launch_prediction" in prediction_tools
    assert "run_quick_simulation" in simulation_tools
    assert plain_tools == []
