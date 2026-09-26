from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.error_book import ErrorRecord
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.struggle_signal_aggregator import StruggleSignalAggregator

# wt590 冻结钟（CI run 36268994104 族C）：aggregator 的「今日」窗口按用户本地日
# （V3-FIX-211，缺省 Asia/Shanghai）定界——原用例按 UTC 日锚定播种，宿主钟使
# UTC 日 ≠ 上海本地日时（每日 16:00–24:00Z 窗口，恰为舰队夜间 CI 段）今日窗口
# 捕空、skip_rate 掉 0.0。沿双冻结钟族判例（wt559 29cdf7ae）：冻结服务器
# UTC 钟 NOW=2026-09-25 20:00Z（上海本地 09-26 04:00，日界已跨、与 UTC 宿主日
# 09-25 可区分）+ 用户显式钉 Asia/Shanghai，播种/期望按新契约手算，与宿主机
# TZ 无关。窗口推导（上海 09-26）：
# - Task.created_at/updated_at（UTC 存储列）：[09-25 16:00Z, 09-26 16:00Z)
# - FocusSession.start_time（墙上钟列）：[09-26 00:00, 09-27 00:00)
# - overdue：due_date < 09-26；ErrorRecord 3d：now.date()=09-25 的 09-23/24/25
_NOW_NAIVE_UTC = datetime(2026, 9, 25, 20, 0)
_LOCAL_TODAY = date(2026, 9, 26)


async def _create_user_and_plan(db_session) -> tuple[User, Plan]:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="Thermo Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add_all([user, plan])
    await db_session.flush()
    return user, plan


@pytest.mark.asyncio
async def test_compute_struggle_score_skip_rate_0_7_triggers_even_before_other_signals(db_session) -> None:
    user, plan = await _create_user_and_plan(db_session)
    now = datetime.utcnow()
    db_session.add_all(
        [
            Task(
                id=uuid4(),
                user_id=user.id,
                plan_id=plan.id,
                title=f"skip-only task {index}",
                type=TaskType.LEARNING,
                status=TaskStatus.ABANDONED if index < 7 else TaskStatus.PENDING,
                estimated_minutes=20,
                difficulty=2,
                energy_cost=2,
                created_at=now,
                updated_at=now,
            )
            for index in range(10)
        ]
    )
    await db_session.commit()

    context = await StruggleSignalAggregator().get_struggle_context(
        db_session,
        user_id=str(user.id),
        plan_id=str(plan.id),
    )

    assert context["skip_rate"] == 0.7
    assert context["struggle_score"] > 0.6


@pytest.mark.asyncio
async def test_compute_struggle_score_high_skip_rate_crosses_trigger_threshold(db_session, monkeypatch) -> None:
    # 冻结 aggregator 的 utcnow + 钉用户时区（窗口推导见模块头注释）。
    monkeypatch.setattr(
        "app.services.struggle_signal_aggregator._utcnow",
        lambda: _NOW_NAIVE_UTC,
        raising=False,
    )
    user, plan = await _create_user_and_plan(db_session)
    db_session.add(PushPreference(user_id=user.id, timezone="Asia/Shanghai"))

    # V3-FIX-120 的「当日正午」锚升级为冻结本地日窗口内锚：今日任务播种在
    # 上海 09-26 02:00（=09-25 18:00Z），恒落 [09-25 16:00Z, 09-26 16:00Z) 窗口。
    today_created = datetime(2026, 9, 25, 18, 0)

    today_tasks = []
    for index in range(10):
        created = today_created + timedelta(minutes=index)
        today_tasks.append(
            Task(
                id=uuid4(),
                user_id=user.id,
                plan_id=plan.id,
                title=f"today task {index}",
                type=TaskType.LEARNING,
                status=TaskStatus.ABANDONED if index < 7 else TaskStatus.PENDING,
                estimated_minutes=20,
                difficulty=2,
                energy_cost=2,
                created_at=created,
                updated_at=created + timedelta(minutes=30),
            )
        )

    overdue_tasks = [
        Task(
            id=uuid4(),
            user_id=user.id,
            plan_id=plan.id,
            title=f"overdue task {index}",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            estimated_minutes=20,
            difficulty=2,
            energy_cost=2,
            due_date=_LOCAL_TODAY - timedelta(days=1),
            created_at=today_created - timedelta(days=2),
            updated_at=today_created - timedelta(days=2),
        )
        for index in range(3)
    ]
    db_session.add_all(today_tasks + overdue_tasks)

    sessions = []
    for index in range(10):
        duration = 3 if index < 7 else 25
        # 墙上钟列（用户本地 09-26 凌晨 01:0x），全部落 [09-26 00:00, 09-27 00:00)。
        start = datetime(2026, 9, 26, 1, 0) + timedelta(minutes=index)
        sessions.append(
            FocusSession(
                user_id=user.id,
                task_id=today_tasks[index].id,
                start_time=start,
                end_time=start + timedelta(minutes=duration),
                duration_minutes=duration,
                focus_type=FocusType.POMODORO,
                status=FocusStatus.COMPLETED,
            )
        )
    db_session.add_all(sessions)

    # ErrorRecord 3d 窗口按冻结 UTC 日期 09-25 展开：昨日 09-24 一条（带概念）、
    # 今日 09-25 两条——与原用例 (day2, day1, day0) 计数布局一致。
    yesterday_start = datetime(2026, 9, 24, 0, 0)
    today_start = datetime(2026, 9, 25, 0, 0)
    db_session.add_all(
        [
            ErrorRecord(
                id=uuid4(),
                user_id=user.id,
                subject_code="physics",
                chapter="热力学过程",
                question_text=f"q-{index}",
                created_at=created_at,
                updated_at=created_at,
                suggested_concepts=["热力学过程"] if index == 0 else [],
                is_deleted=False,
            )
            for index, created_at in enumerate(
                [
                    yesterday_start + timedelta(hours=12),
                    today_start + timedelta(hours=1),
                    today_start + timedelta(hours=2),
                ]
            )
        ]
    )
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            facts={"adaptive_meta": {"struggle_streak_since_last_replan": 3}},
            milestones=[],
            task_index={},
            task_summaries=[],
            feedback_log=[],
            constraints={},
            status=PlanStateStatus.ACTIVE.value,
        )
    )
    await db_session.commit()

    aggregator = StruggleSignalAggregator()
    context = await aggregator.get_struggle_context(db_session, user_id=str(user.id), plan_id=str(plan.id))

    assert context["skip_rate"] == 0.7
    assert context["primary_signal"] == "task_skip"
    assert context["struggle_score"] > 0.6
    assert "热力学过程" in context["stuck_concepts"]


@pytest.mark.asyncio
async def test_compute_struggle_score_all_zero_signals_stays_normal(db_session) -> None:
    user, plan = await _create_user_and_plan(db_session)
    await db_session.commit()

    score = await StruggleSignalAggregator().compute_struggle_score(
        db_session,
        redis=None,
        user_id=str(user.id),
        plan_id=str(plan.id),
    )

    assert score < 0.3
