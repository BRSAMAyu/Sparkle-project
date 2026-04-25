from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


async def _seed_comeback_fixture(
    db_session,
    *,
    inactive_days: int,
    days_remaining: int,
) -> tuple[User, Plan]:
    user = User(
        id=uuid4(),
        username=f"comeback_{uuid4().hex[:8]}",
        email=f"comeback_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        last_login_at=datetime.now(UTC) - timedelta(days=inactive_days),
    )
    plan = Plan(
        name="7天计算机网络冲刺",
        user_id=user.id,
        type=PlanType.SPRINT,
        subject="计算机网络",
        target_date=date.today() + timedelta(days=days_remaining),
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
