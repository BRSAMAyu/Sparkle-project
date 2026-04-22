from __future__ import annotations

from datetime import UTC, date, datetime
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.cache import cache_service
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.plan import Plan, PlanType
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.execution_engine import ExecutionEngineMixin
from app.orchestration.orchestrator import ChatOrchestrator
from app.tools.base import ToolResult
from app.tools.report_tool import GenerateLearningReportParams, GenerateLearningReportTool
from app.services.report.learning_report_agent import LearningReportAgent
from app.services.simulation.simulation_engine import ModeratorDecision, SimulationEngine
from app.services.theater.prediction_theater_service import TheaterNodeAccessError
from app.services.simulation.seed_extractor import SeedExtractor, SimulationSeed
from app.services.theater.prediction_theater_service import PredictionTheaterService
from app.tools.simulation_tool import QuickSimulationParams, QuickSimulationTool
from app.tools.theater_tool import LaunchPredictionParams, LaunchPredictionTool


class _DummyContextBuilder(ContextBuilderMixin):
    pass


class _DummyExecutionEngine(ExecutionEngineMixin):
    pass


@pytest.fixture(autouse=True)
def _reset_report_cache():
    previous_redis = cache_service.redis
    previous_local_cache = dict(cache_service._local_cache)
    cache_service.redis = None
    cache_service._local_cache.clear()
    yield
    cache_service._local_cache.clear()
    cache_service._local_cache.update(previous_local_cache)
    cache_service.redis = previous_redis


def test_context_builder_preserves_seed_library_toggle_flag():
    builder = _DummyContextBuilder()

    merged = builder._merge_user_contexts(
        {"preferences": {}},
        {"seed_library_enabled": False},
    )

    assert merged["seed_library_enabled"] is False


