from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.card_protocol import (
    ArtifactType,
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionOutcomeStatus,
    InterventionTriggerType,
    OccurrenceStatus,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.services.card_protocol.decision_log_service import DecisionLogService
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService
from app.services.card_protocol.risk_register_service import RiskRegisterService
from app.services.intervention_record_service import InterventionRecordService
from app.services.main_chain_artifact_consumer import MainChainArtifactConsumer
from app.services.plan_state_service import PlanStateService
from app.services.planning_artifact_service import PlanningArtifactService
from app.services.task_occurrence_service import TaskOccurrenceService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "phase4-test-event"

    async def connect(self) -> None:
        return None


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_active_phase_pack_materializes_current_execution_slice(db_session, test_user):
    plan = Plan(
        user_id=test_user.id,
        name="Thermodynamics Sprint",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.HIGH,
        is_active=True,
        progress=0.25,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_card = await PlanAdapter(db_session, FakeEventBus()).plan_to_card(plan)

    task_one = Task(
        user_id=test_user.id,
        plan_id=plan.id,
        title="Differentiate reversible vs irreversible",
        type=TaskType.LEARNING,
        tags=["thermo"],
        estimated_minutes=25,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
        order_index=10,
    )
    task_two = Task(
        user_id=test_user.id,
        plan_id=plan.id,
        title="Solve entropy practice set",
        type=TaskType.TRAINING,
        tags=["thermo"],
        estimated_minutes=40,
        difficulty=4,
        energy_cost=3,
        status=TaskStatus.PENDING,
        priority=2,
        order_index=20,
        due_date=date.today() + timedelta(days=2),
    )
    db_session.add_all([task_one, task_two])
    await db_session.commit()
    await db_session.refresh(task_one)
    await db_session.refresh(task_two)

    task_card_one = await TaskAdapter(db_session, FakeEventBus()).task_to_card(task_one)
    task_card_two = await TaskAdapter(db_session, FakeEventBus()).task_to_card(task_two)
    phase_card_id = UUID(str(plan_card.metadata_["current_phase_card_id"]))

    occurrence_service = TaskOccurrenceService(db_session)
    await occurrence_service.create_occurrence(
        series_card_id=task_card_one.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase_card_id,
        scheduled_for=date.today(),
        status=OccurrenceStatus.READY,
    )
    await occurrence_service.create_occurrence(
        series_card_id=task_card_two.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase_card_id,
        scheduled_for=date.today() + timedelta(days=1),
        status=OccurrenceStatus.PLANNED,
    )

    service = MainChainArtifactService(db_session)
    artifact = await service.refresh_active_phase_pack(
        plan_card_id=plan_card.id,
        generated_reason="phase4_test",
    )
    await db_session.commit()

    assert artifact is not None
    assert artifact.artifact_type == ArtifactType.ACTIVE_PHASE_PACK
    assert artifact.payload["plan"]["name"] == "Thermodynamics Sprint"
    assert artifact.payload["phase"]["task_count"] == 2
    assert [task["title"] for task in artifact.payload["tasks"]] == [
        "Differentiate reversible vs irreversible",
        "Solve entropy practice set",
    ]
    assert artifact.payload["metrics"]["occurrence_status_counts"]["READY"] == 1
    assert artifact.payload["metrics"]["occurrence_status_counts"]["PLANNED"] == 1

    artifact_service = PlanningArtifactService(db_session)
    unchanged = await service.refresh_active_phase_pack(
        plan_card_id=plan_card.id,
        generated_reason="phase4_test_repeat",
    )
    current = await artifact_service.get_approved(plan_card.id, ArtifactType.ACTIVE_PHASE_PACK)
    assert unchanged is not None
    assert current is not None
    assert current.version == artifact.version


@pytest.mark.asyncio
async def test_reflection_report_summarizes_learning_and_risk_state(db_session, test_user):
    plan = Plan(
        user_id=test_user.id,
        name="Main Loop Reflection Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_card = await PlanAdapter(db_session, FakeEventBus()).plan_to_card(plan)

    task = Task(
        user_id=test_user.id,
        plan_id=plan.id,
        title="Repair concept gap",
        type=TaskType.LEARNING,
        tags=["gap"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
        priority=1,
        order_index=10,
        actual_minutes=35,
        completed_at=datetime.utcnow(),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    await TaskAdapter(db_session, FakeEventBus()).task_to_card(task)

    feedback = TaskFeedback(
        user_id=test_user.id,
        task_id=task.id,
        category="too_difficult",
        feedback_text="可逆和不可逆还是会混。",
        reflection_payload={
            "selected_option": "概念没理解",
            "free_text": "可逆和不可逆总是容易混",
            "submitted_at": datetime.utcnow().isoformat(),
        },
    )
    db_session.add(feedback)

    plan_state_service = PlanStateService(db_session, redis=None)
    await plan_state_service.upsert_plan_state(
        user_id=test_user.id,
        plan_id=plan.id,
        patch={
            "feedback_log": [
                {
                    "id": "fb-pos",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "task_feedback",
                    "content": "补完概念之后节奏更顺了。",
                },
                {
                    "id": "fb-neg",
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "type": "task_feedback",
                    "content": "昨天还是有点卡住。",
                },
            ]
        },
        bump_version=True,
    )

    record_service = InterventionRecordService(db_session)
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.CONCEPT_GAP,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
    )
    await record_service.mark_delivered(record.id)
    await record_service.mark_accepted(record.id)
    await record_service.mark_acted(record.id, action_payload={"cta": "review_concept"})
    await record_service.resolve_outcome(
        record.id,
        InterventionOutcomeStatus.EFFECTIVE,
        evidence_payload={"resolution_method": "phase4_test"},
    )

    decision_log = DecisionLogService(db_session)
    entry = await decision_log.record_decision(
        plan_card_id=plan_card.id,
        decision="Reduce concurrency around thermo review",
        rationale="Detected concept confusion and overload",
        trigger="concept_gap",
        linked_intervention_id=str(record.id),
    )
    assert entry is not None
    await decision_log.confirm_entry(plan_card.id, entry["id"], evidence={"outcome": "effective"})

    risk_register = RiskRegisterService(db_session)
    await risk_register.register_risk(
        plan_card_id=plan_card.id,
        description="User may stall on thermodynamics concept confusion",
        likelihood="high",
        impact_level="high",
        mitigation_strategy="Insert prerequisite review",
        source_pattern="cognitive",
    )

    service = MainChainArtifactService(db_session)
    await service.refresh_active_phase_pack(
        plan_card_id=plan_card.id,
        generated_reason="phase4_reflection_setup",
    )
    artifact = await service.refresh_reflection_report(
        plan_card_id=plan_card.id,
        generated_reason="phase4_test",
        linked_intervention_id=str(record.id),
        linked_feedback_id=str(feedback.id),
    )
    await db_session.commit()

    assert artifact is not None
    assert artifact.artifact_type == ArtifactType.REFLECTION_REPORT
    assert artifact.payload["summary"]["intervention_count"] >= 1
    assert artifact.payload["summary"]["effective_intervention_count"] >= 1
    assert artifact.payload["decision_summary"].get("CONFIRMED", 0) >= 1
    assert artifact.payload["reflection_signals"][0]["selected_option"] == "概念没理解"
    assert artifact.payload["active_risks_snapshot"][0]["description"].startswith("User may stall")
    assert artifact.payload["what_worked"]


@pytest.mark.asyncio
async def test_main_chain_consumer_refreshes_artifacts_for_intervention_status(db_session, test_user):
    plan = Plan(
        user_id=test_user.id,
        name="Consumer Sync Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_card = await PlanAdapter(db_session, FakeEventBus()).plan_to_card(plan)
    await db_session.commit()

    record_service = InterventionRecordService(db_session)
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
    )
    await record_service.mark_delivered(record.id)
    await db_session.commit()

    consumer = MainChainArtifactConsumer(event_bus=FakeEventBus())
    consumer.session_factory = lambda: _AsyncSessionContext(db_session)
    await consumer._handle_event(
        {
            "event_type": "intervention_record.status_changed",
            "record_id": str(record.id),
        }
    )

    artifact_service = PlanningArtifactService(db_session)
    active_pack = await artifact_service.get_approved(plan_card.id, ArtifactType.ACTIVE_PHASE_PACK)
    reflection_report = await artifact_service.get_approved(plan_card.id, ArtifactType.REFLECTION_REPORT)

    assert active_pack is not None
    assert reflection_report is not None
