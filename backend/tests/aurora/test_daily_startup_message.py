from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.models.calendar_event import CalendarEvent
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


class _WakeDecisionStub:
    def __init__(self, energy: str = "silent") -> None:
        self.energy = energy

    def to_payload(self) -> dict[str, str]:
        return {"energy": self.energy}


class _WakePolicyStub:
    async def evaluate(self, **kwargs):
        return _WakeDecisionStub()


async def _create_sprint_plan(db_session, *, completion_rate: float) -> tuple[User, Plan, date]:
    session_day = date.today()
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"daily_startup_{uuid4().hex[:8]}",
        email=f"daily_startup_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    plan = Plan(
        name="3天计算机网络冲刺",
        user_id=user_id,
        type=PlanType.SPRINT,
        subject="计算机网络",
        target_date=session_day + timedelta(days=1),
        daily_available_minutes=60,
        plan_stage=PlanStage.SPRINT,
        is_active=True,
        source_metadata={
            "exam_sprint_intake": {
                "goal_model": {
                    "days_left": 3,
                    "target_mode": "pass",
                },
            },
        },
    )
    db_session.add(user)
    db_session.add(plan)
    await db_session.flush()

    completed_count = int(10 * completion_rate)
    for index in range(10):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"Day 1 · 昨日任务 {index + 1}",
                type=TaskType.LEARNING,
                tags=["规划生成", "day:1"],
                estimated_minutes=10,
                difficulty=1,
                energy_cost=1,
                status=TaskStatus.COMPLETED if index < completed_count else TaskStatus.PENDING,
                order_index=1000 + index,
            )
        )

    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 2 · 传输层 - TCP 流量控制",
            type=TaskType.LEARNING,
            tags=["规划生成", "day:2"],
            estimated_minutes=45,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            order_index=2001,
            guide_json={
                "knowledge_nodes": ["TCP 流量控制"],
                "objective": "Day 2：优先拿下 TCP 流量控制。",
            },
        )
    )
    await db_session.commit()
    return user, plan, session_day


@pytest.mark.asyncio
async def test_daily_startup_positive_when_yesterday_completion_high(db_session):
    user, plan, session_day = await _create_sprint_plan(db_session, completion_rate=0.9)
    service = AuroraRuntimeV1Service(wake_policy_service=_WakePolicyStub())

    payload = await service.get_daily_startup_message(
        active_db=db_session,
        user_id=user.id,
        plan_id=plan.id,
        session_date=session_day,
    )

    assert payload["today_focus"] == "TCP 流量控制"
    assert payload["estimated_minutes"] == 45
    assert any(word in payload["message"] for word in ("很好", "不错", "顺利"))


@pytest.mark.asyncio
async def test_daily_startup_softens_when_yesterday_completion_low(db_session):
    user, plan, session_day = await _create_sprint_plan(db_session, completion_rate=0.3)
    service = AuroraRuntimeV1Service(wake_policy_service=_WakePolicyStub())

    payload = await service.get_daily_startup_message(
        active_db=db_session,
        user_id=user.id,
        plan_id=plan.id,
        session_date=session_day,
    )

    assert "轻一点" in payload["message"] or "缩" in payload["message"]
    assert payload["adjustment_reason"]


@pytest.mark.asyncio
async def test_daily_startup_mentions_previous_exam_weak_priority_boost(db_session):
    user, plan, session_day = await _create_sprint_plan(db_session, completion_rate=0.9)
    plan.source_metadata = {
        **(plan.source_metadata or {}),
        "day_highlights": {
            "day": 2,
            "recommendation": "根据你上次的考后复盘，TCP 相关部分需要额外加强，我已经把相关节点的优先级提高了。",
        },
    }
    await db_session.commit()

    service = AuroraRuntimeV1Service(wake_policy_service=_WakePolicyStub())
    payload = await service.get_daily_startup_message(
        active_db=db_session,
        user_id=user.id,
        plan_id=plan.id,
        session_date=session_day,
    )

    assert "根据你上次的考后复盘" in payload["message"]
    assert "TCP" in payload["message"]
    assert "优先级提高" in payload["message"]


@pytest.mark.asyncio
async def test_daily_startup_mentions_calendar_conflict_with_specific_time(db_session):
    user, plan, session_day = await _create_sprint_plan(db_session, completion_rate=0.9)
    db_session.add(
        CalendarEvent(
            user_id=user.id,
            title="高数考试",
            start_time=datetime.combine(session_day, datetime.min.time()).replace(hour=14),
            end_time=datetime.combine(session_day, datetime.min.time()).replace(hour=15, minute=30),
        )
    )
    await db_session.commit()

    service = AuroraRuntimeV1Service(wake_policy_service=_WakePolicyStub())
    payload = await service.get_daily_startup_message(
        active_db=db_session,
        user_id=user.id,
        plan_id=plan.id,
        session_date=session_day,
    )

    assert "14:00-15:30" in payload["message"]
    assert "高数考试" in payload["message"]
    assert "09:00-10:00" in payload["message"]
    assert payload["calendar_note"]


@pytest.mark.asyncio
async def test_daily_startup_mentions_calendar_exam_countdown(db_session):
    user, plan, session_day = await _create_sprint_plan(db_session, completion_rate=0.9)
    db_session.add(
        CalendarEvent(
            user_id=user.id,
            title="计算机网络考试",
            start_time=datetime.combine(session_day + timedelta(days=1), datetime.min.time()).replace(hour=9),
            end_time=datetime.combine(session_day + timedelta(days=1), datetime.min.time()).replace(hour=11),
        )
    )
    await db_session.commit()

    service = AuroraRuntimeV1Service(wake_policy_service=_WakePolicyStub())
    payload = await service.get_daily_startup_message(
        active_db=db_session,
        user_id=user.id,
        plan_id=plan.id,
        session_date=session_day,
    )

    assert "距「计算机网络考试」还有 1 天" in payload["message"]
    assert payload["calendar_note"]
