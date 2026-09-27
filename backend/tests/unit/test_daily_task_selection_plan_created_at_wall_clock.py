"""V3-FIX-314 红绿测：``_plan_current_day`` 的 plan.created_at 按墙上钟语义取日。

定界（JOURNEY day6 门 09-27 08:00 实测捕获，主会话取证）：today 面
零候选——``_plan_current_day``（daily_task_selection_service.py:107-121）
把**本地墙上钟存储**的 ``plan.created_at``（JOURNEY 计划 7917e864
created 2026-09-22 21:15:30，与 day0 会话 run_id 20260922-211514 同钟
=上海墙上钟；mobile/服务写入无时区后缀本地 ISO，wt582 已实证同库约定）
当 UTC 经 ``_as_local_date``（V3-FIX-221 统一入口，UTC 假设）+8 换算成
09-23 → total_days 少一天 → current_day 恒偏小 → 当日 day:N 任务被
today 面排除（day6 门 08:00 实测 /tasks/today 返回 []）。

同族约定（修法依据）：day 数学的两个同源消费面早就按墙上钟取日——
``exam_sprint_dashboard_service._derive_initial_days_left`` 与
``api/v1/plans.py._initial_days_for_today`` 均为
``(plan.target_date - plan.created_at.date()).days``（无 tz 换算）；
``_plan_current_day`` 的注释也自称「the same convention
exam_sprint_dashboard uses」，实现却在 V3-FIX-221 统一入口时被误带成
UTC 换算。修法：plan.created_at 直接 ``.date()``（墙上钟语义，不做
+8 双重换算）；``plan.target_date`` 是日界值透传不换算（既有行为）。

墙上钟语义与时区无关：存储值即本地钟，day 数学读侧不该再吃 tz——
同一 stored plan 对 Asia/Shanghai 与 UTC 用户算出的 current_day 必须一致
（修前恰好相反：Shanghai +8→current 5，UTC 恒等→current 6，昨日 day5
门通过系当时栈 tz 缺省 UTC 恰好算对）。冻结钟 NOW=2026-09-27 03:00
naive UTC（上海 11:00/UTC 均为 09-27，两时区本地日相同，一致性断言干净）：
- plan created 09-22 21:15:30 墙上钟 + target 09-29 + today 09-27 →
  墙上钟语义 created 日 = 09-22 → total=7、days_remaining=2 →
  current_day=6；day:6（order_index 6000/day:6 tag）入 today 面，
  day:7 不入。修前 Shanghai current=5 → day:6 被排除（红）。
- task.completed_at 消费面（:50/:183）**保持 UTC 语义不动**：三处写侧
  （task_service:716/execution_ingestor:627/execution_service:3130）均
  ``_utcnow()``，time_utils 模块注释亦点名 Task.completed_at 为 UTC naive
  存储（JOURNEY day5 实测 2026-09-26T00:19:04Z=上海 08:19 亦吻合）。
  对照控制组：completed_at=09-26 00:19:04（UTC naive=上海 09-26 08:19）
  的已完成任务在两时区用户的本地日均 09-26 ≠ today 09-27，不入
  「今日已完成」面——修后仍须保持。
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.daily_task_selection_service import (
    DailyTaskSelectionService,
    _is_today_relevant,
    _plan_current_day,
)

# 冻结服务钟：naive UTC 2026-09-27 03:00（上海 11:00 同日；UTC 用户同日）。
NOW_DAY6 = datetime(2026, 9, 27, 3, 0)
TODAY_DAY6 = date(2026, 9, 27)
# JOURNEY 计划 7917e864 的墙上钟 created_at（无时区后缀的本地钟存储值）。
PLAN_CREATED_WALL = datetime(2026, 9, 22, 21, 15, 30)
PLAN_TARGET = date(2026, 9, 29)


def _freeze_service_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.daily_task_selection_service.utcnow",
        lambda: NOW_DAY6,
        raising=False,
    )


def _wall_plan(**kwargs) -> Plan:
    return Plan(
        name="JOURNEY 7天冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        priority=PlanPriority.HIGH,
        target_date=PLAN_TARGET,
        created_at=PLAN_CREATED_WALL,  # 墙上钟存储语义
        **kwargs,
    )


def _day_task(user_id, plan_id, day: int, *, status=TaskStatus.PENDING) -> Task:
    return Task(
        user_id=user_id,
        plan_id=plan_id,
        title=f"Day {day} · 冲刺",
        type=TaskType.LEARNING,
        estimated_minutes=60,
        status=status,
        tags=[f"day:{day}"],
        order_index=day * 1000,
    )


def test_plan_current_day_reads_wall_clock_created_at():
    """created 09-22 21:15 墙上钟 + target 09-29 + today 09-27 → current_day=6。

    修前 +8 换算把 created 日推成 09-23 → total=6 → current_day=5（红）。
    """
    plan = _wall_plan()
    assert _plan_current_day(plan, TODAY_DAY6, "Asia/Shanghai") == 6


def test_plan_current_day_wall_semantics_is_timezone_independent():
    """墙上钟语义与时区无关：同一 stored plan 对 Shanghai/UTC 用户同算。

    修前 Shanghai +8（current 5）≠ UTC 恒等（current 6），一致性断言同红。
    """
    plan = _wall_plan()
    shanghai_day = _plan_current_day(plan, TODAY_DAY6, "Asia/Shanghai")
    utc_day = _plan_current_day(plan, TODAY_DAY6, "UTC")
    assert shanghai_day == 6
    assert utc_day == 6
    assert shanghai_day == utc_day


def test_day6_task_is_today_relevant_under_wall_clock_day_math():
    """day:6（order_index 6000）在 current_day=6 下必须 today-relevant。

    修前 current=5 → 6<=5 为假被排除（红，即 JOURNEY day6 门 /tasks/today
    返回 [] 的直接成因）。
    """
    plan = _wall_plan()
    day6 = Task(
        user_id=uuid4(),
        title="Day 6 · 冲刺",
        type=TaskType.LEARNING,
        estimated_minutes=60,
        tags=["day:6"],
        order_index=6000,
    )
    day7 = Task(
        user_id=uuid4(),
        title="Day 7 · 冲刺",
        type=TaskType.LEARNING,
        estimated_minutes=60,
        tags=["day:7"],
        order_index=7000,
    )
    assert _is_today_relevant(day6, TODAY_DAY6, plan=plan, tz_name="Asia/Shanghai") is True
    assert _is_today_relevant(day7, TODAY_DAY6, plan=plan, tz_name="Asia/Shanghai") is False


@pytest.mark.asyncio
async def test_today_face_includes_day6_for_shanghai_and_utc_users(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """端到端（select_tasks）：day:6 入 today 面，Shanghai 与 UTC 用户一致。

    32 天模板同构（day:N tag / order_index=N*1000）：冻结钟下两时区用户
    today 均 09-27，day 1-6 入面、day 7 不入。修前 Shanghai 用户的
    day:6 被 current=5 排除（红）。附带 completed_at UTC 语义控制组：
    JOURNEY day5 的 completed_at=09-26 00:19:04（UTC naive，上海 08:19）
    在两时区本地日均 09-26 ≠ today 09-27，不得以「今日已完成」混入。
    """
    _freeze_service_clock(monkeypatch)

    selections_by_tz: dict[str, set[str]] = {}
    for tz in ("Asia/Shanghai", "UTC"):
        user = User(username=f"wt602-{tz}-{uuid4().hex[:6]}", email=f"wt602-{uuid4().hex[:6]}@test.local", hashed_password="x")
        db_session.add(user)
        await db_session.flush()
        db_session.add(PushPreference(user_id=user.id, timezone=tz))
        plan = _wall_plan(user_id=user.id)
        db_session.add(plan)
        await db_session.flush()
        for day in range(1, 8):
            db_session.add(_day_task(user.id, plan.id, day))
        # JOURNEY day5 实测 completed_at（UTC naive 存储=上海 09-26 08:19）。
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"Day 5 · 已完成（{tz}）",
                type=TaskType.LEARNING,
                estimated_minutes=60,
                status=TaskStatus.COMPLETED,
                completed_at=datetime(2026, 9, 26, 0, 19, 4),
                tags=["day:5"],
                order_index=5 * 1000,
            )
        )
        await db_session.commit()

        selections = await DailyTaskSelectionService(db_session, redis=None).select_tasks(
            user_id=user.id,
            limit=50,
            include_completed_today=True,
            only_today_relevant=True,
        )
        selections_by_tz[tz] = {item.task.title for item in selections}

    for tz, titles in selections_by_tz.items():
        assert "Day 6 · 冲刺" in titles, f"[{tz}] day:6 必须入 today 面（修前 current=5 被排除）：{sorted(titles)}"
        assert "Day 7 · 冲刺" not in titles, f"[{tz}] day:7 超出 current_day=6，不得入面：{sorted(titles)}"
        assert f"Day 5 · 已完成（{tz}）" not in titles, (
            f"[{tz}] completed_at UTC 语义控制组：本地日 09-26 ≠ today 09-27，不得混入今日已完成面：{sorted(titles)}"
        )

    # 墙上钟语义与时区无关：两时区用户的 day 1-6 面必须逐任务一致。
    shanghai_titles = {
        title for title in selections_by_tz["Asia/Shanghai"] if title.startswith("Day ")
    }
    utc_titles = {title for title in selections_by_tz["UTC"] if title.startswith("Day ")}
    assert shanghai_titles == utc_titles == {f"Day {d} · 冲刺" for d in range(1, 7)}, (
        f"两时区用户的 today 面必须一致且恰为 day 1-6（墙上钟语义）：{selections_by_tz}"
    )
