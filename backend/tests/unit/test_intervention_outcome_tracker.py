from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base, _utcnow
from app.models.intervention_outcome import InterventionOutcome
from app.services.intervention_outcome_tracker import InterventionOutcomeTracker


class FakeGalaxyService:
    def __init__(self, mastery: float | None):
        self.mastery = mastery

    async def get_node_mastery(self, db, *, user_id, node_id):
        del db, user_id, node_id
        return self.mastery


@pytest.fixture
def tracker() -> InterventionOutcomeTracker:
    return InterventionOutcomeTracker()


@pytest.mark.asyncio
async def test_record_intervention_writes_db_and_publishes_event(db_session, tracker, monkeypatch):
    publish = AsyncMock(return_value="event-id")
    monkeypatch.setattr("app.services.intervention_outcome_tracker.event_bus.publish", publish)

    user_id = uuid4()
    target_node_id = uuid4()
    intervention_id = await tracker.record_intervention(
        db_session,
        user_id=str(user_id),
        intervention_type="replan",
        trigger_reason="low_mastery",
        target_concept="fractions",
        target_node_id=str(target_node_id),
        mastery_before=42,
    )

    outcome = await db_session.get(InterventionOutcome, intervention_id)
    assert outcome is not None
    assert outcome.user_id == user_id
    assert outcome.target_node_id == target_node_id
    assert outcome.outcome_status == "pending"
    assert outcome.follow_up_at - outcome.triggered_at == timedelta(hours=72)

    publish.assert_awaited_once()
    event_type, payload = publish.await_args.args[:2]
    assert event_type == "intervention_recorded"
    assert payload["intervention_id"] == intervention_id
    assert payload["intervention_type"] == "replan"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mastery_before", "mastery_after", "expected_status", "expected_effective"),
    [
        (40, 50.1, "improved", True),
        (40, 45, "no_change", False),
        (40, 34.9, "degraded", False),
    ],
)
async def test_check_outcome_classifies_mastery_delta(
    db_session,
    tracker,
    monkeypatch,
    mastery_before,
    mastery_after,
    expected_status,
    expected_effective,
):
    publish = AsyncMock(return_value="event-id")
    monkeypatch.setattr("app.services.intervention_outcome_tracker.event_bus.publish", publish)
    outcome = InterventionOutcome(
        user_id=uuid4(),
        intervention_type="replan",
        trigger_reason="stuck",
        target_concept="limits",
        target_node_id=uuid4(),
        triggered_at=_utcnow(),
        follow_up_at=_utcnow(),
        outcome_status="pending",
        mastery_before=mastery_before,
    )
    db_session.add(outcome)
    await db_session.commit()

    result = await tracker.check_outcome(
        db_session,
        intervention_id=str(outcome.id),
        galaxy_service=FakeGalaxyService(mastery_after),
    )

    assert result == {
        "intervention_id": str(outcome.id),
        "effective": expected_effective,
        "status": expected_status,
    }
    await db_session.refresh(outcome)
    assert outcome.outcome_status == expected_status
    assert outcome.effective is expected_effective
    assert outcome.mastery_after == mastery_after
    assert outcome.outcome_checked_at is not None

    assert publish.await_args.args[0] == "intervention_outcome_recorded"
    assert publish.await_args.args[1]["status"] == expected_status


@pytest.mark.asyncio
async def test_check_outcome_without_target_node_marks_not_checked(db_session, tracker, monkeypatch):
    publish = AsyncMock(return_value="event-id")
    monkeypatch.setattr("app.services.intervention_outcome_tracker.event_bus.publish", publish)
    outcome = InterventionOutcome(
        user_id=uuid4(),
        intervention_type="push_nudge",
        trigger_reason="missed_task",
        target_concept="derivatives",
        target_node_id=None,
        triggered_at=_utcnow(),
        follow_up_at=_utcnow(),
        outcome_status="pending",
        mastery_before=55,
    )
    db_session.add(outcome)
    await db_session.commit()

    result = await tracker.check_outcome(
        db_session,
        intervention_id=str(outcome.id),
        galaxy_service=FakeGalaxyService(90),
    )

    assert result == {
        "intervention_id": str(outcome.id),
        "effective": None,
        "status": "not_checked",
    }
    await db_session.refresh(outcome)
    assert outcome.outcome_status == "not_checked"
    assert outcome.mastery_after is None
    assert outcome.effective is None


