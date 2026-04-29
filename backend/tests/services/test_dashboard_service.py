from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.cognitive import BehaviorPattern
from app.services.dashboard_service import DashboardService


@pytest.mark.asyncio
async def test_get_cognitive_summary_filters_archived_patterns():
    db = AsyncMock()
    service = DashboardService(db)

    pattern = BehaviorPattern(
        id=uuid4(),
        user_id=uuid4(),
        pattern_name="Perfectionism Loop",
        pattern_type="cognitive",
        description="desc",
        solution_text="fix",
        confidence_score=0.91,
        frequency=2,
    )

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = pattern
    second_result = MagicMock()
    second_result.scalar.return_value = 1

    seen_queries: list[str] = []

    async def execute_side_effect(query):
        seen_queries.append(str(query).lower())
        return [first_result, second_result][len(seen_queries) - 1]

    db.execute.side_effect = execute_side_effect

    summary = await service._get_cognitive_summary(pattern.user_id)

    assert summary["weekly_pattern"] == "Perfectionism Loop"
    assert summary["description"] == "desc"
    assert summary["solution_text"] == "fix"
    assert summary["status"] == "new"
    assert len(seen_queries) == 2
    assert "is_archived is false" in seen_queries[0]
    assert "is_archived is false" in seen_queries[1]


@pytest.mark.asyncio
async def test_get_cognitive_summary_localizes_known_patterns():
    db = AsyncMock()
    service = DashboardService(db)

    pattern = BehaviorPattern(
        id=uuid4(),
        user_id=uuid4(),
        pattern_name="The Night-Time Energy Mismatch Loop",
        pattern_type="cognitive",
        description="This is an English description that should not leak to users.",
        solution_text="Move hard work earlier in the day.",
        confidence_score=0.93,
        frequency=3,
    )

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = pattern
    second_result = MagicMock()
    second_result.scalar.return_value = 0
    db.execute.side_effect = [first_result, second_result]

    summary = await service._get_cognitive_summary(pattern.user_id)

    assert summary["weekly_pattern"] == "夜间能量错配循环"
    assert "精力明显下滑" in summary["description"]
    assert "前移到你最清醒的两个小时" in summary["solution_text"]
    assert summary["status"] == "active"


