from datetime import date
from uuid import uuid4

import pytest

from app.api.v1 import events as events_api
from app.models.nightly_review import NightlyReview
from app.models.task import Task, TaskType, TaskStatus
from app.models.user import User
from app.schemas.events import EvidenceResolveRequest
from app.schemas.intervention import EvidenceRef


@pytest.mark.asyncio
async def test_evidence_resolve_task_and_summary(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        user_id=user_id,
        title="Finish unit tests",
        type=TaskType.LEARNING,
        tags=["testing"],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
        due_date=date.today(),
    )
    review = NightlyReview(
        user_id=user_id,
        review_date=date.today(),
        summary_text="Completed the important tasks today.",
    )

    db_session.add_all([user, task, review])
    await db_session.commit()

    payload = EvidenceResolveRequest(
        items=[
            EvidenceRef(type="task", id=str(task.id)),
            EvidenceRef(type="summary", id=str(review.id)),
        ]
    )
    response = await events_api.resolve_evidence(payload, db=db_session, current_user=user)

    assert response.resolved[0].status == "ok"
    assert response.resolved[0].task["id"] == str(task.id)
    assert response.resolved[0].task["status"] == TaskStatus.PENDING.value

    assert response.resolved[1].status == "ok"
    assert response.resolved[1].summary["id"] == str(review.id)
    assert response.resolved[1].summary["summary_text"] == review.summary_text