@pytest.mark.asyncio
async def test_launch_prediction_tool_returns_preview_payload(monkeypatch):
    prediction_id = str(uuid4())
    target_node_id = str(uuid4())

    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14, preview_mode=False):
        assert topic == "两周掌握特征值"
        assert preview_mode is True
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
    assert result.data["target_name"] == "两周掌握特征值"
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

    async def fake_preview(self, *, topic, scenario_key, user_id, user_context=None, max_rounds=3):
        assert topic == "矩阵特征值"
        assert scenario_key == "study_group"
        assert max_rounds == 3
        return fake_session

    monkeypatch.setattr(
        "app.tools.simulation_tool.SimulationEngine.preview",
        fake_preview,
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
    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14, preview_mode=False):
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
async def test_quick_simulation_tool_uses_seed_topic_for_generic_prompt(monkeypatch):
    fake_session = SimpleNamespace(
        id="sim-002",
        scenario_key="study_group",
        topic="特征值",
        participants=["主持人"],
        rounds=[{"round": 1, "summary": "先补前置概念"}],
        insight_summary="先补前置概念。",
    )

    async def fake_preview(self, *, topic, scenario_key, user_id, user_context=None, max_rounds=3):
        assert topic == "特征值"
        assert scenario_key == "study_group"
        assert max_rounds == 3
        return fake_session

    async def fake_get_cached_or_generate(
        self,
        user_id,
        *,
        scenario_key=None,
        limit=3,
        force_refresh=False,
        allow_llm_refine=True,
    ):
        assert scenario_key == "study_group"
        assert limit == 1
        assert allow_llm_refine is False
        return [
            SimulationSeed(
                topic="特征值",
                context="最近卡在前置概念",
                tension_point="总把行列式和特征值混淆",
                source_type="galaxy",
                source_ids=["node-1"],
                relevance_score=0.92,
                suggested_scenario="study_group",
                suggested_experts=["数学专家"],
            )
        ]

    monkeypatch.setattr(
        "app.tools.simulation_tool.SimulationEngine.preview",
        fake_preview,
    )
    monkeypatch.setattr(
        "app.tools.simulation_tool.SeedExtractor.get_cached_or_generate",
        fake_get_cached_or_generate,
    )

    result = await QuickSimulationTool().execute(
        QuickSimulationParams(
            scenario_key="study_group",
            seed_topic="我想模拟一下学习场景",
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-generic-simulation",
    )

    assert result.success is True
    assert result.data is not None
    assert result.data["topic"] == "特征值"


@pytest.mark.asyncio
async def test_generate_learning_report_tool_returns_preview_payload(monkeypatch):
    async def fake_generate_report(self, user_id, section_limit=5, *, delivery_mode="full", trigger_source="api"):
        assert delivery_mode == "chat_bridge"
        assert trigger_source == "chat"
        assert section_limit == 4
        return {
            "report_id": "report-001",
            "quality_mode": "fast_balanced",
            "deep_link": "/learning-report",
            "report_preview": {
                "report_id": "report-001",
                "markdown": "# 学习分析报告\n\n## 行动计划\n- 先补 Python 基础语法",
                "sections": ["Executive Summary", "行动计划"],
                "mastery": [{"node_name": "Python 基础语法", "mastery_score": 58}],
                "summary": "优先关注 Python 基础语法，并结合最近学习记录补一轮针对性练习。",
            },
        }

    monkeypatch.setattr(
        "app.tools.report_tool.LearningReportAgent.generate_report",
        fake_generate_report,
    )

    result = await GenerateLearningReportTool().execute(
        GenerateLearningReportParams(
            section_limit=4,
            delivery_mode="chat_bridge",
            source_chat_session_id="chat-789",
        ),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tool-3",
    )

    assert result.success is True
    assert result.data is not None
    assert result.data["report_id"] == "report-001"
    assert result.data["open_report"] is True
    assert result.data["report_preview"]["mastery"][0]["node_name"] == "Python 基础语法"
    assert result.data["deep_link"] == "/learning-report?report_id=report-001&source_chat_session_id=chat-789"


@pytest.mark.asyncio
async def test_learning_report_agent_reuses_cached_payload(monkeypatch):
    agent = LearningReportAgent(db=object())
    user_id = uuid4()
    compose_calls = {"count": 0}

    monkeypatch.setattr(
        agent.tools,
        "query_mastery_scores",
        AsyncMock(return_value=[{"node_name": "矩阵", "mastery_score": 61.0}]),
    )
    monkeypatch.setattr(agent.tools, "query_error_patterns", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        agent.tools,
        "query_study_timeline",
        AsyncMock(
            return_value=[
                {
                    "node_name": "矩阵",
                    "study_minutes": 35,
                    "mastery_delta": 4.0,
                    "created_at": "2026-03-27T08:00:00",
                }
            ],
        ),
    )
    monkeypatch.setattr(agent.tools, "interview_learner", AsyncMock(return_value={}))
    monkeypatch.setattr(
        agent.tools,
        "infer_learning_state_from_chat",
        AsyncMock(return_value={"topics": ["矩阵"]}),
    )
    monkeypatch.setattr(agent, "_build_starter_focus", AsyncMock(return_value=[]))

    async def fake_compose_markdown(**kwargs):
        del kwargs
        compose_calls["count"] += 1
        return "# 学习分析报告\n\n- 缓存命中测试"

    monkeypatch.setattr(agent, "_compose_markdown", fake_compose_markdown)
    monkeypatch.setattr(agent, "_should_run_reflection", lambda **kwargs: False)
    monkeypatch.setattr(agent, "_push_report_notification", AsyncMock())
    monkeypatch.setattr(
        "app.services.report.learning_report_agent.SystemUpdateService.enqueue",
        AsyncMock(return_value=True),
    )

    first = await agent.generate_report(
        user_id,
        delivery_mode="full",
        trigger_source="api",
    )
    second = await agent.generate_report(
        user_id,
        delivery_mode="full",
        trigger_source="api",
    )

    assert compose_calls["count"] == 1
    assert first["report_preview"] == second["report_preview"]


async def test_simulation_engine_builds_interaction_point():
    engine = SimulationEngine()
    participants = [
        {"name": "优等生"},
        {"name": "提问者"},
        {"name": "主持人"},
    ]
    participant_objects = engine._build_agent_participants(
        participants,
        scenario_key="knowledge_debate",
    )
    rounds = [
        {
            "round": 1,
            "speaker": "优等生",
            "message": "我认为先理解几何意义，后面推导会更稳。",
        },
        {
            "round": 2,
            "speaker": "提问者",
            "message": "如果遇到计算题，还是容易直接陷入公式。",
        },
    ]
    moderator_payload = engine._fallback_moderator_decision(
        topic="特征值与特征向量",
        scenario_key="knowledge_debate",
        rounds=rounds,
        participants=participant_objects,
        planned_round_count=4,
    )
    interaction = await engine._build_user_interaction_point(
        topic="特征值与特征向量",
        participants=participant_objects,
        rounds=rounds,
        moderator_decision=ModeratorDecision(
            speaker=str(moderator_payload["speaker"]),
            reply_target=str(moderator_payload["reply_target"]),
            turn_goal=str(moderator_payload["turn_goal"]),
            real_time_insight=str(moderator_payload["real_time_insight"]),
            round_target=int(moderator_payload["round_target"]),
            should_pause_for_user=True,
            should_end=True,
            interaction_type=str(moderator_payload["interaction_type"]),
            interaction_prompt="围绕“特征值与特征向量”已经形成两种走法。现在轮到你：你会更支持哪一边，还是给出第三种学习策略？",
            interaction_options=list(moderator_payload["interaction_options"]),
            suggested_replies=list(moderator_payload["suggested_replies"]),
        ),
        anchor_material="特征值与特征向量的定义与一个矩阵例子",
    )

    assert interaction is not None
    assert len(interaction.suggested_replies) == 3
    assert "你会更支持哪一边" in interaction.prompt


@pytest.mark.asyncio
async def test_simulation_engine_persists_gap_events(monkeypatch):
    engine = SimulationEngine()
    publish = AsyncMock(return_value="evt-1")
    monkeypatch.setattr(engine.event_bus, "publish", publish)

    session = engine._session_from_payload(
        {
            "id": "session-gap-1",
            "scenario_key": "study_group",
            "state": "COMPLETED",
            "topic": "特征值与特征向量",
            "participants": [],
            "rounds": [],
            "insight_summary": json.dumps(
                {
                    "knowledge_gaps_revealed": [
                        "把特征值和对角线元素直接等同",
                        "不知道特征向量为什么表示不变方向",
                    ]
                },
                ensure_ascii=False,
            ),
        },
        fallback_topic="特征值与特征向量",
        fallback_scenario="study_group",
    )

    await engine._persist_simulation_insights(session=session, user_id=str(uuid4()))

    assert publish.await_count == 2
    first_call = publish.await_args_list[0]
    assert first_call.args[0] == "SimulationGapRevealed"
    assert first_call.args[1]["gap_description"] == "把特征值和对角线元素直接等同"


@pytest.mark.asyncio
async def test_simulation_engine_summarize_rounds_returns_structured_payload(monkeypatch):
    engine = SimulationEngine()
    monkeypatch.setattr(
        "app.services.simulation.simulation_engine.analysis_llm.json_call",
        AsyncMock(
            return_value={
                "key_arguments": ["先区分特征值和对角线元素。"],
                "unresolved_disagreements": ["几何直觉是否要先于计算练习。"],
                "user_contributions": "用户在第 2 轮提出了几何意义的疑问。",
                "knowledge_gaps_revealed": ["不知道特征向量为什么表示不变方向。"],
                "suggested_next_steps": ["先用一个 2x2 矩阵验证几何解释。"],
            }
        ),
    )

    summary = await engine._summarize_rounds(
        "特征值与特征向量",
        [
            {"round": 1, "speaker": "优等生", "message": "先澄清对角化和特征值的关系。"},
            {"round": 2, "speaker": "你", "message": "我还是不懂特征向量为什么表示不变方向。"},
        ],
    )

    payload = json.loads(summary)
    assert payload["key_arguments"]
    assert payload["knowledge_gaps_revealed"] == ["不知道特征向量为什么表示不变方向。"]
    assert "用户在第 2 轮" in payload["user_contributions"]


@pytest.mark.asyncio
async def test_generate_agent_round_references_anchor_material(monkeypatch):
    engine = SimulationEngine()
    monkeypatch.setattr(
        "app.services.simulation.simulation_engine.analysis_llm.json_call",
        AsyncMock(
            return_value={
                "message": "题目里是 5kg 和 10N，不可能直接得出 50 m/s²。先回到 F=ma，看单位怎么约束计算。",
                "reply_to_speaker": "",
                "turn_goal": "probe",
            }
        ),
    )

    round_payload = await engine._generate_agent_round(
        topic="牛顿第二定律",
        scenario_key="error_diagnosis",
        participants=[
            SimpleNamespace(
                name="错因教练",
                role_hint="专门拆错误思路",
                persona={},
                stance="challenging",
                source="template",
                strategy="using_misconception",
                response_policy="reply_when_addressed",
                memory=[],
                context_anchor="学生答：50 m/s²",
            )
        ],
        rounds=[],
        moderator_decision=ModeratorDecision(
            speaker="错因教练",
            reply_target="",
            turn_goal="probe",
            real_time_insight="先检查用户是否把力和加速度直接相乘。",
            round_target=3,
        ),
        facilitation_style="practical",
        anchor_material="一个 5kg 的物体受到 10N 的力，求加速度。学生答：50 m/s²",
        learning_objective="识别错因",
    )

    assert any(keyword in round_payload["message"] for keyword in ["5kg", "10N", "50 m/s²", "F=ma"])


@pytest.mark.asyncio
async def test_seed_extractor_builds_simulation_gap_seeds(monkeypatch):
    extractor = SeedExtractor(db=AsyncMock())
    user_id = uuid4()

    monkeypatch.setattr(
        "app.services.simulation.seed_extractor.SystemUpdateService.list_updates",
        AsyncMock(
            return_value=[
                {
                    "type": "simulation_session_ready",
                    "metadata": {
                        "session_payload": {
                            "id": "sim-1",
                            "topic": "线性代数",
                            "insight_summary": json.dumps(
                                {
                                    "knowledge_gaps_revealed": [
                                        "不知道特征向量为什么表示不变方向",
                                    ]
                                },
                                ensure_ascii=False,
                            ),
                        }
                    },
                }
            ]
        ),
    )
    monkeypatch.setattr(extractor, "_resolved_simulation_gaps", AsyncMock(return_value=set()))

    seeds = await extractor._simulation_gap_seeds(user_id)

    assert len(seeds) == 1
    assert seeds[0].source_type == "simulation_gap"
    assert "上次关于" in seeds[0].context
    assert seeds[0].topic == "不知道特征向量为什么表示不变方向"


@pytest.mark.asyncio
async def test_build_learning_gaps_summary_uses_cached_seeds(monkeypatch):
    builder = _DummyContextBuilder()
    user_id = str(uuid4())

    async def fake_get_cached_or_generate(
        self,
        target_user_id,
        *,
        scenario_key=None,
        limit=3,
        force_refresh=False,
        allow_llm_refine=True,
    ):
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

    async def fake_get_cached_or_generate(
        self,
        target_user_id,
        *,
        scenario_key=None,
        limit=3,
        force_refresh=False,
        allow_llm_refine=True,
    ):
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
        "_get_prediction_for_user_or_raise",
        AsyncMock(
            return_value={
                "prediction_id": prediction_id,
                "user_id": str(test_user.id),
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
    created_task_counter = {"value": 0}

    async def fake_task_create(db, obj_in, user_id):
        del db, user_id
        created_task_counter["value"] += 1
        return SimpleNamespace(
            id=uuid4(),
            title=obj_in.title,
            type=obj_in.type,
        )

    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.TaskService.create",
        AsyncMock(side_effect=fake_task_create),
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
    assert len(result["created_tasks"]) >= 3
    assert len(result["checkpoint_dates"]) >= 1
    assert created_task_counter["value"] >= len(result["created_tasks"])
    assert any(message.role == MessageRole.SYSTEM for message in persisted_messages)
    assert any("已根据推演创建计划" in message.content for message in persisted_messages)
    update_payload = enqueue_mock.await_args.args[1]
    assert update_payload["type"] == "theater_route_adopted"
    assert update_payload["metadata"]["plan_id"] == str(plan_id)
    assert update_payload["metadata"]["route_id"] == route_id
    assert len(update_payload["metadata"]["created_tasks"]) >= 3


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
    monkeypatch.setattr(
        agent.tools,
        "infer_learning_state_from_chat",
        AsyncMock(return_value={}),
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
    assert payload["diagnosis_cards"]
    assert payload["action_cards"]
    assert payload["trend_overview"]["headline"]
    assert payload["trigger_summary"]["title"]
    update_payload = enqueue_mock.await_args.args[1]
    assert update_payload["type"] == "learning_report_ready"
    assert update_payload["metadata"]["report_payload"]["report_id"] == payload["report_id"]
    assert update_payload["title"] == payload["trigger_summary"]["title"]


def test_learning_report_preview_uses_pattern_summary_when_mastery_missing():
    agent = LearningReportAgent(db=AsyncMock())

    preview = agent._build_report_preview(
        {
            "report_id": "report-1",
            "sections": ["Executive Summary", "行动计划"],
            "mastery": [],
            "patterns": [
                {
                    "pattern_name": "夜间能量错配循环",
                    "solution_text": "把最费脑的任务前移到你最清醒的两个小时。",
                }
            ],
            "markdown": "# 学习分析报告",
        }
    )

    assert preview["summary"].startswith("当前最影响推进节奏的是 夜间能量错配循环")
    assert preview["highlights"] == ["夜间能量错配循环"]
    assert preview["action_cards"] == []


@pytest.mark.asyncio
async def test_learning_report_generate_uses_starter_focus_for_cold_start(monkeypatch):
    agent = LearningReportAgent(db=AsyncMock())
    user_id = uuid4()

    monkeypatch.setattr(agent.tools, "query_mastery_scores", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent.tools, "query_error_patterns", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent.tools, "query_study_timeline", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        agent.tools,
        "interview_learner",
        AsyncMock(return_value={"learner_voice": "先建立连续三次学习记录。"}),
    )
    monkeypatch.setattr(
        agent.tools,
        "infer_learning_state_from_chat",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "app.services.report.learning_report_agent.SeedExtractor.extract_seeds",
        AsyncMock(
            return_value=[
                SimulationSeed(
                    topic="把 特征值 变成第一轮可执行练习",
                    context="适合先从定义与几何意义切入。",
                    tension_point="先说清第一步。",
                    source_type="starter_graph",
                    source_ids=["node-1"],
                    relevance_score=0.64,
                    suggested_scenario="study_group",
                    suggested_experts=["学伴"],
                )
            ]
        ),
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
    monkeypatch.setattr(
        "app.services.report.learning_report_agent.SystemUpdateService.enqueue",
        AsyncMock(return_value=True),
    )

    payload = await agent.generate_report(user_id)

    assert payload["starter_focus"][0]["topic"] == "把 特征值 变成第一轮可执行练习"
    assert payload["trigger_summary"]["mode"] == "baseline_ready"
    assert payload["trigger_summary"]["data_status"] == "insufficient"
    assert payload["mastery"] == []
    assert payload["patterns"] == []
    assert payload["trend_overview"]["status"] == "no_data"
    assert payload["action_cards"][0]["id"] == "start-first-learning-task"
    assert all("/theater" not in card["deep_link"] for card in payload["action_cards"])
    assert all("/simulation" not in card["deep_link"] for card in payload["action_cards"])


@pytest.mark.asyncio
async def test_learning_report_uses_actual_mastery_values_without_fabrication(monkeypatch):
    agent = LearningReportAgent(db=AsyncMock())
    user_id = uuid4()
    mastery_rows = [
        {"node_name": "行列式", "mastery_score": 38.0, "node_id": "node-1"},
        {"node_name": "特征值", "mastery_score": 72.0, "node_id": "node-2"},
    ]
    timeline_rows = [
        {
            "node_name": "行列式",
            "node_id": "node-1",
            "study_minutes": 25,
            "mastery_delta": None,
            "created_at": "2026-03-30T08:00:00+00:00",
            "days_since_last": 3,
        }
    ]
    monkeypatch.setattr(agent.tools, "query_mastery_scores", AsyncMock(return_value=mastery_rows))
    monkeypatch.setattr(agent.tools, "query_error_patterns", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent.tools, "query_study_timeline", AsyncMock(return_value=timeline_rows))
    monkeypatch.setattr(
        agent.tools,
        "interview_learner",
        AsyncMock(return_value={"learner_voice": "我现在更怕把行列式展开搞错。"}),
    )
    monkeypatch.setattr(
        agent.tools,
        "infer_learning_state_from_chat",
        AsyncMock(return_value={}),
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
    monkeypatch.setattr(
        "app.services.report.learning_report_agent.SystemUpdateService.enqueue",
        AsyncMock(return_value=True),
    )
    agent.logger.log_jsonl = lambda *args, **kwargs: None
    agent.logger.log_text = lambda *args, **kwargs: None

    payload = await agent.generate_report(user_id)

    mastery_by_name = {item["node_name"]: item["mastery_score"] for item in payload["mastery"]}
    assert mastery_by_name == {"行列式": 38.0, "特征值": 72.0}
    assert payload["timeline"][0]["mastery_delta"] is None


async def test_learning_report_builds_structured_dashboard_payload(monkeypatch):
    agent = LearningReportAgent(db=AsyncMock())
    fixed_now = datetime(2026, 4, 1, 8, 0, 0, tzinfo=UTC)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is not None else fixed_now.replace(tzinfo=None)

    # drift-fix: freeze trend bucketing so dashboard expectations do not drift
    # with the wall clock date of the test run.
    monkeypatch.setattr("app.services.report.learning_report_agent.datetime", _FixedDateTime)

    diagnosis_cards = agent._build_diagnosis_cards(
        mastery=[
            {"node_name": "行列式", "mastery_score": 52},
            {"node_name": "特征值", "mastery_score": 81},
        ],
        patterns=[
            {
                "pattern_name": "夜间能量错配循环",
                "description": "高强度任务经常被拖到晚上。",
                "solution_text": "把最费脑的任务前移到白天。",
            }
        ],
        timeline=[
            {
                "node_name": "行列式",
                "study_minutes": 30,
                "mastery_delta": 3,
                "created_at": "2026-03-26T08:00:00+00:00",
            },
            {
                "node_name": "特征值",
                "study_minutes": 40,
                "mastery_delta": 7,
                "created_at": "2026-03-19T08:00:00+00:00",
            },
        ],
        chat_inference={"topics": ["行列式"]},
    )
    trend_overview = agent._build_trend_overview(
        mastery=[
            {"node_name": "行列式", "mastery_score": 52},
            {"node_name": "特征值", "mastery_score": 81},
        ],
        timeline=[
            {
                "node_name": "行列式",
                "study_minutes": 30,
                "mastery_delta": 3,
                "created_at": "2026-03-26T08:00:00+00:00",
            },
            {
                "node_name": "特征值",
                "study_minutes": 40,
                "mastery_delta": 7,
                "created_at": "2026-03-19T08:00:00+00:00",
            },
        ],
    )
    action_cards = await agent._build_action_cards(
        mastery=[
            {"node_name": "行列式", "mastery_score": 52, "node_id": "node-1"},
            {"node_name": "特征值", "mastery_score": 81, "node_id": "node-2"},
        ],
        patterns=[{"pattern_name": "中途放弃倾向"}],
        timeline=[
            {
                "node_name": "行列式",
                "node_id": "node-1",
                "study_minutes": 30,
                "mastery_delta": 3,
                "days_since_last": 10,
                "created_at": "2026-03-26T08:00:00+00:00",
            }
        ],
        user_id=uuid4(),
    )

    assert diagnosis_cards[0]["tag"] == "weak_spot"
    assert any(card["tag"] == "pattern" for card in diagnosis_cards)
    assert trend_overview["history_points"]
    assert trend_overview["comparisons"]
    assert action_cards[0]["kind"] == "immediate_action"
    assert action_cards[0]["deep_link"] == "/galaxy/node/node-1"
    assert any(card["kind"] == "behavior_change" for card in action_cards)
    assert any(card["kind"] == "spaced_review" for card in action_cards)


def test_build_trend_overview_handles_sparse_week_buckets(monkeypatch):
    agent = LearningReportAgent(db=AsyncMock())
    fixed_now = datetime(2026, 4, 1, 8, 0, 0, tzinfo=UTC)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is not None else fixed_now.replace(tzinfo=None)

    # drift-fix: keep week labels deterministic across later calendar dates.
    monkeypatch.setattr("app.services.report.learning_report_agent.datetime", _FixedDateTime)

    trend_overview = agent._build_trend_overview(
        mastery=[
            {"node_name": "学习方法论", "mastery_score": 45},
            {"node_name": "任务拆解", "mastery_score": 75},
        ],
        timeline=[
            {
                "node_name": "学习方法论",
                "study_minutes": 25,
                "mastery_delta": 2,
                "created_at": "2026-03-29T08:00:00+00:00",
            },
            {
                "node_name": "任务拆解",
                "study_minutes": 35,
                "mastery_delta": 4,
                "created_at": "2026-03-15T08:00:00+00:00",
            },
        ],
    )

    labels = [point["label"] for point in trend_overview["history_points"]]
    assert labels == ["上上周", "本周"]
    assert trend_overview["comparisons"]


def test_build_trend_overview_returns_no_data_without_timeline():
    agent = LearningReportAgent(db=AsyncMock())

    trend_overview = agent._build_trend_overview(
        mastery=[],
        timeline=[],
    )

    assert trend_overview["status"] == "no_data"
    assert "暂无足够学习记录生成趋势" in trend_overview["message"]


def test_learning_report_extracts_simulation_blindspots_from_explicit_trigger_source():
    payload = {
        "source": "simulation",
        "knowledge_gaps_revealed": [
            "不知道特征向量为什么表示不变方向",
            "把特征值和对角线元素直接等同",
        ],
    }

    blindspots = LearningReportAgent._simulation_blindspots_from_trigger_source(payload)

    assert blindspots == [
        "不知道特征向量为什么表示不变方向",
        "把特征值和对角线元素直接等同",
    ]


def test_infer_bridge_tool_names_matches_prediction_and_simulation_intents():
    orchestrator = object.__new__(ChatOrchestrator)

    prediction_tools = orchestrator._infer_bridge_tool_names("如果我两周学完特征值会怎样？")
    simulation_tools = orchestrator._infer_bridge_tool_names("帮我模拟一个学习小组讨论这个概念")
    natural_prediction_tools = orchestrator._infer_bridge_tool_names("帮我推演一下学 Python 的路径")
    natural_simulation_tools = orchestrator._infer_bridge_tool_names("我想模拟一下学习场景")
    report_tools = orchestrator._infer_bridge_tool_names("给我生成一份最近学习表现的分析报告")
    plain_tools = orchestrator._infer_bridge_tool_names("解释一下什么是特征值")

    assert "launch_prediction" in prediction_tools
    assert "run_quick_simulation" in simulation_tools
    assert "launch_prediction" in natural_prediction_tools
    assert "run_quick_simulation" in natural_simulation_tools
    assert "generate_learning_report" in report_tools
    assert plain_tools == []


def test_infer_bridge_tool_names_respects_negation():
    orchestrator = object.__new__(ChatOrchestrator)

    no_prediction_tools = orchestrator._infer_bridge_tool_names("我不需要推演这条学习路径")
    no_simulation_tools = orchestrator._infer_bridge_tool_names("先别模拟学习小组讨论")
    no_report_tools = orchestrator._infer_bridge_tool_names("这次不用生成学习报告")

    assert "launch_prediction" not in no_prediction_tools
    assert "run_quick_simulation" not in no_simulation_tools
    assert "generate_learning_report" not in no_report_tools


def test_resolve_active_tools_uses_body_awareness_for_knowledge_turns():
    orchestrator = object.__new__(ChatOrchestrator)
    request = SimpleNamespace(active_tools=[], chat_mode="standard")

    resolved = orchestrator._resolve_active_tools(request, "解释一下什么是特征值")

    assert "query_knowledge" in resolved


def test_resolve_active_tools_does_not_override_explicit_tool_scope():
    orchestrator = object.__new__(ChatOrchestrator)
    request = SimpleNamespace(active_tools=["create_task"], chat_mode="standard")

    resolved = orchestrator._resolve_active_tools(request, "解释一下什么是特征值")

    assert resolved == ["create_task"]


@pytest.mark.asyncio
async def test_maybe_short_circuit_bridge_tool_returns_preview_metadata():
    engine = _DummyExecutionEngine()
    engine.tool_executor = SimpleNamespace(
        execute_tool_call=AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_name="launch_prediction",
                data={
                    "prediction_id": "prediction-001",
                    "topic": "学 Python 的路径",
                    "target_node_id": "node-python",
                    "target_name": "Python编程",
                    "paths": [{"id": "path_foundation", "title": "稳扎稳打"}],
                    "deep_link": "/theater?topic=%E5%AD%A6+Python+%E7%9A%84%E8%B7%AF%E5%BE%84",
                    "source_chat_session_id": "chat-bridge-1",
                },
            )
        ),
    )
    engine._persist_assistant_message = AsyncMock()
    engine._cache_response = AsyncMock()

    responses = await engine._maybe_short_circuit_bridge_tool(
        active_tools=["launch_prediction"],
        user_message="学 Python 的路径",
        user_id=str(uuid4()),
        session_id="chat-bridge-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=None,
    )

    assert responses is not None
    assert len(responses) == 2
    final_response = responses[-1]
    assert final_response.full_text
    assert final_response.metadata["open_theater"] == "true"
    assert "prediction_preview" in final_response.metadata
    engine._persist_assistant_message.assert_awaited_once()
    engine._cache_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_short_circuit_learning_report_returns_preview_metadata():
    engine = _DummyExecutionEngine()
    engine.tool_executor = SimpleNamespace(
        execute_tool_call=AsyncMock(
            return_value=ToolResult(
                success=True,
                tool_name="generate_learning_report",
                data={
                    "report_id": "report-bridge-1",
                    "quality_mode": "fast_balanced",
                    "deep_link": "/learning-report",
                    "report_preview": {
                        "report_id": "report-bridge-1",
                        "markdown": "# 学习分析报告\n\n## 行动计划\n- 先补弱项",
                        "sections": ["Executive Summary", "行动计划"],
                        "mastery": [{"node_name": "特征值", "mastery_score": 61}],
                        "summary": "优先关注特征值，并结合最近学习记录补一轮针对性练习。",
                    },
                    "source_chat_session_id": "chat-bridge-report",
                },
            )
        ),
    )
    engine._persist_assistant_message = AsyncMock()
    engine._cache_response = AsyncMock()

    responses = await engine._maybe_short_circuit_bridge_tool(
        active_tools=["generate_learning_report"],
        user_message="帮我总结最近学习表现",
        user_id=str(uuid4()),
        session_id="chat-bridge-report",
        response_id="resp-report-1",
        request_id="req-report-1",
        trace_id="trace-report-1",
        workflow_id="workflow-report-1",
        prompt_version="v1",
        active_db=None,
    )

    assert responses is not None
    final_response = responses[-1]
    assert final_response.metadata["open_report"] == "true"
    assert final_response.metadata["report_deep_link"] == "/learning-report"
    assert "report_preview" in final_response.metadata
    engine._persist_assistant_message.assert_awaited_once()
    engine._cache_response.assert_awaited_once()
