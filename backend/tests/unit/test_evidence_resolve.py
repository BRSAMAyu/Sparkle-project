from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.api.v1 import events as events_api
from app.models.chat import ChatMessage, MessageRole
from app.models.error_book import ErrorRecord
from app.models.memory import EpisodicMemory
from app.models.nightly_review import NightlyReview
from app.models.task import Task, TaskType, TaskStatus
from app.models.user import User
from app.schemas.error_book import ReviewAction, ReviewPerformanceEnum
from app.schemas.events import EvidenceResolveRequest
from app.schemas.intervention import EvidenceRef
from app.services.error_book_service import ErrorBookService


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


@pytest.mark.asyncio
async def test_evidence_resolve_practice_outcome_returns_memory_backed_review_payload(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    error = ErrorRecord(
        user_id=user_id,
        subject_code="math",
        question_text="1+1=?",
        user_answer="3",
        correct_answer="2",
        mastery_level=0.0,
        easiness_factor=2.5,
        review_count=0,
        interval_days=0.0,
    )
    db_session.add_all([user, error])
    await db_session.commit()
    await db_session.refresh(error)

    with (
        patch("app.services.error_book_signal_processor.ErrorBookSignalProcessor") as mock_processor,
        patch("app.services.error_book_mastery_sync_service.ErrorBookMasterySyncService") as mock_mastery,
        patch("app.services.memory_service.SystemUpdateService.enqueue", new=AsyncMock(return_value=True)),
    ):
        mock_processor.return_value.process_error_created = AsyncMock()
        mock_mastery.return_value.apply_review_feedback = AsyncMock(return_value=[])

        service = ErrorBookService(db_session)
        await service.submit_review(
            user_id,
            error.id,
            ReviewAction(performance=ReviewPerformanceEnum.REMEMBERED),
        )

    episodic = (
        await db_session.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.source_type == "practice_outcome",
                EpisodicMemory.source_id == str(error.id),
            )
        )
    ).scalar_one()

    assert episodic.summary.startswith("错题复习结果：remembered")
    assert "performance:remembered" in (episodic.tags or [])

    payload = EvidenceResolveRequest(
        items=[EvidenceRef(type="practice_outcome", id=str(error.id))]
    )
    response = await events_api.resolve_evidence(payload, db=db_session, current_user=user)

    assert response.resolved[0].status == "ok"
    assert response.resolved[0].practice_outcome["error_id"] == str(error.id)
    assert response.resolved[0].practice_outcome["review_performance"] == "remembered"


@pytest.mark.asyncio
async def test_evidence_resolve_chat_turn_returns_session_payload(db_session):
    user_id = uuid4()
    session_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    turn = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=MessageRole.USER,
        content="最近我在整理线代错题。",
    )
    db_session.add_all([user, turn])
    await db_session.commit()
    await db_session.refresh(turn)

    payload = EvidenceResolveRequest(
        items=[EvidenceRef(type="chat_turn", id=str(turn.id))]
    )
    response = await events_api.resolve_evidence(payload, db=db_session, current_user=user)

    assert response.resolved[0].status == "ok"
    assert response.resolved[0].chat_turn["id"] == str(turn.id)
    assert response.resolved[0].chat_turn["session_id"] == str(session_id)
