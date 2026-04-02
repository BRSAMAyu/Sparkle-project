"""
Legacy adapters that project existing plans/tasks into the card protocol.

Migration rule (from ADR-0004):
  1. Introduce protocol tables
  2. Build adapters
  3. Dual-write the critical path
  4. Compare projections
  5. Cut over one consumer at a time
  6. Retire legacy only after shadow validation

These adapters are Phase 1's step 2-3. They ensure the legacy system continues
to work while the card protocol is built alongside it.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanType, PlanStatus
from app.models.task import Task, TaskStatus
from app.models.card_protocol import (
    Card,
    CardType,
    CardLifecycleStatus,
    CardVisibility,
    CardSourceType,
    CardCreatedBy,
    CardEdge,
    EdgeType,
    BindingMode,
)
from app.services.card_service import CardService
from app.services.card_edge_service import CardEdgeService
from app.core.event_bus import EventBus


# ---------------------------------------------------------------------------
# Legacy Plan → Card Protocol mapping
# ---------------------------------------------------------------------------

_PLAN_STATUS_TO_LIFECYCLE: dict[PlanStatus, CardLifecycleStatus] = {
    PlanStatus.DRAFT: CardLifecycleStatus.DRAFT,
    PlanStatus.PENDING_REVIEW: CardLifecycleStatus.DRAFT,
    PlanStatus.ACTIVE: CardLifecycleStatus.ACTIVE,
    PlanStatus.PAUSED: CardLifecycleStatus.PAUSED,
    PlanStatus.COMPLETED: CardLifecycleStatus.COMPLETED,
    PlanStatus.ARCHIVED: CardLifecycleStatus.ARCHIVED,
    PlanStatus.CANCELLED: CardLifecycleStatus.CANCELLED,
}

_PLAN_TYPE_TO_KIND = {
    PlanType.SPRINT: "SPRINT",
    PlanType.GROWTH: "GROWTH",
}


class PlanAdapter:
    """Projects legacy Plan records into card protocol cards.

    During dual-write phase, this adapter:
    1. Creates a PLAN card when a legacy plan is created
    2. Keeps the card in sync with the legacy plan status
    3. Stores the legacy plan_id in card metadata for traceability
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)

    async def plan_to_card(self, plan: Plan) -> Card:
        """Create or update a PLAN card from a legacy Plan.

        The legacy plan_id is stored in card.metadata_["legacy_plan_id"]
        for bidirectional lookup.
        """
        # Check if a card already exists for this plan
        existing = await self._find_card_by_legacy_plan(plan.id)

        card_metadata = {
            "legacy_plan_id": str(plan.id),
            "name": plan.name,
            "description": plan.description or "",
            "plan_kind": _PLAN_TYPE_TO_KIND.get(plan.type, "GROWTH"),
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "subject": plan.subject,
            "mastery_level": float(plan.mastery_level) if plan.mastery_level else None,
            "progress": float(plan.progress) if plan.progress else None,
            "daily_available_minutes": plan.daily_available_minutes,
            "priority": plan.priority.value if plan.priority else None,
            "is_primary": plan.is_primary,
        }

        lifecycle = _PLAN_STATUS_TO_LIFECYCLE.get(plan.plan_stage, CardLifecycleStatus.DRAFT)

        if existing:
            # Update existing card
            existing.metadata_ = card_metadata
            existing.lifecycle_status = lifecycle
            existing.version += 1
            existing.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()
            return existing

        # Create new card
        card = await self.card_service.create_card(
            card_type=CardType.PLAN,
            owner_id=plan.user_id,
            holder_id=plan.user_id,
            metadata=card_metadata,
            tags=[plan.type.value] if plan.type else [],
            source_type=CardSourceType.ORIGINAL,
            created_by=CardCreatedBy.SYSTEM,
            visibility=CardVisibility.PRIVATE,
            lifecycle_status=lifecycle,
        )
        return card

    async def _find_card_by_legacy_plan(self, plan_id: uuid.UUID) -> Card | None:
        """Find a card that projects a specific legacy plan."""
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Legacy Task → Card Protocol mapping
# ---------------------------------------------------------------------------

