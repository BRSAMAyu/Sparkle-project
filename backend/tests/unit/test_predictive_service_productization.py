from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from app.services.predictive_service import PredictiveService


def test_finalize_prediction_builds_unified_shape():
    service = PredictiveService(db=None)  # type: ignore[arg-type]

    result = service._finalize_prediction(
        user_id=uuid4(),
        forecast={
            "title": "系统预测你会继续推进重点任务",
            "summary": "先推进 25 分钟最顺手。",
            "confidence": 0.82,
            "predicted_action_type": "resume_priority_task",
            "predicted_window": "next_2h",
            "reasons": ["当前仍有高优先级任务"],
            "suggested_prompt": "帮我继续推进今天的重点任务",
            "explanations": {
                "recent_24h": ["最近24小时保持活跃"],
            },
        },
        horizon="long_horizon",
        source="rules",
        tier="rules",
        fallback_used=True,
        surface="dashboard",
    )

    assert result["schema_version"] == "prediction.v1"
    assert result["horizon"] == "long_horizon"
    assert result["prediction_source"] == "rules"
    assert result["tracking"]["candidate_id"] == result["prediction_id"]
    assert result["recommended_actions"][0]["action_type"] == "resume_priority_task"
    assert result["explanations"]["recent_24h"] == ["最近24小时保持活跃"]
    assert result["entity_card"]["entity_type"] == "prediction"
    assert result["entity_card"]["metrics"]["confidence"] == 0.82


def test_finalize_prediction_adds_chat_action_for_prompt():
    service = PredictiveService(db=None)  # type: ignore[arg-type]

    result = service._finalize_prediction(
        user_id=uuid4(),
        forecast={
            "title": "系统预测你想先把它落成任务",
            "summary": "这更像一个可执行待办。",
            "confidence": 0.79,
            "predicted_action_type": "create_task",
            "predicted_window": "now",
            "reasons": ["输入里有明确任务语义"],
            "suggested_prompt": "帮我把这件事创建成任务",
        },
        horizon="realtime",
        source="free_fast",
        tier="glm-4.7-flash",
        fallback_used=False,
        surface="chat_input",
    )

    action_types = [item["action_type"] for item in result["recommended_actions"]]
    assert "create_task" in action_types
    assert "continue_chat" in action_types


@pytest.mark.asyncio
async def test_dashboard_forecast_attaches_bounded_within_category_preference_hint():
    service = PredictiveService(db=None)  # type: ignore[arg-type]
    forecast = service._finalize_prediction(
        user_id=uuid4(),
        forecast={
            "title": "系统预测你会继续推进重点任务",
            "summary": "先推进 25 分钟最顺手。",
            "confidence": 0.82,
            "predicted_action_type": "resume_priority_task",
            "predicted_window": "next_2h",
            "reasons": ["当前仍有高优先级任务"],
            "suggested_prompt": "帮我继续推进今天的重点任务",
        },
        horizon="long_horizon",
        source="rules",
        tier="rules",
        fallback_used=True,
        surface="dashboard",
    )

    with patch(
        "app.services.predictive_service.WithinCategoryPreferenceService.build_hint",
        new=AsyncMock(
            return_value={
                "claim_scope": "within_category_only",
                "surface": "dashboard.predicted_intent_card",
                "request_category": "task",
                "preferred_tool": "create_task",
                "confidence": 0.79,
                "support_count": 6,
                "shadow_records": 7,
                "divergence_rate": 0.14,
            }
        ),
    ) as mock_build:
        enriched = await service._maybe_attach_within_category_preference(
            user_id=uuid4(),
            forecast=forecast,
        )

    assert enriched["within_category_preference"]["preferred_tool"] == "create_task"
    mock_build.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_surface_forecast_never_attaches_within_category_preference_hint():
    service = PredictiveService(db=None)  # type: ignore[arg-type]
    forecast = service._finalize_prediction(
        user_id=uuid4(),
        forecast={
            "title": "系统预测你想先把它落成任务",
            "summary": "这更像一个可执行待办。",
            "confidence": 0.79,
            "predicted_action_type": "create_task",
            "predicted_window": "now",
            "reasons": ["输入里有明确任务语义"],
            "suggested_prompt": "帮我把这件事创建成任务",
        },
        horizon="realtime",
        source="rules",
        tier="rules",
        fallback_used=True,
        surface="chat_input",
    )

    with patch(
        "app.services.predictive_service.WithinCategoryPreferenceService.build_hint",
        new=AsyncMock(return_value={"preferred_tool": "create_task"}),
    ) as mock_build:
        enriched = await service._maybe_attach_within_category_preference(
            user_id=uuid4(),
            forecast=forecast,
        )

    assert "within_category_preference" not in enriched
    mock_build.assert_not_awaited()
