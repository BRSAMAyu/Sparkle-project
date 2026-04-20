from __future__ import annotations

import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.tool_history import UserToolPreference
from app.routing.tool_preference_router import ToolPreferenceRouter, _utcnow


@pytest.fixture
def router() -> ToolPreferenceRouter:
    db_session = MagicMock()
    user_id = uuid.uuid4()
    router = ToolPreferenceRouter(db_session=db_session, user_id=user_id)
    router.history_service.get_user_preferred_tools = AsyncMock()
    router.history_service.get_tool_success_rate = AsyncMock()
    router._get_all_used_tools = AsyncMock()
    return router


@pytest.mark.asyncio
async def test_get_preferred_tools_returns_ranked_names(router: ToolPreferenceRouter):
    router.history_service.get_user_preferred_tools.return_value = [
        UserToolPreference(
            user_id=router.user_id,
            tool_name="create_plan",
            preference_score=0.9,
            last_30d_success_rate=90.0,
            last_30d_usage=10,
        ),
        UserToolPreference(
            user_id=router.user_id,
            tool_name="create_task",
            preference_score=0.8,
            last_30d_success_rate=80.0,
            last_30d_usage=8,
        ),
    ]

    result = await router.get_preferred_tools(category="plan", limit=2)

    assert result == ["create_plan", "create_task"]
    router.history_service.get_user_preferred_tools.assert_awaited_once_with(
        user_id=router.user_id,
        limit=2,
        days=30,
    )


@pytest.mark.asyncio
async def test_estimate_tool_success_probability_applies_context_factor(router: ToolPreferenceRouter):
    router.history_service.get_tool_success_rate.return_value = 60.0
    router._get_productivity_factor = MagicMock(return_value=1.2)

    result = await router.estimate_tool_success_probability("create_plan", context={"hour": 9})

    assert result == pytest.approx(0.72)


@pytest.mark.asyncio
async def test_rank_tools_by_success_sorts_descending(router: ToolPreferenceRouter):
    async def side_effect(tool_name: str, context=None) -> float:
        return {
            "create_plan": 0.6,
            "create_task": 0.9,
            "query_knowledge": 0.4,
        }[tool_name]

    router.estimate_tool_success_probability = AsyncMock(side_effect=side_effect)

    ranked = await router.rank_tools_by_success(
        ["create_plan", "create_task", "query_knowledge"],
        context={"mode": "study"},
    )

    assert ranked == [
        ("create_task", 0.9),
        ("create_plan", 0.6),
        ("query_knowledge", 0.4),
    ]


@pytest.mark.asyncio
async def test_should_retry_tool_when_recent_success_rate_is_high(router: ToolPreferenceRouter):
    router.history_service.get_tool_success_rate.return_value = 88.0

    should_retry = await router.should_retry_tool("create_plan", _utcnow())

    assert should_retry is True


@pytest.mark.asyncio
async def test_should_retry_tool_after_long_failure_cooldown(router: ToolPreferenceRouter):
    router.history_service.get_tool_success_rate.return_value = 10.0

    should_retry = await router.should_retry_tool(
        "create_plan",
        _utcnow() - timedelta(hours=4),
    )

    assert should_retry is True


@pytest.mark.asyncio
async def test_get_fallback_tools_excludes_primary_and_returns_best_candidates(router: ToolPreferenceRouter):
    router._get_all_used_tools.return_value = [
        "create_plan",
        "create_task",
        "query_knowledge",
        "suggest_focus_session",
    ]
    router.rank_tools_by_success = AsyncMock(
        return_value=[
            ("query_knowledge", 0.91),
            ("create_task", 0.82),
            ("suggest_focus_session", 0.71),
        ]
    )

    result = await router.get_fallback_tools("create_plan", limit=2)

    assert result == ["query_knowledge", "create_task"]
    router.rank_tools_by_success.assert_awaited_once()


class _FakeScalarResult:
    def __init__(self, records):
        self._records = records

    def scalars(self):
        return self

    def all(self):
        return list(self._records)


@pytest.mark.asyncio
async def test_rule_v_reward_label_regression_explicit_unhelpful_success_does_not_outvote_helpful_tool():
    db_session = MagicMock()
    user_id = uuid.uuid4()
    db_session.execute = AsyncMock(
        return_value=_FakeScalarResult(
            [
                SimpleNamespace(
                    tool_category="plan",
                    tool_name="create_plan",
                    success=True,
                    was_helpful=False,
                    user_satisfaction=2,
                )
                for _ in range(5)
            ]
            + [
                SimpleNamespace(
                    tool_category="plan",
                    tool_name="break_down_task",
                    success=True,
                    was_helpful=True,
                    user_satisfaction=5,
                )
                for _ in range(3)
            ]
        )
    )

    router = ToolPreferenceRouter(db_session=db_session, user_id=user_id)
    await router.update_learner_from_history()

    helpful_probability = await router.learner.get_probability("state_plan", "break_down_task")
    unhelpful_probability = await router.learner.get_probability("state_plan", "create_plan")

    assert helpful_probability > unhelpful_probability


@pytest.mark.asyncio
async def test_rule_v_reward_label_regression_satisfaction_fallback_beats_raw_success_only():
    db_session = MagicMock()
    user_id = uuid.uuid4()
    db_session.execute = AsyncMock(
        return_value=_FakeScalarResult(
            [
                SimpleNamespace(
                    tool_category="review",
                    tool_name="semantic_search",
                    success=True,
                    was_helpful=None,
                    user_satisfaction=2,
                )
                for _ in range(4)
            ]
            + [
                SimpleNamespace(
                    tool_category="review",
                    tool_name="reopen_error_book",
                    success=True,
                    was_helpful=None,
                    user_satisfaction=5,
                )
                for _ in range(3)
            ]
        )
    )

    router = ToolPreferenceRouter(db_session=db_session, user_id=user_id)
    await router.update_learner_from_history()

    satisfied_probability = await router.learner.get_probability("state_review", "reopen_error_book")
    low_satisfaction_probability = await router.learner.get_probability("state_review", "semantic_search")

    assert satisfied_probability > low_satisfaction_probability
