from datetime import timezone, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.achievement import UserStreakStats
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.progress_narrative_service import ProgressNarrativeService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_progress_snapshot_includes_task_and_streak_highlights(db_session):
    user_id = uuid4()
    now = _utcnow()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="高数复习",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
        actual_minutes=35,
        difficulty=3,
        energy_cost=2,
        tags=[],
        completed_at=now - timedelta(days=1),
    )
    study = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=uuid4(),
        task_id=task.id,
        study_minutes=35,
        mastery_delta=12.0,
        record_type="task_complete",
    )
    streak = UserStreakStats(
        user_id=user_id,
        current_streak=12,
        max_streak=12,
        total_checkin_days=30,
    )
    db_session.add_all([user, task, study, streak])
    await db_session.commit()

    service = ProgressNarrativeService(db_session, redis=None)
    snapshot = await service.build_snapshot(str(user_id))

    assert snapshot.highlights
    assert snapshot.comparisons["tasks_completed"]["current"] == 1
    assert snapshot.streak_info["current_streak"] == 12
