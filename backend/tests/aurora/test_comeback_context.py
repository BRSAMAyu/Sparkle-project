from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.models.chat import ChatMessage, MessageRole
from app.models.focus import FocusSession, FocusStatus, FocusType
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
