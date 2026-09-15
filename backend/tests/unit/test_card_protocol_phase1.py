from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.time_utils import utcnow
from app.models.card_protocol import (
    BindingMode,
    Card,
    CardEdge,
    CardLifecycleStatus,
    CardShareRecord,
    CardType,
    EdgeType,
    SharePermission,
    ShareScope,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter
from app.services.card_protocol.mastery_bridge import ErrorMasteryBridge
from app.services.card_protocol.share_service import ShareService
from app.services.card_service import CardService
from app.services.plan_service import PlanService
from app.services.task_occurrence_service import OccurrenceStatus, TaskOccurrenceService
from app.services.task_service import TaskService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "test-id"


@pytest.mark.asyncio
async def test_share_service_rejects_revoked_expired_and_private_shares(db_session):
    service = ShareService(db_session)
    viewer_id = uuid4()
    owner_id = uuid4()

    revoked = CardShareRecord(
        snapshot_id=uuid4(),
        shared_by_user_id=owner_id,
        scope=ShareScope.PUBLIC,
        permission=SharePermission.ADOPT,
        revoked_at=utcnow(),
    )
    with pytest.raises(ValueError, match="revoked"):
        await service._assert_share_access(revoked, viewer_id)

    expired = CardShareRecord(
        snapshot_id=uuid4(),
        shared_by_user_id=owner_id,
        scope=ShareScope.PUBLIC,
        permission=SharePermission.ADOPT,
        metadata_={"expires_at": (utcnow() - timedelta(minutes=1)).isoformat()},
    )
    with pytest.raises(ValueError, match="expired"):
        await service._assert_share_access(expired, viewer_id)

    private = CardShareRecord(
        snapshot_id=uuid4(),
        shared_by_user_id=owner_id,
        scope=ShareScope.USER,
        permission=SharePermission.ADOPT,
    )
    with pytest.raises(ValueError, match="private"):
        await service._assert_share_access(private, viewer_id)


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


@pytest.mark.asyncio
async def test_card_service_facade_manages_edges_snapshots_and_soft_delete(db_session, test_user):
    fake_bus = FakeEventBus()
    service = CardService(db_session, fake_bus)
    plan = await service.create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Card facade plan"},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )
    task = await service.create_card(
        card_type=CardType.TASK,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"title": "Card facade task"},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )

    edge = await service.create_edge(
        from_card_id=plan.id,
        to_card_id=task.id,
        edge_type=EdgeType.CONTAINS,
        binding_mode=BindingMode.OWNED,
        order_index=1000,
    )
    await db_session.commit()

    children = await service.get_children(plan.id, edge_type=EdgeType.CONTAINS)
    parents = await service.get_parents(task.id, edge_type=EdgeType.CONTAINS)
    assert [(item.id, item.order_index) for item, _ in children] == [(edge.id, 1000)]
    assert [parent.id for _, parent in parents] == [plan.id]

    first_snapshot = await service.create_snapshot(card_id=plan.id, include_children=True, max_depth=2)
    second_snapshot = await service.create_snapshot(card_id=plan.id, include_children=False, max_depth=1)
    await db_session.commit()

    snapshots = await service.get_snapshots(plan.id)
    latest = await service.get_latest_snapshot(plan.id)
    assert [snapshot.id for snapshot in snapshots[:2]] == [second_snapshot.id, first_snapshot.id]
    assert latest is not None
    assert latest.id == second_snapshot.id

    deleted = await service.delete_card(task.id)
    await db_session.commit()

    assert deleted is True
    assert await service.get_card(task.id) is None
    assert await service.get_children(plan.id, edge_type=EdgeType.CONTAINS) == []

    event_types = [event_type for event_type, _ in fake_bus.events]
    assert "card_edge.created" in event_types
    assert "card.deleted" in event_types


@pytest.mark.asyncio
async def test_plan_and_task_services_dual_write_card_projection(db_session, test_user):
    with (
        patch("app.services.plan_quota_service.PlanQuotaService") as quota_service_cls,
        patch("app.services.plan_service.Stage33JourneyEventService.publish", AsyncMock(return_value="1-0")),
        patch("app.services.task_service.task_document_service.auto_link_from_task_context", AsyncMock()),
        patch("app.services.focus_context_service.focus_context_service.preload_for_task", AsyncMock()),
        patch("app.services.task_state_sync.TaskStateSyncService.on_task_created", AsyncMock()),
    ):
        quota_service_cls.return_value.get_quota_status = AsyncMock(return_value=SimpleNamespace(used=0))
        plan = await PlanService.create(
            db=db_session,
            obj_in=PlanCreate(
                name="Card dual-write plan",
                type=PlanType.SPRINT,
                plan_stage=PlanStage.SPRINT,
                subject="计算机网络",
                daily_available_minutes=90,
            ),
            user_id=test_user.id,
            skip_quota_check=True,
        )
        task = await TaskService.create(
            db=db_session,
            obj_in=TaskCreate(
                title="Card dual-write task",
                type=TaskType.LEARNING,
                plan_id=plan.id,
                estimated_minutes=45,
                difficulty=2,
                energy_cost=2,
                guide_content="完成一次闭卷复述",
                tags=["规划生成", "day:1"],
            ),
            user_id=test_user.id,
        )

    plan_card = (
        await db_session.execute(
            select(Card).where(
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(plan.id),
                Card.not_deleted_filter(),
            )
        )
    ).scalar_one()
    task_card = (
        await db_session.execute(
            select(Card).where(
                Card.card_type == CardType.TASK,
                Card.metadata_["legacy_task_id"].as_string() == str(task.id),
                Card.not_deleted_filter(),
            )
        )
    ).scalar_one()

    assert plan_card.metadata_["name"] == plan.name
    assert task_card.metadata_["legacy_plan_id"] == str(plan.id)

    phase_card_id = plan_card.metadata_["current_phase_card_id"]
    edge = (
        await db_session.execute(
            select(CardEdge).where(
                CardEdge.from_card_id == phase_card_id,
                CardEdge.to_card_id == task_card.id,
                CardEdge.edge_type == EdgeType.CONTAINS,
                CardEdge.active.is_(True),
            )
        )
    ).scalar_one()
    assert edge.metadata_["source"] == "legacy_task_adapter"