_TASK_STATUS_MAP = {
    TaskStatus.PENDING: CardLifecycleStatus.ACTIVE,
    TaskStatus.IN_PROGRESS: CardLifecycleStatus.ACTIVE,
    TaskStatus.COMPLETED: CardLifecycleStatus.COMPLETED,
    TaskStatus.ABANDONED: CardLifecycleStatus.CANCELLED,
}


class TaskAdapter:
    """Projects legacy Task records into card protocol cards + edges.

    For each legacy task:
    1. Creates a TASK card (canonical definition)
    2. If task has a plan_id, creates a CONTAINS edge from plan card to task card
    3. If task has a knowledge_node_id, creates a REFERENCES edge to a KNOWLEDGE card
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)

    async def task_to_card(self, task: Task) -> Card:
        """Create or update a TASK card from a legacy Task."""
        existing = await self._find_card_by_legacy_task(task.id)

        card_metadata = {
            "legacy_task_id": str(task.id),
            "legacy_plan_id": str(task.plan_id) if task.plan_id else None,
            "title": task.title,
            "description": task.guide_content or "",
            "task_kind": task.type.value,
            "effort_minutes_default": task.estimated_minutes,
            "difficulty": task.difficulty,
            "energy_cost": task.energy_cost,
            "execution_mode": task.execution_mode,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "priority": task.priority,
            "order_index": task.order_index,
            "knowledge_node_id": str(task.knowledge_node_id) if task.knowledge_node_id else None,
            "tags": task.tags if isinstance(task.tags, list) else [],
        }

        lifecycle = _TASK_STATUS_MAP.get(task.status, CardLifecycleStatus.ACTIVE)

        if existing:
            existing.metadata_ = card_metadata
            existing.lifecycle_status = lifecycle
            existing.version += 1
            existing.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()
            return existing

        card = await self.card_service.create_card(
            card_type=CardType.TASK,
            owner_id=task.user_id,
            holder_id=task.user_id,
            metadata=card_metadata,
            tags=task.tags if isinstance(task.tags, list) else [],
            source_type=CardSourceType.ORIGINAL,
            created_by=CardCreatedBy.SYSTEM,
            visibility=CardVisibility.PRIVATE,
            lifecycle_status=lifecycle,
        )

        # Create edges
        if task.plan_id:
            plan_card = await self._find_plan_card(task.plan_id)
            if plan_card:
                await self.edge_service.create_edge(
                    from_card_id=plan_card.id,
                    to_card_id=card.id,
                    edge_type=EdgeType.CONTAINS,
                    binding_mode=BindingMode.OWNED,
                    order_index=task.order_index,
                )

        if task.knowledge_node_id:
            knowledge_card = await self._find_or_create_knowledge_card(
                task.knowledge_node_id, task.user_id
            )
            if knowledge_card:
                await self.edge_service.create_edge(
                    from_card_id=card.id,
                    to_card_id=knowledge_card.id,
                    edge_type=EdgeType.REFERENCES,
                    binding_mode=BindingMode.REFERENCE,
                )

        return card

    async def _find_card_by_legacy_task(self, task_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.TASK,
                Card.metadata_["legacy_task_id"].as_string() == str(task_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_plan_card(self, plan_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_or_create_knowledge_card(
        self, knowledge_node_id: uuid.UUID, user_id: uuid.UUID
    ) -> Card | None:
        """Find existing KNOWLEDGE card for a knowledge node, or create one."""
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.KNOWLEDGE,
                Card.metadata_["knowledge_node_id"].as_string() == str(knowledge_node_id),
                Card.owner_id == user_id,
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Create a minimal KNOWLEDGE card pointing to the galaxy node
        card = await self.card_service.create_card(
            card_type=CardType.KNOWLEDGE,
            owner_id=user_id,
            metadata={"knowledge_node_id": str(knowledge_node_id)},
            created_by=CardCreatedBy.SYSTEM,
            lifecycle_status=CardLifecycleStatus.ACTIVE,
        )
        return card
