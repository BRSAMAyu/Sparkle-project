from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.card_protocol import (
    Card,
    CardSourceType,
    CardType,
    EdgeType,
    ImportMode,
    SharePermission,
    ShareScope,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.card_edge_service import CardEdgeService
from app.services.card_protocol.card_snapshot_service import CardSnapshotService, ShareService
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.temporal_engine import RecurrenceRule, TemporalEngine
from app.services.card_service import CardService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "phase-c-test"


async def _make_plan(db_session, user_id, name: str) -> Plan:
    plan = Plan(
        user_id=user_id,
        name=name,
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
        description=f"{name} description",
        subject="Systems",
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
        tags=["phase-c"],
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_snapshot_preserves_plan_tree_and_reference_edges(db_session, test_user):
    fake_bus = FakeEventBus()
    plan = await _make_plan(db_session, test_user.id, "Portable Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase = await PhaseService(db_session, fake_bus).create_phase(
        plan_card_id=plan_card.id,
        name="Foundation",
        phase_index=1,
        user_id=test_user.id,
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Portable Task")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    await TemporalEngine(db_session, fake_bus).set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="weekly", days_of_week=[1, 3]),
        user_id=test_user.id,
    )

    knowledge_card = await CardService(db_session, fake_bus).create_card(
        card_type=CardType.KNOWLEDGE,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Transferable Concept"},
        tags=["knowledge"],
        lifecycle_status=plan_card.lifecycle_status,
    )
    await CardEdgeService(db_session, fake_bus).create_edge(
        from_card_id=task_card.id,
        to_card_id=knowledge_card.id,
        edge_type=EdgeType.REFERENCES,
    )
    await db_session.commit()

    snapshot = await CardSnapshotService(db_session, fake_bus).create_snapshot(
        card_id=plan_card.id,
        include_children=True,
        max_depth=4,
    )

    payload = dict(snapshot.payload or {})
    cards = payload.get("cards") or []
    edges = payload.get("edges") or []
    assert len(cards) >= 4
    assert any(card["card_type"] == CardType.PLAN.value for card in cards)
    assert any(card["card_type"] == CardType.PHASE.value for card in cards)
    assert any(card["card_type"] == CardType.TASK.value for card in cards)
    assert any(card["card_type"] == CardType.KNOWLEDGE.value for card in cards)
    assert any(edge["type"] == EdgeType.CONTAINS.value for edge in edges)
    assert any(edge["type"] == EdgeType.REFERENCES.value for edge in edges)


@pytest.mark.asyncio
async def test_adopt_plan_share_creates_independent_plan_with_phases_and_tasks(db_session, test_user):
    fake_bus = FakeEventBus()
    adopter = User(
        username="adopter",
        email="adopter@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(adopter)
    await db_session.commit()
    await db_session.refresh(adopter)

    plan = await _make_plan(db_session, test_user.id, "Shared Plan")
    plan_card = await PlanAdapter(db_session, fake_bus).plan_to_card(plan)
    phase_service = PhaseService(db_session, fake_bus)
    phase_one = await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase One",
        phase_index=1,
        user_id=test_user.id,
    )
    await phase_service.create_phase(
        plan_card_id=plan_card.id,
        name="Phase Two",
        phase_index=2,
        user_id=test_user.id,
    )
    task = await _make_task(db_session, user_id=test_user.id, plan_id=plan.id, title="Shared Task")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    await TemporalEngine(db_session, fake_bus).set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(pattern="daily", end_condition="count", end_value=5),
        user_id=test_user.id,
    )
    await db_session.commit()

    share_service = ShareService(db_session, fake_bus)
    share = await share_service.share_card(
        card_id=plan_card.id,
        user_id=test_user.id,
        scope=ShareScope.USER,
        target_id=adopter.id,
        permission=SharePermission.ADOPT,
        include_children=True,
        max_depth=4,
    )
    result = await share_service.adopt_shared_card(
        share_record_id=share.id,
        user_id=adopter.id,
        import_mode=ImportMode.ADOPT,
        modifications={"name": "Adopted Shared Plan"},
    )
    await db_session.commit()

    assert result.imported_root_plan_id is not None
    adopted_plan = await db_session.get(Plan, result.imported_root_plan_id)
    assert adopted_plan is not None
    assert adopted_plan.name == "Adopted Shared Plan"
    assert adopted_plan.source == "community_shared"
    assert result.root_card.source_type == CardSourceType.ADOPTED

    phase_payload = await PhaseService(db_session, fake_bus).get_phase_summaries_for_legacy_plan(
        legacy_plan_id=adopted_plan.id,
        user_id=adopter.id,
    )
    assert [item["title"] for item in phase_payload["phases"]] == ["Phase One", "Phase Two"]

    task_result = await db_session.execute(select(Task).where(Task.plan_id == adopted_plan.id))
    adopted_tasks = list(task_result.scalars().all())
    assert len(adopted_tasks) == 1

    edge_result = await db_session.execute(
        select(Card).where(
            Card.id == result.root_card.id,
            Card.not_deleted_filter(),
        )
    )
    assert edge_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_fork_task_share_preserves_recurrence_rule(db_session, test_user):
    fake_bus = FakeEventBus()
    recipient = User(
        username="forker",
        email="forker@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(recipient)
    await db_session.commit()
    await db_session.refresh(recipient)

    task = await _make_task(db_session, user_id=test_user.id, plan_id=None, title="Forkable Task")
    task_card = await TaskAdapter(db_session, fake_bus).task_to_card(task)
    await TemporalEngine(db_session, fake_bus).set_task_recurrence(
        task_card_id=task_card.id,
        rule=RecurrenceRule(
            pattern="weekly",
            days_of_week=[2, 4],
            end_condition="date",
            end_value=date(2026, 4, 30).isoformat(),
        ),
        user_id=test_user.id,
    )
    await db_session.commit()

    share = await ShareService(db_session, fake_bus).share_card(
        card_id=task_card.id,
        user_id=test_user.id,
        scope=ShareScope.USER,
        target_id=recipient.id,
        permission=SharePermission.FORK,
        include_children=True,
        max_depth=2,
    )
    result = await ShareService(db_session, fake_bus).adopt_shared_card(
        share_record_id=share.id,
        user_id=recipient.id,
        import_mode=ImportMode.FORK,
    )
    await db_session.commit()

    assert result.imported_root_task_id is not None
    imported_task = await db_session.get(Task, result.imported_root_task_id)
    assert imported_task is not None
    assert result.root_card.source_type == CardSourceType.FORKED
    recurrence = (result.root_card.metadata_ or {}).get("temporal", {}).get("recurrence")
    assert recurrence is not None
    assert recurrence["pattern"] == "weekly"
    assert recurrence["days_of_week"] == [2, 4]
