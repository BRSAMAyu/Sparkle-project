from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.exam_sprint import ExamSprintDashboardTaskGroup
from app.services.exam_sprint_dashboard_service import ExamSprintDashboardService


@pytest.mark.asyncio
async def test_get_dashboard_returns_inactive_when_no_active_exam_plan():
    service = ExamSprintDashboardService(AsyncMock())
    service._get_active_exam_sprint_plan = AsyncMock(return_value=None)

    payload = await service.get_dashboard(uuid4())

    assert payload.active is False
    assert payload.task_groups == []


@pytest.mark.asyncio
async def test_get_dashboard_aggregates_metrics_for_active_plan():
    user_id = uuid4()
    service = ExamSprintDashboardService(AsyncMock())
    plan = SimpleNamespace(
        id=uuid4(),
        name="6天计算机网络冲刺",
        subject="计算机网络",
        target_date=date.today() + timedelta(days=5),
        created_at=None,
        source_metadata={
            "exam_sprint_intake": {
                "goal_model": {
                    "days_left": 6,
                    "target_mode": "pass",
                    "estimated_score_now": 52,
                },
                "initial_assessment": {
                    "pass_probability": 0.38,
                },
            },
        },
    )
    today_group = ExamSprintDashboardTaskGroup(
        day_index=1,
        is_today=True,
        completed_count=2,
        total_count=3,
        tasks=[],
    )

    service._get_active_exam_sprint_plan = AsyncMock(return_value=plan)
    service._get_latest_diagnostic = AsyncMock(
        return_value={
            "diagnostic_estimated_score": 68,
            "diagnostic_pass_probability": 0.71,
        }
    )
    service._list_plan_tasks = AsyncMock(return_value=[])
    service._get_high_frequency_coverage = AsyncMock(
        return_value={
            "coverage": 0.75,
            "covered_count": 3,
            "total_count": 4,
            "weak_topics": ["传输层可靠传输"],
        }
    )
    service._get_mistake_fix_rate = AsyncMock(
        return_value={
            "rate": 0.8,
            "fixed_count": 4,
            "total_count": 5,
        }
    )
    service._get_streak_days = AsyncMock(return_value=7)
    service._derive_initial_days_left = MagicMock(return_value=6)
    service._days_left = MagicMock(return_value=5)
    service._current_day_index = MagicMock(return_value=1)
    service._build_task_groups = MagicMock(return_value=[today_group])

    payload = await service.get_dashboard(user_id)

    assert payload.active is True
    assert payload.days_left == 5
    assert payload.target_mode == "pass"
    assert payload.estimated_score_now == pytest.approx(68)
    assert payload.baseline_estimated_score == pytest.approx(52)
    assert payload.pass_probability == pytest.approx(0.71)
    assert payload.baseline_pass_probability == pytest.approx(0.38)
    assert payload.today_progress.completed == 2
    assert payload.today_progress.total == 3
    assert payload.high_freq_coverage == pytest.approx(0.75)
    assert payload.mistake_fix_rate == pytest.approx(0.8)
    assert payload.streak_days == 7
    assert payload.high_yield_low_mastery_topics == ["传输层可靠传输"]
