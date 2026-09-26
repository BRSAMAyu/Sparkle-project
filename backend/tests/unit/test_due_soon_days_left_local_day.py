"""V3-FIX-209（用户洞察 due_soon / 计划 days_left 沿 UTC date）红绿测：切用户本地日。

定界实录（wt494 V3-FIX-197 同族 grep 登记）：
- ``user_insight_analysis_service._build_medium_span``（经 ``analyze``）：
  ``due_soon = (task.due_date - _utcnow().date()).days <= 7`` —— UTC+8 晨间
  （UTC 尚在前日）due_soon 少算一日（due_date=本地今日+7 的任务差一天
  不进「7 天内到期」）；
- ``growth_dashboard_service._days_until``（plan chip ``days_to_deadline``
  与 growth_status 文案共用）：``(target - _utcnow().date()).days`` ——
  同钟错位，晨间 days_left 偏一日；
- 纯提示性读数无资损（P4），修法 = 一处换算：today 用用户本地日
  （push_preference.timezone 标量直查 + 缺省 Asia/Shanghai，沿
  experience_readouts._user_local_today / time_utils.local_date 先例）。

冻结钟 NOW = 2026-09-25 23:30 UTC（上海本地 = 2026-09-26 07:30，沿
test_today_view_local_date_boundary 冻结钟族）：上海用户「今日」= 09-26，
UTC 用户「今日」= 09-25 —— due/target = 2026-10-03 时上海侧恰在 7 天界上
（应计入/days=7），修前按 UTC 09-25 取 8 天 → 漏计/偏一日；UTC 用户控制
组证明边界确由用户时区驱动。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.profile_context import ProfileContext
from app.core.user_insight_state import UserInsightState
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.user_insight_analysis_service import UserInsightAnalysisService

NOW = dt.datetime(2026, 9, 25, 23, 30)  # naive UTC；上海本地 = 2026-09-26 07:30
LOCAL_TODAY = dt.date(2026, 9, 26)  # 上海用户本地今日
UTC_TODAY = dt.date(2026, 9, 25)  # UTC 用户本地今日
TARGET = dt.date(2026, 10, 3)  # = LOCAL_TODAY + 7（上海侧恰在 7 天界上）


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.growth_dashboard_service as growth_module
    import app.services.user_insight_analysis_service as insight_module

    monkeypatch.setattr(insight_module, "_utcnow", lambda: NOW)
    monkeypatch.setattr(growth_module, "_utcnow", lambda: NOW)


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt499-{uuid4().hex[:8]}",
        email=f"wt499-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def test_insight_due_soon_uses_user_local_day(db_session: AsyncSession, frozen_clock: None):
    """上海晨间：due_date=本地今日+7 的任务应进 due_soon（修前差一日漏计）。

    due_soon 是 _build_medium_span 内部计数，外显面为 deadline_pressure
    （due_soon>=1 → medium；漏计时 0 → low）。
    """
    user = await _seed_user(db_session)
    db_session.add(
        Task(
            user_id=user.id,
            title="七天后到期的复习",
            type=TaskType.LEARNING,
            tags=[],
            estimated_minutes=25,
            status=TaskStatus.PENDING,
            due_date=TARGET,
        )
    )
    await db_session.commit()

    service = UserInsightAnalysisService(db_session)
    result = await service.analyze(user_id=user.id, state=UserInsightState(), profile_context=ProfileContext())

    assert result["medium_span"]["deadline_pressure"] == "medium", (
        f"上海晨间本地今日=09-26，due_date=10-03 恰在 7 天界上应计入 due_soon"
        f"（deadline_pressure=medium）；修前按 UTC 今日 09-25 取 8 天 → 漏计为 low：{result['medium_span']}"
    )


async def test_insight_due_soon_boundary_is_timezone_driven(db_session: AsyncSession, frozen_clock: None):
    """UTC 用户控制组：本地今日=09-25，due_date=10-03 差 8 天不进 due_soon。"""
    user = await _seed_user(db_session, timezone="UTC")
    db_session.add(
        Task(
            user_id=user.id,
            title="UTC 用户八天后到期",
            type=TaskType.LEARNING,
            tags=[],
            estimated_minutes=25,
            due_date=TARGET,
        )
    )
    await db_session.commit()

    service = UserInsightAnalysisService(db_session)
    result = await service.analyze(user_id=user.id, state=UserInsightState(), profile_context=ProfileContext())

    assert (
        result["medium_span"]["deadline_pressure"] == "low"
    ), f"UTC 用户本地今日=09-25，due_date=10-03 差 8 天不应进 due_soon：{result['medium_span']}"


async def test_plan_days_left_uses_user_local_day(db_session: AsyncSession, frozen_clock: None):
    """上海晨间：target_date=本地今日+7 的计划 days_to_deadline 应为 7（修前 8）。"""
    user = await _seed_user(db_session)
    db_session.add(
        Plan(
            user_id=user.id,
            name="上海用户冲刺",
            type=PlanType.GROWTH,
            plan_stage=PlanStage.DAILY,
            priority=PlanPriority.NORMAL,
            is_active=True,
            target_date=TARGET,
        )
    )
    await db_session.commit()

    snapshot = await GrowthDashboardService(db_session).build_snapshot(user.id)

    progress = snapshot["active_plan_progress"]
    assert progress is not None
    assert progress["days_to_deadline"] == 7, (
        f"上海晨间本地今日=09-26，target_date=10-03 的 days_to_deadline 应为 7；"
        f"修前按 UTC 今日 09-25 → 偏一日为 8：{progress}"
    )


async def test_plan_days_left_boundary_is_timezone_driven(db_session: AsyncSession, frozen_clock: None):
    """UTC 用户控制组：本地今日=09-25，target_date=10-03 的 days_to_deadline=8。"""
    user = await _seed_user(db_session, timezone="UTC")
    db_session.add(
        Plan(
            user_id=user.id,
            name="UTC 用户冲刺",
            type=PlanType.GROWTH,
            plan_stage=PlanStage.DAILY,
            priority=PlanPriority.NORMAL,
            is_active=True,
            target_date=TARGET,
        )
    )
    await db_session.commit()

    snapshot = await GrowthDashboardService(db_session).build_snapshot(user.id)

    progress = snapshot["active_plan_progress"]
    assert progress is not None
    assert progress["days_to_deadline"] == 8, f"UTC 用户本地今日=09-25，days_to_deadline 应为 8：{progress}"
