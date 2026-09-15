from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionRecord,
    InterventionTriggerType,
    OccurrenceStatus,
    TaskOccurrence,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.card_protocol.feedback_gate_engine import FeedbackGateEngine
from app.services.card_protocol.phase_design_service import PhaseDesignService
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.planning_memory_service import PlanningMemoryService
from app.services.card_protocol.temporal_engine import RecurrenceRule, TemporalEngine
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.intervention_record_service import InterventionRecordService
from app.services.task_occurrence_service import TaskOccurrenceService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "phase-e-test"


async def _make_plan(db_session, user_id, name: str = "Phase E Plan") -> Plan:
    plan = Plan(
        user_id=user_id,
        name=name,
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
        description="Long-horizon growth plan",
        subject="AI",
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


async def _make_task(db_session, *, user_id, plan_id, title: str) -> Task:
    task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title=title,
        type=TaskType.LEARNING,
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
        tags=["phase-e"],
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_phase_design_creates_tasks_and_occurrences(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, "Design Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase_service = PhaseService(db_session, fake_bus)
    phase = await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Execution",
        phase_index=1,
        user_id=test_user.id,
        estimated_start=date.today(),
        estimated_end=date.today() + timedelta(days=14),
    )
    await phase_service.activate_phase(phase_card_id=phase.id, user_id=test_user.id)

    created = await PhaseDesignService(db_session, fake_bus).design_phase_tasks(
        phase_card_id=phase.id,
        plan_card_id=plan_card.id,
        user_id=test_user.id,
    )
    await db_session.commit()

    assert len(created) == 3
    result = await db_session.execute(
        select(TaskOccurrence).where(TaskOccurrence.phase_card_id == phase.id)
    )
    occurrences = list(result.scalars().all())
    assert len(occurrences) >= 3


@pytest.mark.asyncio
async def test_feedback_gate_completes_phase_and_designs_next_phase(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, "Feedback Gate Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase_service = PhaseService(db_session, fake_bus)
    phase_one = await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase One",
        phase_index=1,
        user_id=test_user.id,
        estimated_start=date.today(),
        estimated_end=date.today() + timedelta(days=7),
    )
    await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase Two",
        phase_index=2,
        user_id=test_user.id,
        estimated_start=date.today() + timedelta(days=8),
        estimated_end=date.today() + timedelta(days=20),
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Current phase task")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    await TemporalEngine(db_session, fake_bus).set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="weekly", days_of_week=[1, 3]),
        user_id=test_user.id,
    )
    await phase_service.activate_phase(phase_card_id=phase_one.id, user_id=test_user.id)

    engine = FeedbackGateEngine(db_session, fake_bus)
    session = await engine.trigger_feedback_gate(
        phase_card_id=phase_one.id,
        user_id=test_user.id,
    )
    responses = [
        "这个阶段最大的阻力是工作太忙，但我还是有一些进步。",
        "多次延期主要是时间不够。",
        "下一阶段我最想保留稳定的核心学习节奏。",
    ]
    result = None
    for response in responses:
        result = await engine.process_feedback_response(
            session_id=session["session_id"],
            user_message=response,
        )
    assert result is not None
    assert result["completed"] is True

    advanced = await engine.advance_to_next_phase(
        plan_card_id=plan_card.id,
        user_id=test_user.id,
    )
    assert advanced["workflow_state"] == "PHASE_DESIGN"
    assert advanced["designed_task_count"] == 3


@pytest.mark.asyncio
async def test_planning_memory_detects_drift_and_outcome_verifier_raises_misalignment(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, "Drift Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase_service = PhaseService(db_session, fake_bus)
    phase = await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Drift Phase",
        phase_index=1,
        user_id=test_user.id,
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Drifting task")
    task.status = TaskStatus.ABANDONED
    await db_session.commit()
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    occ_service = TaskOccurrenceService(db_session, fake_bus)
    occurrence = await occ_service.create_occurrence(
        series_card_id=task_card.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase.id,
        scheduled_for=date.today(),
        status=OccurrenceStatus.PLANNED,
    )
    await occ_service.defer(occurrence.id, new_date=date.today() + timedelta(days=1))
    await occ_service.defer(occurrence.id, new_date=date.today() + timedelta(days=2))
    await db_session.commit()

    drift = await PlanningMemoryService(db_session, fake_bus).compute_drift_score(
        plan_card_id=plan_card.id,
    )
    assert drift.drift_score > 0.4

    record = await InterventionRecordService(db_session, fake_bus).create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.IN_APP,
        plan_card_id=plan_card.id,
        phase_card_id=phase.id,
        diagnosis_payload={"reason": "test"},
        outcome_window_days=0,
    )
    await db_session.commit()

    await InterventionOutcomeVerifier(db_session, fake_bus)._phase_e_drift_check(record)
    await db_session.commit()
    result = await db_session.execute(
        select(InterventionRecord).where(
            InterventionRecord.plan_card_id == plan_card.id,
            InterventionRecord.trigger_type == InterventionTriggerType.MISALIGNMENT,
        )
    )
    misalignment = result.scalars().first()
    assert misalignment is not None
