from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.growth_dashboard_service import DailyContextLineContext, GrowthDashboardService


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


def test_daily_context_rule_line_uses_real_context_points():
    service = GrowthDashboardService(db=None)
    context = DailyContextLineContext(
        target_day=date(2026, 4, 25),
        display_name="Mina",
        plan_name="热力学考试",
        days_to_deadline=3,
        yesterday_total=4,
        yesterday_completed=2,
        bottleneck="热力学",
        streak_days=3,
        next_action_title="整理可逆过程错题",
    )

    line = service._rule_daily_context_line(context)

    assert "热力学" in line
    assert "整理可逆过程错题" in line or "3天" in line or "2/4" in line
    assert line.endswith("。")


def test_daily_context_rule_line_falls_back_without_data():
    service = GrowthDashboardService(db=None)
    context = DailyContextLineContext(
        target_day=date(2026, 4, 25),
        display_name="Mina",
    )

    line = service._rule_daily_context_line(context)

    assert line
    assert "早上好" in line or "今天" in line
    assert line.endswith("。")


@pytest.mark.asyncio
async def test_daily_context_line_uses_ai_when_it_references_context():
    service = GrowthDashboardService(db=None)
    user_id = uuid4()
    context = DailyContextLineContext(
        target_day=date(2026, 4, 25),
        display_name="Mina",
        plan_name="热力学考试",
        days_to_deadline=3,
        bottleneck="热力学",
        streak_days=4,
        next_action_title="整理错题",
    )

    class FakeCache:
        def __init__(self):
            self.values = {}

        async def get(self, key):
            return self.values.get(key)

        async def set(self, key, value, ttl=None):
            self.values[key] = value

    fake_cache = FakeCache()
    service._build_daily_context_line_context = AsyncMock(return_value=context)  # type: ignore[method-assign]
    service._generate_daily_context_line_with_ai = AsyncMock(  # type: ignore[method-assign]
        return_value="离「热力学考试」还有 3 天，今天先把热力学错题接上。"
    )

    with patch("app.services.growth_dashboard_service.cache_service", fake_cache):
        payload = await service.get_daily_context_line(user_id, target_day=context.target_day)
        cached = await service.get_daily_context_line(user_id, target_day=context.target_day)

    assert payload["source"] == "ai"
    assert payload["text"] == "离「热力学考试」还有3天，今天先把热力学错题接上。"
    assert cached == payload
    service._generate_daily_context_line_with_ai.assert_awaited_once()
