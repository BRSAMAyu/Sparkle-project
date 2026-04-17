from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.growth_dashboard_service import GrowthDashboardService


@pytest.mark.asyncio
async def test_growth_status_reads_like_growth_briefing():
    service = GrowthDashboardService(db=None)
    service._sum_focus_minutes = AsyncMock(return_value=180)  # type: ignore[method-assign]
    service._count_completed_tasks = AsyncMock(return_value=8)  # type: ignore[method-assign]
    service._get_current_streak_days = AsyncMock(return_value=4)  # type: ignore[method-assign]
    service._get_weakest_area = AsyncMock(return_value="听力理解")  # type: ignore[method-assign]

    user = SimpleNamespace(nickname="Mina", full_name=None, username="mina")
    active_plan = SimpleNamespace(name="IELTS 冲刺", subject="IELTS", target_date=None)
    growth_signal = {"topic": "听力理解", "delta_points": 22.0}
    most_important_task = {"title": "20 分钟 shadowing 训练"}

    status = await service._get_growth_status(
        user_id=uuid4(),
        user=user,
        active_plan=active_plan,
        growth_signal=growth_signal,
        most_important_task=most_important_task,
        weakest_area="听力理解",
    )

    assert "完成了 8 个任务" in status["headline"]
    assert "听力理解" in status["headline"]
    assert "现在最该补的是「听力理解」" in status["subtitle"]
    assert "我建议你先做「20 分钟 shadowing 训练」" in status["subtitle"]
    assert "连续 4 天保持推进" in status["subtitle"]

    what_changed = service._build_what_changed_card(
        growth_signal={"topic": "听力理解", "summary": "掌握度在稳步回升。"},
        growth_status=status,
        weakest_area="听力理解",
    )
    next_move = service._build_next_move_card(
        most_important_task={
            "id": "task-1",
            "title": "20 分钟 shadowing 训练",
            "estimated_minutes": 20,
            "reason": "它背后对应的掌握度缺口还比较大，先补上会更稳。",
            "plan_name": "IELTS 冲刺",
            "days_to_deadline": 6,
        },
        active_plan=active_plan,
        weakest_area="听力理解",
    )

    assert what_changed is not None
    assert "听力理解" in what_changed["summary"]
    assert next_move is not None
    assert "下一步先做" in next_move["headline"]
    assert "如果今天状态不稳" in next_move["reassurance"]
