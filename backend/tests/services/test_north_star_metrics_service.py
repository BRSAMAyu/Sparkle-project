from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.north_star_metrics import NorthStarMetricEvent
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.exam_sprint_review_service import ExamSprintReviewService
from app.services.north_star_metrics_service import (
    NorthStarMetricsService,
    NorthStarMetricType,
)


async def _create_user(db_session: AsyncSession, username: str = "north_star_user") -> User:
    user = User(username=username, email=f"{username}@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_sprint_plan(db_session: AsyncSession, user: User, *, target_date: date | None = None) -> Plan:
    plan = Plan(
        user_id=user.id,
        name="7-day operating systems sprint",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="Operating Systems",
        target_date=target_date or (date.today() + timedelta(days=7)),
        daily_available_minutes=90,
        progress=0.0,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest.mark.asyncio
async def test_north_star_metric_writes_are_idempotent_and_aggregated(db_session: AsyncSession):
    user = await _create_user(db_session)
    plan = await _create_sprint_plan(db_session, user)
    service = NorthStarMetricsService(db_session)

    await service.record_exam_pass_probability(
        user_id=user.id,
        plan_id=plan.id,
        pass_probability=0.42,
        source="test",
        occurred_at=datetime(2026, 5, 1, 9, 0, 0),
        payload={"target_mode": "pass"},
    )
    await service.record_exam_pass_probability(
        user_id=user.id,
        plan_id=plan.id,
        pass_probability=0.64,
        source="test",
        occurred_at=datetime(2026, 5, 1, 10, 0, 0),
        payload={"target_mode": "pass", "recomputed": True},
    )
    await service.record_exam_outcome(
        user_id=user.id,
        plan_id=plan.id,
        passed=True,
        source="post_exam_review",
        occurred_at=datetime(2026, 5, 1, 12, 0, 0),
    )
    await service.record_seven_day_goal_started(
        user_id=user.id,
        plan_id=plan.id,
        source="exam_sprint_intake",
        occurred_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    await service.record_seven_day_goal_completed(
        user_id=user.id,
        plan_id=plan.id,
        source="exam_sprint_completion",
        occurred_at=datetime(2026, 5, 1, 13, 0, 0),
    )

    count_result = await db_session.execute(select(func.count(NorthStarMetricEvent.id)))
    assert count_result.scalar_one() == 4

    trend = await service.get_trends(user_id=user.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 1))
    assert trend.summary["latest_exam_pass_probability"] == 0.64
    assert trend.summary["exam_pass_outcome_rate"] == 1.0
    assert trend.summary["seven_day_goal_completion_rate"] == 1.0
    assert trend.series[0].exam_pass_probability == 0.64
    assert trend.series[0].exam_pass_outcome_rate == 1.0
    assert trend.series[0].seven_day_goal_completion_rate == 1.0


@pytest.mark.asyncio
async def test_cold_start_milestones_track_first_value_once(db_session: AsyncSession):
    user = await _create_user(db_session, username="north_star_cold_start_user")
    plan = await _create_sprint_plan(db_session, user)
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="First meaningful task",
        type=TaskType.LEARNING,
        estimated_minutes=15,
        difficulty=1,
        energy_cost=1,
        order_index=1,
        status=TaskStatus.COMPLETED,
        completed_at=datetime(2026, 5, 1, 9, 30, 0),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    service = NorthStarMetricsService(db_session)

    await service.record_cold_start_milestone(
        user_id=user.id,
        milestone=NorthStarMetricType.FIRST_GOAL_PROFILE_CREATED,
        source="test",
        occurred_at=datetime(2026, 5, 1, 9, 0, 0),
        payload={"goal": "计算机网络"},
    )
    await service.record_cold_start_milestone(
        user_id=user.id,
        milestone=NorthStarMetricType.FIRST_GOAL_PROFILE_CREATED,
        source="test_second_write",
        occurred_at=datetime(2026, 5, 2, 9, 0, 0),
        payload={"goal": "should not replace first event"},
    )
    await service.record_cold_start_milestone(
        user_id=user.id,
        milestone=NorthStarMetricType.FIRST_AURORA_BASELINE_FORMED,
        source="test",
        occurred_at=datetime(2026, 5, 1, 9, 5, 0),
    )
    await service.record_cold_start_milestone(
        user_id=user.id,
        milestone=NorthStarMetricType.FIRST_PLAN_REQUESTED,
        source="test",
        occurred_at=datetime(2026, 5, 1, 9, 10, 0),
        plan_id=plan.id,
    )
    await service.record_cold_start_milestone(
        user_id=user.id,
        milestone=NorthStarMetricType.FIRST_TASK_COMPLETED,
        source="test",
        occurred_at=datetime(2026, 5, 1, 9, 30, 0),
        plan_id=plan.id,
        task_id=task.id,
    )

    trend = await service.get_trends(user_id=user.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 2))

    assert trend.summary["first_goal_profiles_created"] == 1
    assert trend.summary["aurora_baselines_formed"] == 1
    assert trend.summary["first_plan_requests"] == 1
    assert trend.summary["first_tasks_completed"] == 1
    assert trend.summary["cold_start_first_value_completion_rate"] == 1.0
    assert trend.series[0].first_goal_profiles_created == 1
    assert trend.series[0].aurora_baselines_formed == 1
    assert trend.series[0].first_plan_requests == 1
    assert trend.series[0].first_tasks_completed == 1
    assert trend.series[1].first_goal_profiles_created == 0


@pytest.mark.asyncio
async def test_sprint_completion_check_records_seven_day_goal_metric(db_session: AsyncSession):
    user = await _create_user(db_session, username="north_star_sprint_user")
    plan = await _create_sprint_plan(db_session, user)
    for day in range(1, 8):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"Day {day} task",
                type=TaskType.LEARNING,
                tags=["exam_sprint", f"day:{day}"],
                guide_json={"day": day},
                estimated_minutes=30,
                actual_minutes=30,
                difficulty=1,
                energy_cost=1,
                order_index=day * 1000,
                status=TaskStatus.COMPLETED,
                completed_at=datetime(2026, 5, day, 8, 0, 0),
            )
        )
    await db_session.commit()

    response = await ExamSprintReviewService(db_session, redis_client=None).check_sprint_completion(
        user_id=user.id,
        plan_id=plan.id,
    )

    assert response.completed is True
    event_result = await db_session.execute(
        select(NorthStarMetricEvent).where(
            NorthStarMetricEvent.plan_id == plan.id,
            NorthStarMetricEvent.event_type == "seven_day_goal_completed",
        )
    )
    event = event_result.scalar_one()
    assert event.value_float == 1.0
    assert event.payload["completed_tasks"] == 7
