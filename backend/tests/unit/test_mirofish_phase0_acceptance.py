from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.report.learning_report_agent import LearningReportAgent
from app.services.simulation.seed_extractor import SeedExtractor, SimulationSeed
from app.services.theater.prediction_theater_service import PredictionTheaterService
from app.tools.theater_tool import LaunchPredictionParams, LaunchPredictionTool


@pytest.mark.asyncio
async def test_theater_free_mode_generates_preview_when_node_lookup_fails(monkeypatch):
    service = PredictionTheaterService(db=AsyncMock())

    monkeypatch.setattr(
        service,
        "_resolve_target_node_for_user",
        AsyncMock(side_effect=ValueError('No knowledge node found for topic "Rust"')),
    )
    monkeypatch.setattr(
        service,
        "_get_mastery_map",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        service,
        "_build_user_learning_profile",
        AsyncMock(return_value={"average_session_minutes": 35}),
    )
    monkeypatch.setattr(
        service,
        "_top_pattern_names",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        service.accuracy,
        "record_prediction",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.analysis_llm.json_call",
        AsyncMock(
            return_value={
                "target_name": "Rust 学习路径",
                "description": "面向系统编程初学者的自由模式推演。",
                "prerequisites": ["变量与类型", "所有权", "借用"],
                "milestones": ["完成一个命令行小项目"],
            }
        ),
    )

    payload = await service.generate_prediction(
        user_id=uuid4(),
        topic="帮我推演一下学 Rust 的路径",
        preview_mode=True,
    )

    assert payload["target_name"] == "Rust 学习路径"
    assert payload["target_node_id"] is None
    assert payload["routing_notes"]["target_resolution_mode"] == "free_mode"
    assert payload["paths"]


@pytest.mark.asyncio
async def test_launch_prediction_tool_omits_target_node_id_in_free_mode_deep_link(monkeypatch):
    async def fake_generate_prediction(self, *, user_id, topic, target_node_id=None, horizon_days=14, preview_mode=False):
        del self, user_id, topic, target_node_id, horizon_days, preview_mode
        return {
            "prediction_id": "prediction-free-1",
            "topic": "帮我推演一下学 Rust 的路径",
            "target_name": "Rust 学习路径",
            "target_node_id": None,
            "paths": [{"id": "path_foundation", "title": "稳扎稳打"}],
        }

    monkeypatch.setattr(
        "app.tools.theater_tool.PredictionTheaterService.generate_prediction",
        fake_generate_prediction,
    )

    tool = LaunchPredictionTool()
    result = await tool.execute(
        LaunchPredictionParams(
            topic="帮我推演一下学 Rust 的路径",
            source_chat_session_id="chat-free-mode",
        ),
        user_id=str(uuid4()),
        db_session=AsyncMock(),
        tool_call_id="tool-free-mode",
    )

    assert result.success is True
    assert result.data["deep_link"] == "/theater?topic=Rust+%E5%AD%A6%E4%B9%A0%E8%B7%AF%E5%BE%84&source_chat_session_id=chat-free-mode"


@pytest.mark.asyncio
async def test_seed_extractor_prefers_onboarding_profile_seeds_for_cold_start(monkeypatch):
    extractor = SeedExtractor(db=AsyncMock())
    onboarding_seed = SimulationSeed(
        topic="先为 数学 生成一条入门理解路线",
        context="来自学习画像的冷启动方向。",
        tension_point="先把起步动作说清楚。",
        source_type="onboarding_profile",
        source_ids=["profile-1"],
        relevance_score=0.78,
        suggested_scenario="knowledge_debate",
        suggested_experts=["深度分析", "星图导航"],
    )

    monkeypatch.setattr(extractor, "_onboarding_seeds", AsyncMock(return_value=[onboarding_seed]))
    monkeypatch.setattr(extractor, "_task_bootstrap_seeds", AsyncMock(return_value=[]))
    monkeypatch.setattr(extractor, "_active_plan_bootstrap_seeds", AsyncMock(return_value=[]))
    monkeypatch.setattr(extractor, "_graph_bootstrap_seeds", AsyncMock(return_value=[]))

    seeds = await extractor._cold_start_seeds(
        uuid4(),
        scenario_key="knowledge_debate",
        limit=2,
    )

    assert [seed.source_type for seed in seeds] == ["onboarding_profile"]


@pytest.mark.asyncio
async def test_learning_report_uses_chat_inference_for_intro_diagnostic(monkeypatch):
    agent = LearningReportAgent(db=AsyncMock())
    user_id = uuid4()

    monkeypatch.setattr(agent.tools, "query_mastery_scores", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent.tools, "query_error_patterns", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent.tools, "query_study_timeline", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        agent.tools,
        "interview_learner",
        AsyncMock(return_value={"learner_voice": "先建立第一轮学习记录。"}),
    )
    monkeypatch.setattr(
        agent.tools,
        "infer_learning_state_from_chat",
        AsyncMock(
            return_value={
                "topics": ["Rust 所有权"],
                "frictions": ["起步路径还不够清晰"],
                "goal_summary": "想系统学 Rust",
                "evidence": ["帮我推演一下学 Rust 的路径"],
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.report.learning_report_agent.SeedExtractor.extract_seeds",
        AsyncMock(return_value=[]),
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

    assert payload["starter_focus"][0]["source_type"] == "chat_inference"
    assert payload["mastery"][0]["node_name"] == "Rust 所有权"
    assert payload["patterns"][0]["raw_pattern_name"] == "chat_inferred_bootstrap_friction"
    assert payload["chat_inference"]["goal_summary"] == "想系统学 Rust"
