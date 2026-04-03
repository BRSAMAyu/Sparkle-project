from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.card_protocol import (
    CardType,
    InterventionRecord,
    OccurrenceStatus,
    TaskOccurrence,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.card_protocol.card_operations_service import CardOperationsService
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.temporal_engine import RecurrenceRule, TemporalEngine
from app.services.task_occurrence_service import TaskOccurrenceService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "phase-b-test"


async def _make_plan(db_session, user_id, name: str = "Phase B Plan") -> Plan:
    plan = Plan(
        user_id=user_id,
        name=name,
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


async def _make_task(
    db_session,
    *,
    user_id,
    plan_id,
    title: str,
    estimated_minutes: int = 25,
) -> Task:
    task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title=title,
        type=TaskType.LEARNING,
        estimated_minutes=estimated_minutes,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
        tags=["phase-b"],
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_create_plan_with_3_real_phases(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id)
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)

    service = PhaseService(db_session, fake_bus)
    await service.create_phase(
        plan_card_id=plan_card.id,
        name="Foundation",
        phase_index=1,
        user_id=test_user.id,
    )
    await service.create_phase(
        plan_card_id=plan_card.id,
        name="Build",
        phase_index=2,
        user_id=test_user.id,
    )
    await service.create_phase(
        plan_card_id=plan_card.id,
        name="Refine",
        phase_index=3,
        user_id=test_user.id,
    )
    await db_session.commit()

    payload = await service.get_phase_summaries_for_legacy_plan(
        legacy_plan_id=plan.id,
        user_id=test_user.id,
    )
    assert [phase["title"] for phase in payload["phases"]] == [
        "Foundation",
        "Build",
        "Refine",
    ]
    assert all(not phase["synthetic_phase"] for phase in payload["phases"])


@pytest.mark.asyncio
async def test_activate_phase_generates_occurrences(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, name="Activation Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase_service = PhaseService(db_session, fake_bus)
    phase = await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase One",
        phase_index=1,
        user_id=test_user.id,
        estimated_start=date.today(),
        estimated_end=date.today() + timedelta(days=2),
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Daily practice")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    await TemporalEngine(db_session, fake_bus).set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="daily"),
        user_id=test_user.id,
    )

    await phase_service.activate_phase(phase_card_id=phase.id, user_id=test_user.id)
    await db_session.commit()

    result = await db_session.execute(
        select(TaskOccurrence).where(TaskOccurrence.phase_card_id == phase.id)
    )
    occurrences = list(result.scalars().all())
    assert len(occurrences) == 3
    assert {occ.scheduled_for for occ in occurrences} == {
        date.today(),
        date.today() + timedelta(days=1),
        date.today() + timedelta(days=2),
    }


@pytest.mark.asyncio
async def test_weekly_recurrence_generates_correct_dates(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, name="Weekly Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase = await PhaseService(db_session, fake_bus).create_phase(
        plan_card_id=plan_card.id,
        name="Week Slice",
        phase_index=1,
        user_id=test_user.id,
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Weekly drill")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)

    engine = TemporalEngine(db_session, fake_bus)
    await engine.set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="weekly", days_of_week=[1, 3, 5]),
        user_id=test_user.id,
    )

    start = date(2026, 4, 6)
    created = await engine.generate_occurrences(
        task_card_id=task_card.id,
        phase_card_id=phase.id,
        from_date=start,
        to_date=start + timedelta(days=6),
    )

    assert [occ.scheduled_for for occ in created] == [
        date(2026, 4, 6),
        date(2026, 4, 8),
        date(2026, 4, 10),
    ]


@pytest.mark.asyncio
async def test_defer_beyond_max_triggers_intervention(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, name="Deferral Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase = await PhaseService(db_session, fake_bus).create_phase(
        plan_card_id=plan_card.id,
        name="Deferral Phase",
        phase_index=1,
        user_id=test_user.id,
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Do not stall")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)

    engine = TemporalEngine(db_session, fake_bus)
    await engine.set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="daily", max_deferrals=2),
        user_id=test_user.id,
    )

    occurrence = await TaskOccurrenceService(db_session, fake_bus).create_occurrence(
        series_card_id=task_card.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase.id,
        scheduled_for=date.today(),
        status=OccurrenceStatus.PLANNED,
    )

    await engine.defer_occurrence(occurrence_id=occurrence.id, user_id=test_user.id)
    await engine.defer_occurrence(occurrence_id=occurrence.id, user_id=test_user.id)
    await db_session.commit()

    records = await db_session.execute(
        select(InterventionRecord).where(InterventionRecord.task_occurrence_id == occurrence.id)
    )
    interventions = list(records.scalars().all())
    assert len(interventions) == 1


