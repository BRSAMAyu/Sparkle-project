from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.galaxy import StudyRecord
from app.models.memory import EpisodicMemory, Scene
from app.models.task import Task, TaskStatus, TaskType
from tests.unit.scene_test_helpers import make_scene


def make_study_record(
    *,
    user_id: UUID,
    node_id: UUID,
    created_at: datetime,
    study_minutes: int = 60,
    mastery_delta: float = 0.1,
) -> StudyRecord:
    return StudyRecord(
        user_id=user_id,
        node_id=node_id,
        task_id=None,
        study_minutes=study_minutes,
        mastery_delta=mastery_delta,
        initial_mastery=0.2,
        record_type="task_complete",
        created_at=created_at,
        updated_at=created_at,
    )


def make_focus_session(
    *,
    user_id: UUID,
    end_time: datetime,
    duration_minutes: int = 25,
) -> FocusSession:
    start_time = end_time - timedelta(minutes=duration_minutes)
    return FocusSession(
        user_id=user_id,
        task_id=None,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        focus_type=FocusType.POMODORO,
        status=FocusStatus.COMPLETED,
        created_at=start_time,
        updated_at=end_time,
    )


def make_task(
    *,
    user_id: UUID,
    created_at: datetime,
    due_date: date | None = None,
    completed_at: datetime | None = None,
    plan_id: UUID | None = None,
    knowledge_node_id: UUID | None = None,
    status: TaskStatus | None = None,
    title: str = "复盘任务",
) -> Task:
    resolved_status = status or (TaskStatus.COMPLETED if completed_at is not None else TaskStatus.PENDING)
    return Task(
        user_id=user_id,
        plan_id=plan_id,
        title=title,
        type=TaskType.LEARNING,
        tags=["stage27:test"],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        status=resolved_status,
        completed_at=completed_at,
        priority=1,
        order_index=1,
        due_date=due_date,
        knowledge_node_id=knowledge_node_id,
        created_at=created_at,
        updated_at=completed_at or created_at,
    )


def make_reflection(
    *,
    user_id: UUID,
    occurred_at: datetime,
    category: str = "plan_stall",
    summary: str | None = None,
) -> EpisodicMemory:
    return EpisodicMemory(
        user_id=user_id,
        summary=summary or f"reflection:{category}",
        source_type="reflection",
        source_id=f"reflection-{category}",
        source_lane="inferred_extraction",
        subject_type="self",
        occurred_at=occurred_at,
        tags=["stage25:reflection", f"reflection_category:{category}"],
        evidence_refs=[{"type": "summary", "id": f"reflection-{category}", "schema_version": "stage27.test.v1"}],
        created_at=occurred_at,
        updated_at=occurred_at,
    )


def make_scene_for_day(
    *,
    user_id: UUID,
    when: datetime,
    quality_score: float = 0.82,
) -> Scene:
    return make_scene(
        user_id=user_id,
        member_memory_ids=[str(uuid4()), str(uuid4())],
        quality_score=quality_score,
        time_start=when - timedelta(minutes=30),
        time_end=when,
    )


async def seed_foresight_history(
    db_session,
    *,
    user_id: UUID,
    days: int,
    start_day: datetime,
    node_id: UUID | None = None,
    recent_drop: bool = False,
    include_reflections: bool = True,
    include_scenes: bool = True,
) -> UUID:
    resolved_node_id = node_id or uuid4()
    plan_id = uuid4()
    for index in range(days):
        current = start_day + timedelta(days=index)
        study_minutes = 90 if not recent_drop or index < days - 3 else 15
        db_session.add(
            make_study_record(
                user_id=user_id,
                node_id=resolved_node_id,
                created_at=current,
                study_minutes=study_minutes,
                mastery_delta=0.08 if study_minutes >= 60 else 0.02,
            )
        )
        db_session.add(make_focus_session(user_id=user_id, end_time=current + timedelta(hours=1)))
        completed_at = current + timedelta(hours=2) if index % 2 == 0 else None
        db_session.add(
            make_task(
                user_id=user_id,
                created_at=current,
                due_date=current.date(),
                completed_at=completed_at,
                plan_id=plan_id,
                knowledge_node_id=resolved_node_id,
                title=f"任务-{index}",
            )
        )
        if include_reflections and index % 3 == 0:
            db_session.add(
                make_reflection(
                    user_id=user_id,
                    occurred_at=current + timedelta(hours=3),
                    category="overload" if recent_drop and index >= days - 3 else "plan_stall",
                )
            )
        if include_scenes and index % 2 == 0:
            db_session.add(
                make_scene(
                    user_id=user_id,
                    member_memory_ids=[str(uuid4()), str(uuid4())],
                    quality_score=0.9 if study_minutes >= 60 else 0.65,
                    time_start=current + timedelta(minutes=15),
                    time_end=current + timedelta(hours=1, minutes=15),
                )
            )
    await db_session.commit()
    return resolved_node_id
