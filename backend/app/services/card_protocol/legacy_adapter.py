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

from app.core.event_bus import EventBus
from app.models.card_protocol import (
    BindingMode,
    Card,
    CardCreatedBy,
    CardEdge,
    CardLifecycleStatus,
    CardSourceType,
    CardType,
    CardVisibility,
    EdgeType,
)
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus
from app.services.card_edge_service import CardEdgeService
from app.services.card_service import CardService

# ---------------------------------------------------------------------------
# Legacy Plan → Card Protocol mapping
# ---------------------------------------------------------------------------

_PLAN_TYPE_TO_KIND = {
    PlanType.SPRINT: "SPRINT",
    PlanType.GROWTH: "GROWTH",
}


def _plan_to_lifecycle(plan: Plan) -> CardLifecycleStatus:
    """Map the legacy plan model to card lifecycle without inventing missing states."""
    if not plan.is_active:
        return CardLifecycleStatus.ARCHIVED
    if plan.plan_stage == PlanStage.PAUSED:
        return CardLifecycleStatus.PAUSED
    if float(plan.progress or 0.0) >= 1.0:
        return CardLifecycleStatus.COMPLETED
    return CardLifecycleStatus.ACTIVE


class PlanAdapter:
    """Projects legacy Plan records into card protocol cards.

    During dual-write phase, this adapter:
    1. Creates a PLAN card when a legacy plan is created
    2. Keeps the card in sync with the legacy plan status
    3. Stores the legacy plan_id in card metadata for traceability
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
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
            "mastery_level": float(plan.mastery_level) if plan.mastery_level is not None else None,
            "progress": float(plan.progress) if plan.progress is not None else None,
            "daily_available_minutes": plan.daily_available_minutes,
            "priority": plan.priority.value if plan.priority else None,
            "is_primary": plan.is_primary,
            "legacy_plan_stage": plan.plan_stage.value if plan.plan_stage else None,
            "legacy_is_active": plan.is_active,
        }

        lifecycle = _plan_to_lifecycle(plan)

        if existing:
            # Update existing card
            existing_meta = dict(existing.metadata_ or {})
            existing_meta.update(card_metadata)
            existing.metadata_ = existing_meta
            existing.lifecycle_status = lifecycle
            existing.version += 1
            existing.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()
            card = existing
        else:
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

        phase_card = await self._ensure_default_phase_card(plan, plan_card=card, lifecycle=lifecycle)
        if phase_card and card.metadata_.get("current_phase_card_id") != str(phase_card.id):
            plan_meta = dict(card.metadata_ or {})
            plan_meta["current_phase_card_id"] = str(phase_card.id)
            card.metadata_ = plan_meta
            card.version += 1
            card.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()

        # Phase 3: Auto-initialize GLOBAL_COMPASS + STRATEGY_MAP artifacts
        await self._ensure_phase3_artifacts(plan, card)
        await self._ensure_phase4_active_pack(plan, card)

        return card

    async def _find_card_by_legacy_plan(self, plan_id: uuid.UUID) -> Card | None:
        """Find a card that projects a specific legacy plan."""
        stmt = select(Card).where(
            Card.card_type == CardType.PLAN,
            Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _ensure_default_phase_card(
        self,
        plan: Plan,
        *,
        plan_card: Card,
        lifecycle: CardLifecycleStatus,
    ) -> Card:
        phase = await self._find_default_phase_card(plan.id)
        phase_metadata = {
            "legacy_plan_id": str(plan.id),
            "synthetic_phase": True,
            "legacy_phase_role": "ACTIVE_EXECUTION_SLICE",
            "title": f"{plan.name} Execution Phase",
            "objective": plan.description or plan.name,
            "phase_index": 1,
        }

        if phase:
            phase_meta = dict(phase.metadata_ or {})
            phase_meta.update(phase_metadata)
            phase.metadata_ = phase_meta
            phase.lifecycle_status = lifecycle
            phase.version += 1
            phase.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()
        else:
            phase = await self.card_service.create_card(
                card_type=CardType.PHASE,
                owner_id=plan.user_id,
                holder_id=plan.user_id,
                metadata=phase_metadata,
                tags=["legacy", "synthetic-phase"],
                source_type=CardSourceType.GENERATED,
                created_by=CardCreatedBy.SYSTEM,
                visibility=CardVisibility.PRIVATE,
                lifecycle_status=lifecycle,
            )

        await self.edge_service.create_edge(
            from_card_id=plan_card.id,
            to_card_id=phase.id,
            edge_type=EdgeType.CONTAINS,
            binding_mode=BindingMode.OWNED,
            order_index=0,
            metadata={"synthetic": True, "source": "legacy_plan_adapter"},
        )
        return phase

    async def _find_default_phase_card(self, plan_id: uuid.UUID) -> Card | None:
        stmt = select(Card).where(
            Card.card_type == CardType.PHASE,
            Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        for card in result.scalars().all():
            if (card.metadata_ or {}).get("synthetic_phase") is True:
                return card
        return None

    async def _ensure_phase3_artifacts(self, plan: Plan, plan_card: Card) -> None:
        """Auto-initialize GLOBAL_COMPASS and STRATEGY_MAP for a plan card.

        This is the Phase 3 onboarding: when a legacy plan gets projected
        into the card protocol, we ensure the governance artifacts exist
        so the ParameterCompiler can work.
        """
        try:
            from app.services.card_protocol.global_compass_manager import GlobalCompassManager
            from app.services.card_protocol.strategy_map_manager import StrategyMapManager

            compass_mgr = GlobalCompassManager(self.db, self.event_bus)
            strategy_mgr = StrategyMapManager(self.db, self.event_bus)

            compass = await compass_mgr.get_or_initialize(
                plan_card_id=plan_card.id,
                user_id=plan.user_id,
                plan_context={"goal": plan.name},
            )
            strategy = await strategy_mgr.get_or_initialize(
                plan_card_id=plan_card.id,
                user_id=plan.user_id,
                plan_structure={"phase_count": 1, "task_density": 0},
            )

            plan_meta = dict(plan_card.metadata_ or {})
            metadata_patch = {
                "global_compass_artifact_id": str(compass.id),
                "global_compass_version": compass.version,
                "strategy_map_artifact_id": str(strategy.id),
                "strategy_map_version": strategy.version,
            }
            if any(plan_meta.get(key) != value for key, value in metadata_patch.items()):
                plan_meta.update(metadata_patch)
                plan_card.metadata_ = plan_meta
                plan_card.version += 1
                plan_card.updated_by = CardCreatedBy.SYSTEM
                await self.db.flush()
        except Exception as exc:
            from loguru import logger

            logger.warning("Phase3 artifact auto-init failed (non-fatal): {}", exc)

    async def _ensure_phase4_active_pack(self, plan: Plan, plan_card: Card) -> None:
        try:
            from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService

            service = MainChainArtifactService(self.db, self.event_bus)
            await service.refresh_active_phase_pack(
                plan_card_id=plan_card.id,
                generated_reason="plan_projection_bootstrap",
            )
        except Exception as exc:
            from loguru import logger

            logger.warning("Phase4 active phase pack bootstrap failed (non-fatal): {}", exc)


# ---------------------------------------------------------------------------
# Legacy Task → Card Protocol mapping
# ---------------------------------------------------------------------------

_TASK_STATUS_MAP = {
    TaskStatus.PENDING: CardLifecycleStatus.ACTIVE,
    TaskStatus.IN_PROGRESS: CardLifecycleStatus.ACTIVE,
    TaskStatus.STUCK: CardLifecycleStatus.ACTIVE,
    TaskStatus.COMPLETED: CardLifecycleStatus.COMPLETED,
    TaskStatus.ABANDONED: CardLifecycleStatus.CANCELLED,
}


class TaskAdapter:
    """Projects legacy Task records into card protocol cards + edges.

    For each legacy task:
    1. Creates a TASK card (canonical definition)
    2. If task has a plan_id, creates a CONTAINS edge from the plan's synthetic PHASE to the task card
    3. If task has a knowledge_node_id, creates a REFERENCES edge to a KNOWLEDGE card
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
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
            existing_meta = dict(existing.metadata_ or {})
            existing_meta.update(card_metadata)
            existing.metadata_ = existing_meta
            existing.lifecycle_status = lifecycle
            existing.version += 1
            existing.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()
            card = existing
        else:
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

        await self._sync_task_containment(task, task_card=card)
        await self._sync_task_knowledge_references(task, task_card=card)
        await self._refresh_phase4_artifacts(task)
        return card

    async def _find_card_by_legacy_task(self, task_id: uuid.UUID) -> Card | None:
        stmt = select(Card).where(
            Card.card_type == CardType.TASK,
            Card.metadata_["legacy_task_id"].as_string() == str(task_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_plan_card(self, plan_id: uuid.UUID) -> Card | None:
        stmt = select(Card).where(
            Card.card_type == CardType.PLAN,
            Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_plan_phase_card(self, plan_id: uuid.UUID) -> Card | None:
        plan_card = await self._find_plan_card(plan_id)
        if plan_card:
            current_phase_id = (plan_card.metadata_ or {}).get("current_phase_card_id")
            if current_phase_id:
                try:
                    current = await self.card_service.get_card(uuid.UUID(str(current_phase_id)))
                    if current and current.card_type == CardType.PHASE:
                        return current
                except (TypeError, ValueError):
                    pass

            children = await self.edge_service.get_children(
                plan_card.id,
                edge_type=EdgeType.CONTAINS,
                active_only=True,
            )
            for _, child in children:
                if child.card_type == CardType.PHASE and not bool((child.metadata_ or {}).get("synthetic_phase")):
                    return child

        stmt = select(Card).where(
            Card.card_type == CardType.PHASE,
            Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        for card in result.scalars().all():
            if (card.metadata_ or {}).get("synthetic_phase") is True:
                return card
        return None

    async def _find_or_create_knowledge_card(self, knowledge_node_id: uuid.UUID, user_id: uuid.UUID) -> Card | None:
        """Find existing KNOWLEDGE card for a knowledge node, or create one."""
        stmt = select(Card).where(
            Card.card_type == CardType.KNOWLEDGE,
            Card.metadata_["knowledge_node_id"].as_string() == str(knowledge_node_id),
            Card.owner_id == user_id,
            Card.not_deleted_filter(),
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

    async def _sync_task_containment(self, task: Task, *, task_card: Card) -> None:
        incoming_stmt = select(CardEdge).where(
            CardEdge.to_card_id == task_card.id,
            CardEdge.edge_type == EdgeType.CONTAINS,
            CardEdge.active.is_(True),
        )
        incoming_result = await self.db.execute(incoming_stmt)
        for edge in incoming_result.scalars().all():
            edge.active = False
            edge.removed_at = datetime.utcnow()

        if not task.plan_id:
            await self.db.flush()
            return

        phase_card = await self._find_plan_phase_card(task.plan_id)
        if not phase_card:
            plan_stmt = select(Plan).where(Plan.id == task.plan_id)
            plan_result = await self.db.execute(plan_stmt)
            plan = plan_result.scalar_one_or_none()
            if not plan:
                await self.db.flush()
                return
            plan_adapter = PlanAdapter(self.db, self.card_service.event_bus)
            await plan_adapter.plan_to_card(plan)
            phase_card = await self._find_plan_phase_card(task.plan_id)
            if not phase_card:
                await self.db.flush()
                return

        await self.edge_service.create_edge(
            from_card_id=phase_card.id,
            to_card_id=task_card.id,
            edge_type=EdgeType.CONTAINS,
            binding_mode=BindingMode.OWNED,
            order_index=task.order_index,
            metadata={"synthetic": True, "source": "legacy_task_adapter"},
        )

    async def _sync_task_knowledge_references(self, task: Task, *, task_card: Card) -> None:
        existing_refs_stmt = select(CardEdge).where(
            CardEdge.from_card_id == task_card.id,
            CardEdge.edge_type == EdgeType.REFERENCES,
            CardEdge.active.is_(True),
        )
        existing_refs_result = await self.db.execute(existing_refs_stmt)
        for edge in existing_refs_result.scalars().all():
            edge.active = False
            edge.removed_at = datetime.utcnow()

        if not task.knowledge_node_id:
            await self.db.flush()
            return

        knowledge_card = await self._find_or_create_knowledge_card(task.knowledge_node_id, task.user_id)
        if not knowledge_card:
            await self.db.flush()
            return

        await self.edge_service.create_edge(
            from_card_id=task_card.id,
            to_card_id=knowledge_card.id,
            edge_type=EdgeType.REFERENCES,
            binding_mode=BindingMode.REFERENCE,
            metadata={"source": "legacy_task_adapter"},
        )

    async def _refresh_phase4_artifacts(self, task: Task) -> None:
        if not task.plan_id:
            return
        try:
            from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService

            service = MainChainArtifactService(self.db, self.event_bus)
            await service.refresh_for_legacy_plan(
                legacy_plan_id=task.plan_id,
                generated_reason="task_projection_updated",
                include_reflection=False,
            )
        except Exception as exc:
            from loguru import logger

            logger.warning("Phase4 artifact refresh after task projection failed (non-fatal): {}", exc)