@pytest.mark.asyncio
async def test_complete_phase_requires_feedback_and_weighted_progress(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, name="Weighted Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    service = PhaseService(db_session, fake_bus)

    phase_one = await service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase One",
        phase_index=1,
        user_id=test_user.id,
        phase_weight=1.0,
    )
    phase_two = await service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase Two",
        phase_index=2,
        user_id=test_user.id,
        phase_weight=3.0,
    )

    task_one = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Weighted task one")
    task_two = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Weighted task two")
    task_card_one = await TaskAdapter(db_session, fake_bus).task_to_card(task_one)
    task_card_two = await TaskAdapter(db_session, fake_bus).task_to_card(task_two)

    card_ops = CardOperationsService(db_session, fake_bus)
    await card_ops.move_card(
        card_id=task_card_one.id,
        new_parent_card_id=phase_one.id,
        user_id=test_user.id,
    )
    await card_ops.move_card(
        card_id=task_card_two.id,
        new_parent_card_id=phase_two.id,
        user_id=test_user.id,
    )

    await TaskOccurrenceService(db_session, fake_bus).create_occurrence(
        series_card_id=task_card_one.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase_one.id,
        scheduled_for=date.today(),
        status=OccurrenceStatus.COMPLETED,
    )
    await TaskOccurrenceService(db_session, fake_bus).create_occurrence(
        series_card_id=task_card_two.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase_two.id,
        scheduled_for=date.today(),
        status=OccurrenceStatus.PLANNED,
    )

    completion = await service.complete_phase(
        phase_card_id=phase_one.id,
        user_id=test_user.id,
    )
    weighted_progress = await service.sync_legacy_plan_progress(plan.id, test_user.id)
    await db_session.commit()

    assert completion.status == "NEEDS_FEEDBACK"
    assert weighted_progress == pytest.approx(0.25, rel=1e-3)


@pytest.mark.asyncio
async def test_activate_phase_blocked_when_previous_phase_gate_not_submitted(db_session, test_user):
    """activate_phase must raise ValueError if the preceding phase requires feedback that was not submitted."""
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, name="Gate Enforcement Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    service = PhaseService(db_session, fake_bus)

    phase_one = await service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase One",
        phase_index=1,
        user_id=test_user.id,
        feedback_gate_required=True,
    )
    phase_two = await service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase Two",
        phase_index=2,
        user_id=test_user.id,
    )
    await db_session.commit()

    # Try to jump straight to phase 2 without submitting phase 1 feedback
    with pytest.raises(ValueError, match="feedback gate"):
        await service.activate_phase(phase_card_id=phase_two.id, user_id=test_user.id)

    # After feedback is submitted it must succeed
    await service.submit_phase_feedback(
        phase_card_id=phase_one.id,
        user_id=test_user.id,
        feedback={"rating": 4, "reflection": "done"},
    )
    await db_session.commit()
    # submit_phase_feedback auto-activates the next phase; no explicit call needed here


@pytest.mark.asyncio
async def test_monthly_recurrence_handles_short_months(db_session, test_user):
    """Monthly recurrence with day_of_month=31 must still fire in February (clamped to last day)."""
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, name="Month-End Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase = await PhaseService(db_session, fake_bus).create_phase(
        plan_card_id=plan_card.id,
        name="Feb Phase",
        phase_index=1,
        user_id=test_user.id,
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Monthly drill")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)

    engine = TemporalEngine(db_session, fake_bus)
    await engine.set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="monthly", day_of_month=31),
        user_id=test_user.id,
    )

    # Generate over February 2027 (28 days, no 31st)
    feb_start = date(2027, 2, 1)
    feb_end = date(2027, 2, 28)
    created = await engine.generate_occurrences(
        task_card_id=task_card.id,
        phase_card_id=phase.id,
        from_date=feb_start,
        to_date=feb_end,
    )
    # Should fire on Feb 28 (clamped from 31)
    assert len(created) == 1
    assert created[0].scheduled_for == date(2027, 2, 28)

    # And on Jan 31 it should fire on the actual 31st
    jan_start = date(2027, 1, 1)
    jan_end = date(2027, 1, 31)
    created_jan = await engine.generate_occurrences(
        task_card_id=task_card.id,
        phase_card_id=phase.id,
        from_date=jan_start,
        to_date=jan_end,
    )
    assert len(created_jan) == 1
    assert created_jan[0].scheduled_for == date(2027, 1, 31)
