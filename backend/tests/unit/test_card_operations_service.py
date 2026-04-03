from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.card_protocol import CardType, EdgeType, OccurrenceStatus, TaskOccurrence
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.card_protocol.card_operations_service import CardOperationsService
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.card_service import CardService
from app.services.plan_state_service import PlanStateService
from app.services.task_occurrence_service import TaskOccurrenceService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "card-ops-test"


@pytest.mark.asyncio
async def test_move_task_card_between_plans_updates_edges_and_legacy_task(db_session, test_user):
    user_id = test_user.id
    plan_a = Plan(
        user_id=user_id,
        name="Plan A",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    plan_b = Plan(
        user_id=user_id,
        name="Plan B",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add_all([plan_a, plan_b])
    await db_session.commit()
    await db_session.refresh(plan_a)
    await db_session.refresh(plan_b)
    plan_a_id = plan_a.id
    plan_b_id = plan_b.id

    fake_bus = FakeEventBus()
    plan_a_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan_a)
    plan_b_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan_b)

    task = Task(
        user_id=user_id,
        plan_id=plan_a.id,
        title="Move me",
        type=TaskType.LEARNING,
        tags=["mobility"],
        estimated_minutes=20,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    phase_a_id = UUID(str(plan_a_card.metadata_["current_phase_card_id"]))

    occ_service = TaskOccurrenceService(db_session, fake_bus)
    await occ_service.create_occurrence(
        series_card_id=task_card.id,
        plan_card_id=plan_a_card.id,
        phase_card_id=phase_a_id,
        status=OccurrenceStatus.PLANNED,
    )

    service = CardOperationsService(db_session, fake_bus)
    result = await service.move_card(
        card_id=task_card.id,
        new_parent_card_id=plan_b_card.id,
        user_id=user_id,
    )
    await db_session.commit()
    await db_session.refresh(task)

    assert str(task.plan_id) == str(plan_b_id)
    assert result.old_plan_card_id == str(plan_a_card.id)
    assert result.new_plan_card_id == str(plan_b_card.id)
    assert result.moved_occurrence_count == 1

    parents = await service.edge_service.get_parents(task_card.id, edge_type=EdgeType.CONTAINS, active_only=True)
    assert len(parents) == 1
    assert parents[0][1].id == UUID(result.new_phase_card_id)

    db_session.expire_all()
    old_state = await PlanStateService(db_session, redis=None).get_plan_state(user_id, plan_a_id, refresh=True)
    new_state = await PlanStateService(db_session, redis=None).get_plan_state(user_id, plan_b_id, refresh=True)
    assert old_state is not None
    assert new_state is not None
    assert (old_state.task_index or {}).get("total") == 0
    assert (new_state.task_index or {}).get("total") == 1

    event_types = [event_type for event_type, _ in fake_bus.events]
    assert "card.moved" in event_types


@pytest.mark.asyncio
async def test_move_task_card_to_orphan_cancels_open_occurrences(db_session, test_user):
    user_id = test_user.id
    plan = Plan(
        user_id=user_id,
        name="Detach Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    fake_bus = FakeEventBus()
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)

    task = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Detach me",
        type=TaskType.LEARNING,
        estimated_minutes=15,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    phase_id = UUID(str(plan_card.metadata_["current_phase_card_id"]))
    occ = await TaskOccurrenceService(db_session, fake_bus).create_occurrence(
        series_card_id=task_card.id,
        plan_card_id=plan_card.id,
        phase_card_id=phase_id,
        status=OccurrenceStatus.PLANNED,
    )

    result = await CardOperationsService(db_session, fake_bus).move_card(
        card_id=task_card.id,
        new_parent_card_id=None,
        user_id=user_id,
    )
    await db_session.commit()
    await db_session.refresh(task)

    assert task.plan_id is None
    assert result.new_parent_card_id is None
    assert result.new_plan_card_id is None

    active_parents = await CardOperationsService(db_session, fake_bus).edge_service.get_parents(
        task_card.id,
        edge_type=EdgeType.CONTAINS,
        active_only=True,
    )
    assert active_parents == []

    refreshed_occ = await TaskOccurrenceService(db_session, fake_bus).get_occurrence(occ.id)
    assert refreshed_occ is not None
    assert refreshed_occ.occurrence_status == OccurrenceStatus.CANCELLED
    assert refreshed_occ.plan_card_id is None
    assert refreshed_occ.phase_card_id is None


@pytest.mark.asyncio
async def test_bulk_move_cards_between_plans_updates_all_legacy_tasks(db_session, test_user):
    user_id = test_user.id
    source_plan = Plan(
        user_id=user_id,
        name="Source Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    target_plan = Plan(
        user_id=user_id,
        name="Target Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add_all([source_plan, target_plan])
    await db_session.commit()
    await db_session.refresh(source_plan)
    await db_session.refresh(target_plan)

    fake_bus = FakeEventBus()
    target_plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(target_plan)
    await PlanAdapter(db_session, fake_bus).plan_to_card(source_plan)

    tasks = []
    task_cards = []
    for index in range(2):
        task = Task(
            user_id=user_id,
            plan_id=source_plan.id,
            title=f"Bulk {index}",
            type=TaskType.LEARNING,
            estimated_minutes=15,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.PENDING,
            priority=index,
            order_index=1000 + index,
        )
        db_session.add(task)
        await db_session.flush()
        task_cards.append(await TaskAdapter(db_session, fake_bus).task_to_card(task))
        tasks.append(task)

    await db_session.commit()

    results = await CardOperationsService(db_session, fake_bus).bulk_move_cards(
        card_ids=[card.id for card in task_cards],
        new_parent_card_id=target_plan_card.id,
        user_id=user_id,
    )
    await db_session.commit()

    assert len(results) == 2
    for task in tasks:
        await db_session.refresh(task)
        assert task.plan_id == target_plan.id

    moved_events = [event_type for event_type, _ in fake_bus.events if event_type == "card.moved"]
    assert len(moved_events) == 2


@pytest.mark.asyncio
async def test_search_cards_filters_by_type_and_text_query(db_session, test_user):
    service = CardService(db_session)
    await service.create_card(
        card_type=CardType.TASK,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"title": "Thermo review"},
        tags=["physics"],
    )
    await service.create_card(
        card_type=CardType.KNOWLEDGE,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Entropy"},
        tags=["physics", "knowledge"],
    )
    await db_session.commit()

    ops = CardOperationsService(db_session)
    results = await ops.search_cards(
        user_id=test_user.id,
        card_type=CardType.KNOWLEDGE,
        text_query="Entropy",
    )
    assert len(results) == 1
    assert results[0].card_type == CardType.KNOWLEDGE


@pytest.mark.asyncio
async def test_search_cards_supports_legacy_task_lookup(db_session, test_user):
    task = Task(
        user_id=test_user.id,
        title="Legacy lookup task",
        type=TaskType.LEARNING,
        tags=["lookup"],
        estimated_minutes=15,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    await TaskAdapter(db_session).task_to_card(task)
    await db_session.commit()

    ops = CardOperationsService(db_session)
    results = await ops.search_cards(
        user_id=test_user.id,
        card_type=CardType.TASK,
        legacy_task_id=task.id,
    )
    assert len(results) == 1
    assert results[0].metadata_["legacy_task_id"] == str(task.id)
