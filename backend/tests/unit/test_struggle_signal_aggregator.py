from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import uuid4

import pytest

from app.models.error_book import ErrorRecord
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.struggle_signal_aggregator import StruggleSignalAggregator


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
async def test_compute_struggle_score_high_skip_rate_crosses_trigger_threshold(db_session) -> None:
    user, plan = await _create_user_and_plan(db_session)
    now = datetime.utcnow()

    today_tasks = []
    for index in range(10):
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
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=30),
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
            due_date=date.today() - timedelta(days=1),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        for index in range(3)
    ]
    db_session.add_all(today_tasks + overdue_tasks)

    sessions = []
    for index in range(10):
        duration = 3 if index < 7 else 25
        sessions.append(
            FocusSession(
                user_id=user.id,
                task_id=today_tasks[index].id,
                start_time=now - timedelta(minutes=60 - index),
                end_time=now - timedelta(minutes=60 - index - duration),
                duration_minutes=duration,
                focus_type=FocusType.POMODORO,
                status=FocusStatus.COMPLETED,
            )
        )
    db_session.add_all(sessions)

    today_start = datetime.combine(now.date(), time.min)
    yesterday_start = today_start - timedelta(days=1)
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
