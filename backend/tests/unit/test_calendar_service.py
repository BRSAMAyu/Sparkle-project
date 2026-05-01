from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.models.calendar_event import CalendarEvent
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.calendar_service import CalendarService


@pytest.mark.asyncio
async def test_calendar_service_builds_busy_free_context_and_time_conflicts(db_session, test_user):
    anchor = date(2026, 5, 1)
    exam_day = anchor + timedelta(days=2)
    db_session.add_all(
        [
            CalendarEvent(
                user_id=test_user.id,
                title="高数考试",
                start_time=datetime.combine(exam_day, datetime.min.time()).replace(hour=7),
                end_time=datetime.combine(exam_day, datetime.min.time()).replace(hour=21),
                source="manual",
                source_metadata={"kind": "exam"},
            ),
            Plan(
                user_id=test_user.id,
                name="高数冲刺",
                type=PlanType.SPRINT,
                plan_stage=PlanStage.SPRINT,
                target_date=exam_day,
                subject="高数",
                daily_available_minutes=180,
                is_active=True,
            ),
            Task(
                user_id=test_user.id,
                title="考前整卷复盘",
                type=TaskType.TRAINING,
                tags=[],
                estimated_minutes=120,
                difficulty=3,
                energy_cost=3,
                status=TaskStatus.PENDING,
                due_date=exam_day,
                order_index=1,
            ),
        ]
    )
    await db_session.commit()

    context = await CalendarService(db_session).get_busy_free_context(
        test_user.id,
        start_date=anchor,
        days=7,
    )

    assert context["time_blocks_by_date"][exam_day.isoformat()] == [
        {"start": "21:00", "end": "22:00"},
    ]
    assert context["available_minutes_by_date"][exam_day.isoformat()] == 60
    assert context["exam_urgency"]["days_left"] == 2
    assert context["exam_urgency"]["title"] == "高数考试"
    assert context["next_time_conflict"]["message"] == "时间可能不够"
    assert {item["type"] for item in context["time_conflicts"]} >= {
        "task_deadline",
        "plan_deadline",
    }
