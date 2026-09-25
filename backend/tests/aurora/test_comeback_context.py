from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.goal import Goal
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


async def _seed_comeback_fixture(
    db_session,
    *,
    inactive_days: int,
    days_remaining: int,
) -> tuple[User, Plan]:
    now = datetime.now(UTC).replace(tzinfo=None)
    user = User(
        id=uuid4(),
        username=f"comeback_{uuid4().hex[:8]}",
        email=f"comeback_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        last_login_at=now - timedelta(days=inactive_days),
    )
    plan = Plan(
        name="7天计算机网络冲刺",
        user_id=user.id,
        type=PlanType.SPRINT,
        subject="计算机网络",
        target_date=datetime.now(UTC).date() + timedelta(days=days_remaining),
        plan_stage=PlanStage.SPRINT,
        is_active=True,
        is_primary=True,
    )
    db_session.add_all([user, plan])
    await db_session.flush()

    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 4 · TCP 流量控制",
            type=TaskType.LEARNING,
            tags=["规划生成", "day:4"],
            estimated_minutes=45,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            order_index=1,
            guide_json={
                "knowledge_nodes": ["TCP 流量控制"],
                "objective": "先把 TCP 流量控制和滑动窗口过一遍。",
            },
        )
    )
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 3 · 已完成任务",
            type=TaskType.LEARNING,
            tags=["规划生成", "day:3"],
            estimated_minutes=30,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.COMPLETED,
            completed_at=now - timedelta(days=inactive_days),
            order_index=2,
        )
    )
    await db_session.commit()
    return user, plan


async def _seed_chat_continuity_fixture(
    db_session,
    *,
    inactive_delta: timedelta,
    last_assistant_question: str = "那你想先从函数极限还是导数开始？",
) -> tuple[User, str]:
    now = datetime.now(UTC).replace(tzinfo=None)
    user = User(
        id=uuid4(),
        username=f"continuity_{uuid4().hex[:8]}",
        email=f"continuity_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    session_id = uuid4()
    user_message_at = now - inactive_delta
    assistant_message_at = user_message_at + timedelta(minutes=1)
    db_session.add(user)
    db_session.add(
        ChatSession(
            id=session_id,
            user_id=user.id,
            title="函数极限复盘",
            last_message_at=assistant_message_at,
        )
    )
    db_session.add(
        ChatMessage(
            user_id=user.id,
            session_id=session_id,
            role=MessageRole.USER,
            content="我想继续复盘函数极限，刚才卡在夹逼准则。",
            created_at=user_message_at,
        )
    )
    db_session.add(
        ChatMessage(
            user_id=user.id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=last_assistant_question,
            created_at=assistant_message_at,
        )
    )
    await db_session.commit()
    return user, str(session_id)


@pytest.mark.asyncio
async def test_get_comeback_context_returns_warm_message_after_six_days(db_session):
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=6,
        days_remaining=3,
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["plan_id"] == str(plan.id)
    assert payload["days_away"] == 6
    assert payload["days_remaining"] == 3
    assert payload["next_task_title"] == "Day 4 · TCP 流量控制"
    assert payload["recent_task_summary"] == "TCP 流量控制"
    assert "3 天" in payload["message"]
    assert "来得及" in payload["message"]
    assert "30分钟保底版" in payload["message"]


@pytest.mark.asyncio
async def test_get_comeback_context_light_resume_after_two_hours(db_session):
    user, session_id = await _seed_chat_continuity_fixture(
        db_session,
        inactive_delta=timedelta(hours=2),
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
        include_short_gaps=True,
    )

    assert payload is not None
    assert payload["comeback_kind"] == "light_resume"
    assert payload["conversation_id"] == session_id
    assert "函数极限" in payload["topic_summary"]
    assert "上次 Aurora 问的是" in payload["message"]
    assert payload["unfinished_items"][0]["type"] == "pending_question"


@pytest.mark.asyncio
async def test_get_comeback_context_silent_resume_under_thirty_minutes(db_session):
    user, session_id = await _seed_chat_continuity_fixture(
        db_session,
        inactive_delta=timedelta(minutes=12),
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
        include_short_gaps=True,
    )

    assert payload is not None
    assert payload["comeback_kind"] == "silent_resume"
    assert payload["conversation_id"] == session_id
    assert payload["message"] == ""
    assert payload["should_show_message"] is False


@pytest.mark.asyncio
async def test_get_comeback_context_returns_none_when_user_was_active_two_days_ago(db_session):
    user, _plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=2,
        days_remaining=3,
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is None


@pytest.mark.asyncio
async def test_get_comeback_context_triggers_at_three_day_threshold(db_session):
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=3,
        days_remaining=3,
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["plan_id"] == str(plan.id)
    assert payload["days_away"] == 3


@pytest.mark.asyncio
async def test_get_comeback_context_uses_recent_task_completion_over_login(db_session):
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=8,
        days_remaining=3,
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    for offset in range(1, 6):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"连续学习任务 {offset}",
                type=TaskType.LEARNING,
                tags=["规划生成", "active"],
                estimated_minutes=20,
                difficulty=1,
                energy_cost=1,
                status=TaskStatus.COMPLETED,
                completed_at=now - timedelta(days=offset),
                order_index=10 + offset,
            )
        )
    await db_session.commit()
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is None


@pytest.mark.asyncio
async def test_get_comeback_context_does_not_trigger_when_login_two_days_and_task_yesterday(db_session):
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=4,
        days_remaining=3,
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    user.last_login_at = now - timedelta(days=2)
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="昨天完成的真实任务",
            type=TaskType.LEARNING,
            tags=["active"],
            estimated_minutes=20,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.COMPLETED,
            completed_at=now - timedelta(days=1),
            order_index=20,
        )
    )
    await db_session.commit()
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is None