@pytest.mark.asyncio
async def test_get_dashboard_status_returns_cached_payload():
    db = AsyncMock()
    service = DashboardService(db)
    user_id = uuid4()
    cached_payload = {"weather": {"type": "sunny"}, "next_actions": []}

    with patch("app.services.dashboard_service.cache_service") as mock_cache:
        mock_cache.get = AsyncMock(return_value=cached_payload)
        mock_cache.set = AsyncMock()

        result = await service.get_dashboard_status(user_id)

    assert result == cached_payload
    db.execute.assert_not_called()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_dashboard_status_caches_computed_payload():
    db = AsyncMock()
    service = DashboardService(db)
    user_id = uuid4()
    user = MagicMock(flame_level=3, flame_brightness=0.75)

    service._get_user = AsyncMock(return_value=user)
    service._get_active_sprint = AsyncMock(return_value={"id": "s1"})
    service._get_active_growth = AsyncMock(return_value={"id": "g1"})
    service._calculate_weather = AsyncMock(return_value={"type": "cloudy", "condition": "需要动起来"})
    service._get_next_actions = AsyncMock(return_value=[{"id": "t1"}])
    service._get_cognitive_summary = AsyncMock(return_value={"status": "active"})
    service._get_today_focus_minutes = AsyncMock(return_value=45)
    service._get_today_completed_tasks = AsyncMock(return_value=3)
    growth_snapshot = {
        "growth_status": {"headline": "Ava，你本周在热力学上进步了 22%"},
        "most_important_task": {"id": "task-1", "title": "复盘热力学错题"},
        "growth_signal": {"topic": "热力学", "delta_points": 22.0},
        "active_plan_progress": {"plan_name": "热力学冲刺", "progress": 0.52},
    }

    with (
        patch("app.services.dashboard_service.cache_service") as mock_cache,
        patch(
            "app.services.dashboard_service.GrowthDashboardService.build_snapshot",
            new=AsyncMock(return_value=growth_snapshot),
        ) as mock_growth_snapshot,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        result = await service.get_dashboard_status(user_id)

    assert result["weather"]["type"] == "cloudy"
    assert result["flame"]["today_focus_minutes"] == 45
    assert result["flame"]["tasks_completed"] == 3
    assert result["growth_status"] == growth_snapshot["growth_status"]
    assert result["most_important_task"] == growth_snapshot["most_important_task"]
    assert result["growth_signal"] == growth_snapshot["growth_signal"]
    assert result["active_plan_progress"] == growth_snapshot["active_plan_progress"]
    mock_growth_snapshot.assert_awaited_once_with(user_id, user=user)
    mock_cache.set.assert_awaited_once_with(
        DashboardService._dashboard_cache_key(user_id),
        result,
        ttl=DashboardService.DASHBOARD_CACHE_TTL_SECONDS,
    )


@pytest.mark.asyncio
async def test_get_recent_anxiety_level_uses_aggregate_counts():
    db = AsyncMock()
    service = DashboardService(db)
    total_result = MagicMock()
    total_result.scalar.return_value = 6
    anxious_result = MagicMock()
    anxious_result.scalar.return_value = 4
    seen_queries: list[str] = []

    async def execute_side_effect(query):
        seen_queries.append(str(query).lower())
        return [total_result, anxious_result][len(seen_queries) - 1]

    db.execute.side_effect = execute_side_effect

    level = await service._get_recent_anxiety_level(uuid4())

    assert level == pytest.approx(4 / 6)
    assert len(seen_queries) == 2
    assert "count(" in seen_queries[0]
    assert "sentiment" in seen_queries[1]


# ── T4.1: Spine/Aurora Dashboard Integration Tests ──────────────────────


@pytest.mark.asyncio
async def test_get_spine_status_returns_band_data():
    """Spine status band data is included in dashboard response."""
    db = AsyncMock()
    service = DashboardService(db)
    user_id = uuid4()
    user = MagicMock(flame_level=3, flame_brightness=0.75)

    service._get_user = AsyncMock(return_value=user)
    service._get_active_sprint = AsyncMock(return_value=None)
    service._get_active_growth = AsyncMock(return_value=None)
    service._calculate_weather = AsyncMock(return_value={"type": "sunny", "condition": "晴朗"})
    service._get_next_actions = AsyncMock(return_value=[])
    service._get_cognitive_summary = AsyncMock(return_value={"status": "empty"})
    service._get_today_focus_minutes = AsyncMock(return_value=0)
    service._get_today_completed_tasks = AsyncMock(return_value=0)

    mock_summary = {
        "band_status": "calibrated",
        "band_label": "已校准",
        "band_summary": "系统已了解你的学习状态",
        "band_severity": "info",
        "band_energy": "L1",
        "active_claims": ["goal_mode:exam_rescue"],
        "correction_options": [{"label": "调整目标", "semantic_value": "adjust_goal"}],
    }

    with (
        patch("app.services.dashboard_service.cache_service") as mock_cache,
        patch("app.services.dashboard_service.GrowthDashboardService") as mock_growth_cls,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.redis = MagicMock()
        mock_growth_cls.return_value.build_snapshot = AsyncMock(return_value={})

        with patch("app.signals.spine_orchestrator.SpineOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch.get_status_band_summary = AsyncMock(return_value=mock_summary)
            mock_orch_cls.return_value = mock_orch

            result = await service.get_dashboard_status(user_id)

    assert result["spine"]["band_status"] == "calibrated"
    assert result["spine"]["band_label"] == "已校准"
    assert result["spine"]["band_severity"] == "info"
    assert result["spine"]["active_claims"] == ["goal_mode:exam_rescue"]
    assert len(result["spine"]["correction_options"]) == 1


@pytest.mark.asyncio
async def test_get_spine_status_returns_none_when_no_redis():
    """Dashboard gracefully degrades when Redis is not initialized."""
    db = AsyncMock()
    service = DashboardService(db)

    with patch("app.services.dashboard_service.cache_service") as mock_cache:
        mock_cache.redis = None
        result = await service._get_spine_status(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_spine_status_returns_none_on_exception():
    """Dashboard does not crash if Spine orchestrator fails."""
    db = AsyncMock()
    service = DashboardService(db)

    with patch("app.services.dashboard_service.cache_service") as mock_cache:
        mock_cache.redis = MagicMock()
        with patch("app.signals.spine_orchestrator.SpineOrchestrator") as mock_orch_cls:
            mock_orch_cls.side_effect = RuntimeError("Redis connection refused")
            result = await service._get_spine_status(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_dashboard_payload_backward_compatible_with_spine():
    """Full dashboard payload includes all legacy fields plus spine data."""
    db = AsyncMock()
    service = DashboardService(db)
    user_id = uuid4()
    user = MagicMock(flame_level=2, flame_brightness=0.5)

    service._get_user = AsyncMock(return_value=user)
    service._get_active_sprint = AsyncMock(return_value=None)
    service._get_active_growth = AsyncMock(return_value=None)
    service._calculate_weather = AsyncMock(return_value={"type": "cloudy", "condition": "进度落后"})
    service._get_next_actions = AsyncMock(return_value=[{"id": "t1", "title": "复习热力学"}])
    service._get_cognitive_summary = AsyncMock(return_value={"status": "active"})
    service._get_today_focus_minutes = AsyncMock(return_value=30)
    service._get_today_completed_tasks = AsyncMock(return_value=2)

    with (
        patch("app.services.dashboard_service.cache_service") as mock_cache,
        patch("app.services.dashboard_service.GrowthDashboardService") as mock_growth_cls,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.redis = None  # No Redis → spine is None
        mock_growth_cls.return_value.build_snapshot = AsyncMock(return_value={})

        result = await service.get_dashboard_status(user_id)

    # Legacy fields all present
    assert "weather" in result
    assert "flame" in result
    assert "sprint" in result
    assert "growth" in result
    assert "next_actions" in result
    assert "cognitive" in result
    # Spine key exists but is None (graceful degradation)
    assert result.get("spine") is None