@pytest.mark.asyncio
async def test_get_effectiveness_summary_calculates_rates(db_session, tracker):
    user_id = uuid4()
    other_user_id = uuid4()
    now = _utcnow()
    db_session.add_all(
        [
            InterventionOutcome(
                user_id=user_id,
                intervention_type="replan",
                trigger_reason="risk",
                triggered_at=now,
                outcome_status="improved",
                effective=True,
            ),
            InterventionOutcome(
                user_id=user_id,
                intervention_type="replan",
                trigger_reason="risk",
                triggered_at=now,
                outcome_status="no_change",
                effective=False,
            ),
            InterventionOutcome(
                user_id=user_id,
                intervention_type="push_nudge",
                trigger_reason="missed_task",
                triggered_at=now,
                outcome_status="improved",
                effective=True,
            ),
            InterventionOutcome(
                user_id=user_id,
                intervention_type="push_nudge",
                trigger_reason="missed_task",
                triggered_at=now,
                outcome_status="pending",
                effective=None,
            ),
            InterventionOutcome(
                user_id=user_id,
                intervention_type="replan",
                trigger_reason="old",
                triggered_at=now - timedelta(days=31),
                outcome_status="improved",
                effective=True,
            ),
            InterventionOutcome(
                user_id=other_user_id,
                intervention_type="replan",
                trigger_reason="other",
                triggered_at=now,
                outcome_status="improved",
                effective=True,
            ),
        ]
    )
    await db_session.commit()

    summary = await tracker.get_effectiveness_summary(db_session, user_id=str(user_id), days=30)

    assert summary["total_interventions"] == 4
    assert summary["checked"] == 3
    assert summary["effective_rate"] == pytest.approx(2 / 3)
    assert summary["by_type"] == {
        "replan": 0.5,
        "push_nudge": 1.0,
    }


@pytest.mark.asyncio
async def test_check_pending_outcomes_checks_due_records_only(db_session, tracker, monkeypatch):
    publish = AsyncMock(return_value="event-id")
    monkeypatch.setattr("app.services.intervention_outcome_tracker.event_bus.publish", publish)
    user_id = uuid4()
    due = InterventionOutcome(
        user_id=user_id,
        intervention_type="replan",
        trigger_reason="risk",
        target_node_id=uuid4(),
        triggered_at=_utcnow() - timedelta(hours=73),
        follow_up_at=_utcnow() - timedelta(minutes=1),
        outcome_status="pending",
        mastery_before=10,
    )
    future = InterventionOutcome(
        user_id=user_id,
        intervention_type="replan",
        trigger_reason="risk",
        target_node_id=uuid4(),
        triggered_at=_utcnow(),
        follow_up_at=_utcnow() + timedelta(hours=1),
        outcome_status="pending",
        mastery_before=10,
    )
    db_session.add_all([due, future])
    await db_session.commit()

    results = await tracker.check_pending_outcomes(
        db_session,
        user_id=str(user_id),
        galaxy_service=FakeGalaxyService(30),
    )

    assert results == [{"intervention_id": str(due.id), "effective": True, "status": "improved"}]
    await db_session.refresh(future)
    assert future.outcome_status == "pending"


@pytest_asyncio.fixture
async def file_session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'outcomes.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_check_outcome_is_idempotent_under_concurrent_checks(file_session_factory, monkeypatch):
    publish = AsyncMock(return_value="event-id")
    monkeypatch.setattr("app.services.intervention_outcome_tracker.event_bus.publish", publish)
    tracker = InterventionOutcomeTracker()
    intervention_id = uuid4()
    user_id = uuid4()
    node_id = uuid4()

    async with file_session_factory() as session:
        session.add(
            InterventionOutcome(
                id=intervention_id,
                user_id=user_id,
                intervention_type="replan",
                trigger_reason="risk",
                target_node_id=node_id,
                triggered_at=_utcnow(),
                follow_up_at=_utcnow(),
                outcome_status="pending",
                mastery_before=10,
            )
        )
        await session.commit()

    async def run_check():
        async with file_session_factory() as session:
            return await tracker.check_outcome(
                session,
                intervention_id=str(intervention_id),
                galaxy_service=FakeGalaxyService(25),
            )

    results = await asyncio.gather(run_check(), run_check())
    successful = [result for result in results if result is not None]

    assert successful == [{"intervention_id": str(intervention_id), "effective": True, "status": "improved"}]
    assert publish.await_count == 1
    async with file_session_factory() as session:
        stored = (await session.execute(select(InterventionOutcome))).scalar_one()
        assert stored.outcome_status == "improved"
        assert stored.effective is True