@pytest.mark.asyncio
async def test_get_comeback_context_uses_recent_user_message_over_login(db_session):
    user, _plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=8,
        days_remaining=3,
    )
    db_session.add(
        ChatMessage(
            user_id=user.id,
            role=MessageRole.USER,
            content="我今天已经回来复习了",
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        )
    )
    await db_session.commit()
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is None


@pytest.mark.asyncio
async def test_get_comeback_context_triggers_when_all_real_activity_is_four_days_old(db_session):
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=4,
        days_remaining=3,
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    user.last_login_at = now - timedelta(days=2)
    db_session.add(
        ChatMessage(
            user_id=user.id,
            role=MessageRole.USER,
            content="四天前还在问计划",
            created_at=now - timedelta(days=4, hours=2),
        )
    )
    db_session.add(
        FocusSession(
            user_id=user.id,
            start_time=now - timedelta(days=4, hours=1, minutes=30),
            end_time=now - timedelta(days=4, hours=1),
            duration_minutes=30,
            focus_type=FocusType.POMODORO,
            status=FocusStatus.COMPLETED,
        )
    )
    await db_session.commit()
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["plan_id"] == str(plan.id)
    assert payload["days_away"] >= 4


# ── A-07: 3/7/14-day test clock + goal-state restore ──────────────────────────


async def _append_task(
    db_session,
    *,
    user,
    plan,
    title: str,
    status: TaskStatus,
    due_offset_days: int | None,
    order_index: int,
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title=title,
            type=TaskType.LEARNING,
            estimated_minutes=30,
            difficulty=1,
            energy_cost=1,
            status=status,
            due_date=now.date() + timedelta(days=due_offset_days)
            if due_offset_days is not None
            else None,
            order_index=order_index,
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_seven_day_clock_with_live_plan_keeps_framing_and_surfaces_goal_state(db_session):
    """7-day clock，计划窗口未过期：正常接回框架 + goal_state 真实呈现。"""
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=7,
        days_remaining=5,
    )
    db_session.add(
        Goal(
            user_id=user.id,
            title="期末计算机网络冲 85 分",
            goal_type="exam",
            status="active",
            is_primary=True,
            plan_id=plan.id,
            # 真源读数可能停 0（R2-A 跟踪中）：必须原样上报，不得修饰。
            progress=0.0,
        )
    )
    await db_session.commit()
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["days_away"] == 7
    # 窗口未过期：不宣称过期，仍按剩余天数接回（回归合理）。
    assert payload["plan_expired"] is False
    assert payload["stale_focus"] is False
    assert "还剩 5 天" in payload["message"]
    # goal_state：真源投影 + 任务账本诚实进度（1 完成 / 2 总数）。
    goal_state = payload["goal_state"]
    assert goal_state["title"] == "期末计算机网络冲 85 分"
    assert goal_state["progress"] == 0.0
    ledger = goal_state["ledger"]
    assert ledger["completed"] == 1
    assert ledger["total"] == 2
    assert ledger["ratio"] == 0.5


@pytest.mark.asyncio
async def test_fourteen_day_clock_does_not_present_stale_task_as_current(db_session):
    """14-day clock + 计划窗口已过：陈旧任务不得包装成当前最优步。"""
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=14,
        days_remaining=-10,
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["days_away"] == 14
    assert payload["plan_expired"] is True
    assert payload["stale_focus"] is True
    message = payload["message"]
    # 诚实红线：不宣称"还来得及/收尾窗口"，不把陈旧任务说成"最近最适合"。
    assert "最近最适合重新捡起来" not in message
    assert "来得及" not in message
    assert "收尾窗口" not in message
    # 诚实呈报 + 指向重新校准（零羞耻、零诊断表述）。
    assert "已经结束" in message
    assert "重新校准" in message
    assert "焦虑" not in message and "压力" not in message


@pytest.mark.asyncio
async def test_three_day_clock_with_long_overdue_task_marks_stale_focus(db_session):
    """3-day clock 阈值触发 + 焦点任务逾期 5 天：标记 stale 且不称"最适合"。"""
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=3,
        days_remaining=6,
    )
    await _append_task(
        db_session,
        user=user,
        plan=plan,
        title="Day 1 · 很久前的欠账",
        status=TaskStatus.PENDING,
        due_offset_days=-5,
        order_index=0,
    )
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["plan_expired"] is False
    assert payload["stale_focus"] is True
    assert payload["next_task_overdue_days"] == 5
    message = payload["message"]
    assert "最近最适合重新捡起来" not in message
    # 陈旧任务如实标注逾期天数，给出"也可以挑一小步"的低压力出路。
    assert "原定 5 天前" in message
    assert "也可以先挑今天最顺的一小步" in message


@pytest.mark.asyncio
async def test_goal_linked_plan_prefers_linked_goal_for_state(db_session):
    """plan.goal_id 挂接的目标优先于全局 primary 目标（读侧投影）。"""
    user, plan = await _seed_comeback_fixture(
        db_session,
        inactive_days=5,
        days_remaining=4,
    )
    db_session.add(
        Goal(
            user_id=user.id,
            title="全局主目标",
            status="active",
            is_primary=True,
        )
    )
    linked_goal = Goal(
        user_id=user.id,
        title="挂接目标",
        status="active",
        is_primary=False,
    )
    db_session.add(linked_goal)
    await db_session.flush()
    plan.goal_id = linked_goal.id
    await db_session.commit()
    service = AuroraRuntimeV1Service()

    payload = await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
    )

    assert payload is not None
    assert payload["goal_state"]["goal_id"] == str(linked_goal.id)
    assert payload["goal_state"]["title"] == "挂接目标"
