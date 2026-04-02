from __future__ import annotations

import pytest

from app.models.card_protocol import CardLifecycleStatus, CardType, EdgeType
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.card_protocol.mastery_bridge import ErrorMasteryBridge
from app.services.card_service import CardService
from app.services.task_occurrence_service import OccurrenceStatus, TaskOccurrenceService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "test-id"


@pytest.mark.asyncio
async def test_legacy_projection_builds_plan_phase_task_graph(db_session, test_user):
    plan = Plan(
        user_id=test_user.id,
        name="Long Horizon Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_card = await PlanAdapter(db_session).plan_to_card(plan)
    await db_session.commit()

    task = Task(
        user_id=test_user.id,
        plan_id=plan.id,
        title="Daily deliberate practice",
        type=TaskType.LEARNING,
        tags=["practice"],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    task_card = await TaskAdapter(db_session).task_to_card(task)
    await db_session.commit()

    phase_cards = (
        await CardService(db_session).get_plan_with_phases(plan_card.id)
    )["phases"]
    assert len(phase_cards) == 1
    synthetic_phase = phase_cards[0]
    assert synthetic_phase.card_type == CardType.PHASE
    assert synthetic_phase.metadata_["synthetic_phase"] is True

    task_edges = await TaskAdapter(db_session).edge_service.get_children(
        synthetic_phase.id,
        edge_type=EdgeType.CONTAINS,
    )
    assert [child.id for _, child in task_edges] == [task_card.id]

    incoming_to_task = await TaskAdapter(db_session).edge_service.get_parents(
        task_card.id,
        edge_type=EdgeType.CONTAINS,
    )
    assert len(incoming_to_task) == 1
    assert incoming_to_task[0][1].id == synthetic_phase.id


@pytest.mark.asyncio
async def test_error_mastery_bridge_uses_metadata_fallback_without_self_edges(db_session, test_user):
    bridge = ErrorMasteryBridge(db_session)
    node_id = test_user.id

    first = await bridge.on_error_created(
        user_id=test_user.id,
        error_id=test_user.id,
        linked_node_ids=[node_id],
        analysis={"why": "missed prerequisite"},
        error_type="concept_gap",
    )
    second = await bridge.on_error_created(
        user_id=test_user.id,
        error_id=test_user.id,
        linked_node_ids=[node_id],
        analysis={"why": "missed prerequisite"},
        error_type="concept_gap",
    )
    await db_session.commit()

    cards = await CardService(db_session).get_cards_by_owner(test_user.id, card_type=CardType.KNOWLEDGE)
    assert len(cards) == 1
    knowledge = cards[0]
    assert knowledge.metadata_["error_count"] == 2
    assert len(knowledge.metadata_["error_evidence_log"]) == 2
    assert first["evidence_edges"] == 0
    assert second["evidence_edges"] == 0


@pytest.mark.asyncio
async def test_occurrence_events_use_consistent_status_change_contract(db_session, test_user):
    fake_bus = FakeEventBus()
    card = await CardService(db_session, fake_bus).create_card(
        card_type=CardType.TASK,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"title": "Timed practice"},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )
    service = TaskOccurrenceService(db_session, fake_bus)
    occurrence = await service.create_occurrence(
        series_card_id=card.id,
        status=OccurrenceStatus.PLANNED,
    )
    await service.defer(occurrence.id)
    await service.complete(occurrence.id, actual_minutes=20, completion_quality=4)

    event_types = [event_type for event_type, _ in fake_bus.events]
    assert "occurrence.created" not in event_types
    assert "occurrence.deferred" not in event_types
    assert event_types.count("occurrence.status_changed") == 2
    assert "occurrence.completed" in event_types

    status_payloads = [payload for event_type, payload in fake_bus.events if event_type == "occurrence.status_changed"]
    assert status_payloads[0]["old_status"] == OccurrenceStatus.PLANNED.value
    assert status_payloads[0]["new_status"] == OccurrenceStatus.DEFERRED.value
    assert status_payloads[1]["old_status"] == OccurrenceStatus.DEFERRED.value
    assert status_payloads[1]["new_status"] == OccurrenceStatus.COMPLETED.value
