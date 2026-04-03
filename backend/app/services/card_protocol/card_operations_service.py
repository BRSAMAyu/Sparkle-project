"""
Card Operations Service

Phase A foundation for card mobility:
- move cards across plan/phase containment
- create/remove typed links
- inspect tree structure
- search canonical cards

This service intentionally bridges both truths during migration:
- canonical card graph
- legacy plans/tasks tables
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.card_protocol import (
    BindingMode,
    Card,
    CardCreatedBy,
    CardEdge,
    CardLifecycleStatus,
    CardType,
    EdgeType,
    OccurrenceStatus,
)
from app.models.plan import Plan
from app.models.task import Task
from app.services.card_edge_service import CardEdgeService
from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService
from app.services.card_service import CardService
from app.services.plan_service import PlanService
from app.services.task_state_sync import TaskStateSyncService
from app.services.task_occurrence_service import TaskOccurrenceService


@dataclass
class MoveResult:
    card_id: str
    card_type: str
    old_parent_card_id: str | None
    new_parent_card_id: str | None
    old_plan_card_id: str | None = None
    new_plan_card_id: str | None = None
    old_phase_card_id: str | None = None
    new_phase_card_id: str | None = None
    old_legacy_plan_id: str | None = None
    new_legacy_plan_id: str | None = None
    moved_occurrence_count: int = 0
    cancelled_occurrence_count: int = 0


@dataclass
class CardTreeNode:
    card_id: str
    card_type: str
    lifecycle_status: str
    metadata: dict[str, Any]
    tags: list[str]
    order_index: int | None = None
    occurrence_count: int | None = None
    children: list["CardTreeNode"] = field(default_factory=list)


class CardOperationsService:
    """Universal operations across canonical cards."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)
        self.occurrence_service = TaskOccurrenceService(db, event_bus)

    async def move_card(
        self,
        *,
        card_id: UUID,
        new_parent_card_id: UUID | None,
        user_id: UUID,
        position: int | None = None,
    ) -> MoveResult:
        card = await self.card_service.get_card(card_id)
        if not card or card.owner_id != user_id:
            raise ValueError("Card not found")

        # Cycle detection: card must not be an ancestor of its proposed new parent.
        if new_parent_card_id and await self._would_create_cycle(card_id, new_parent_card_id):
            raise ValueError(
                f"Cannot move card {card_id} into {new_parent_card_id}: "
                "that would create a containment cycle in the card graph"
            )

        old_parent_edge, old_parent = await self._get_active_parent(card_id)
        normalized_parent, new_plan_card, new_phase_card = await self._normalize_target_parent(
            card=card,
            new_parent_card_id=new_parent_card_id,
            user_id=user_id,
        )

        old_plan_card, old_phase_card = await self._resolve_card_context(card, explicit_parent=old_parent)
        old_legacy_plan_id = self._legacy_plan_id(old_plan_card)
        new_legacy_plan_id = self._legacy_plan_id(new_plan_card)

        if old_parent_edge:
            await self.edge_service.deactivate_edge(old_parent_edge.id)

        if normalized_parent:
            new_order_index = (
                position if position is not None else await self._next_child_order_index(normalized_parent.id)
            )
            await self.edge_service.create_edge(
                from_card_id=normalized_parent.id,
                to_card_id=card.id,
                edge_type=EdgeType.CONTAINS,
                binding_mode=BindingMode.OWNED,
                order_index=new_order_index,
                metadata={"source": "card_operations.move"},
            )

        await self._append_transition_log(
            card=card,
            transition={
                "type": "MOVE",
                "moved_at": datetime.utcnow().isoformat(),
                "old_parent_card_id": str(old_parent.id) if old_parent else None,
                "new_parent_card_id": str(normalized_parent.id) if normalized_parent else None,
                "old_plan_card_id": str(old_plan_card.id) if old_plan_card else None,
                "new_plan_card_id": str(new_plan_card.id) if new_plan_card else None,
                "old_phase_card_id": str(old_phase_card.id) if old_phase_card else None,
                "new_phase_card_id": str(new_phase_card.id) if new_phase_card else None,
            },
        )

        moved_occurrence_count = 0
        cancelled_occurrence_count = 0
        if card.card_type == CardType.TASK:
            moved_occurrence_count, cancelled_occurrence_count = await self._sync_task_move(
                task_card=card,
                old_plan_card=old_plan_card,
                new_plan_card=new_plan_card,
                new_phase_card=new_phase_card,
            )

        await self.db.flush()
        await self._refresh_related_plan_artifacts(old_plan_card, new_plan_card)

        result = MoveResult(
            card_id=str(card.id),
            card_type=card.card_type.value,
            old_parent_card_id=str(old_parent.id) if old_parent else None,
            new_parent_card_id=str(normalized_parent.id) if normalized_parent else None,
            old_plan_card_id=str(old_plan_card.id) if old_plan_card else None,
            new_plan_card_id=str(new_plan_card.id) if new_plan_card else None,
            old_phase_card_id=str(old_phase_card.id) if old_phase_card else None,
            new_phase_card_id=str(new_phase_card.id) if new_phase_card else None,
            old_legacy_plan_id=old_legacy_plan_id,
            new_legacy_plan_id=new_legacy_plan_id,
            moved_occurrence_count=moved_occurrence_count,
            cancelled_occurrence_count=cancelled_occurrence_count,
        )
        if self.event_bus:
            await self.event_bus.publish(
                "card.moved",
                {
                    "event_type": "card.moved",
                    **asdict(result),
                },
            )
        return result

    async def bulk_move_cards(
        self,
        *,
        card_ids: list[UUID],
        new_parent_card_id: UUID | None,
        user_id: UUID,
    ) -> list[MoveResult]:
        results: list[MoveResult] = []
        for card_id in card_ids:
            results.append(
                await self.move_card(
                    card_id=card_id,
                    new_parent_card_id=new_parent_card_id,
                    user_id=user_id,
                )
            )
        return results

    async def link_cards(
        self,
        *,
        source_card_id: UUID,
        target_card_id: UUID,
        link_type: EdgeType,
        user_id: UUID,
        metadata: dict | None = None,
        binding_mode: BindingMode = BindingMode.REFERENCE,
    ) -> CardEdge:
        source = await self.card_service.get_card(source_card_id)
        target = await self.card_service.get_card(target_card_id)
        if not source or not target or source.owner_id != user_id or target.owner_id != user_id:
            raise ValueError("Card not found")
        return await self.edge_service.create_edge(
            from_card_id=source_card_id,
            to_card_id=target_card_id,
            edge_type=link_type,
            binding_mode=binding_mode,
            metadata=metadata or {},
        )

    async def unlink_cards(
        self,
        *,
        source_card_id: UUID,
        target_card_id: UUID,
        link_type: EdgeType,
        user_id: UUID,
    ) -> None:
        source = await self.card_service.get_card(source_card_id)
        if not source or source.owner_id != user_id:
            raise ValueError("Card not found")

        stmt = select(CardEdge).where(
            CardEdge.from_card_id == source_card_id,
            CardEdge.to_card_id == target_card_id,
            CardEdge.edge_type == link_type,
            CardEdge.active.is_(True),
        )
        result = await self.db.execute(stmt)
        edge = result.scalar_one_or_none()
        if edge:
            await self.edge_service.deactivate_edge(edge.id)

    async def get_card_tree(
        self,
        *,
        root_card_id: UUID,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        root = await self.card_service.get_card(root_card_id)
        if not root:
            raise ValueError("Card not found")
        node = await self._build_tree_node(root, max_depth=max_depth, current_depth=0, order_index=None)
        return asdict(node)

    async def search_cards(
        self,
        *,
        user_id: UUID,
        card_type: CardType | None = None,
        status: CardLifecycleStatus | None = None,
        tags: list[str] | None = None,
        text_query: str | None = None,
        parent_card_id: UUID | None = None,
        legacy_task_id: UUID | None = None,
        legacy_plan_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Card]:
        stmt = select(Card).where(Card.owner_id == user_id, Card.not_deleted_filter())
        if card_type:
            stmt = stmt.where(Card.card_type == card_type)
        if status:
            stmt = stmt.where(Card.lifecycle_status == status)
        if legacy_task_id:
            stmt = stmt.where(Card.metadata_["legacy_task_id"].as_string() == str(legacy_task_id))
        if legacy_plan_id:
            stmt = stmt.where(Card.metadata_["legacy_plan_id"].as_string() == str(legacy_plan_id))
        if tags:
            for tag in tags:
                stmt = stmt.where(cast(Card.tags, String).ilike(f'%"{tag}"%'))
        if text_query:
            pattern = f"%{text_query.strip()}%"
            stmt = stmt.where(
                or_(
                    cast(Card.metadata_, String).ilike(pattern),
                    cast(Card.tags, String).ilike(pattern),
                )
            )
        if parent_card_id:
            stmt = stmt.join(
                CardEdge,
                and_(
                    CardEdge.to_card_id == Card.id,
                    CardEdge.edge_type == EdgeType.CONTAINS,
                    CardEdge.active.is_(True),
                    CardEdge.from_card_id == parent_card_id,
                ),
            )

        stmt = stmt.order_by(Card.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _would_create_cycle(self, card_id: UUID, proposed_parent_id: UUID) -> bool:
        """Return True if making proposed_parent_id a CONTAINS parent of card_id would form a cycle.

        Traverses the ancestor chain of proposed_parent_id upward; if we reach card_id
        (or they are the same card) a cycle would be created.
        """
        if card_id == proposed_parent_id:
            return True
        visited: set[UUID] = set()
        frontier = [proposed_parent_id]
        while frontier:
            current_id = frontier.pop()
            if current_id in visited:
                continue
            visited.add(current_id)
            parents = await self.edge_service.get_parents(current_id, edge_type=EdgeType.CONTAINS, active_only=True)
            for _, ancestor in parents:
                if ancestor.id == card_id:
                    return True
                if ancestor.id not in visited:
                    frontier.append(ancestor.id)
        return False

    async def _get_active_parent(self, card_id: UUID) -> tuple[CardEdge | None, Card | None]:
        parents = await self.edge_service.get_parents(card_id, edge_type=EdgeType.CONTAINS, active_only=True)
        if not parents:
            return None, None
        edge, parent = parents[0]
        return edge, parent

    async def _normalize_target_parent(
        self,
        *,
        card: Card,
        new_parent_card_id: UUID | None,
        user_id: UUID,
    ) -> tuple[Card | None, Card | None, Card | None]:
        if new_parent_card_id is None:
            return None, None, None

        parent = await self.card_service.get_card(new_parent_card_id)
        if not parent or parent.owner_id != user_id:
            raise ValueError("Target parent not found")
        if parent.id == card.id:
            raise ValueError("Card cannot contain itself")

        if card.card_type == CardType.TASK:
            if parent.card_type == CardType.PLAN:
                phase = await self._resolve_active_phase_for_plan(parent)
                return phase, parent, phase
            if parent.card_type != CardType.PHASE:
                raise ValueError("TASK cards can only move under PLAN or PHASE")
            plan = await self._resolve_plan_for_phase(parent)
            return parent, plan, parent

        if card.card_type == CardType.PHASE:
            if parent.card_type != CardType.PLAN:
                raise ValueError("PHASE cards can only move under PLAN")
            return parent, parent, card

        return parent, None, None

    async def _resolve_active_phase_for_plan(self, plan_card: Card) -> Card:
        current_phase_id = (plan_card.metadata_ or {}).get("current_phase_card_id")
        if current_phase_id:
            phase = await self.card_service.get_card(UUID(str(current_phase_id)))
            if phase:
                return phase

        children = await self.edge_service.get_children(plan_card.id, edge_type=EdgeType.CONTAINS)
        for _, child in children:
            if child.card_type == CardType.PHASE:
                return child
        raise ValueError("Target PLAN has no phase available")

    async def _resolve_plan_for_phase(self, phase_card: Card) -> Card | None:
        parents = await self.edge_service.get_parents(phase_card.id, edge_type=EdgeType.CONTAINS, active_only=True)
        for _, parent in parents:
            if parent.card_type == CardType.PLAN:
                return parent
        return None

    async def _resolve_card_context(
        self,
        card: Card,
        *,
        explicit_parent: Card | None,
    ) -> tuple[Card | None, Card | None]:
        if card.card_type == CardType.PLAN:
            return card, None
        if card.card_type == CardType.PHASE:
            return await self._resolve_plan_for_phase(card), card
        if card.card_type == CardType.TASK:
            parent = explicit_parent
            if not parent:
                _, parent = await self._get_active_parent(card.id)
            if not parent:
                return None, None
            if parent.card_type == CardType.PHASE:
                return await self._resolve_plan_for_phase(parent), parent
            if parent.card_type == CardType.PLAN:
                return parent, None
        return None, None

    async def _next_child_order_index(self, parent_card_id: UUID) -> int:
        stmt = select(func.max(CardEdge.order_index)).where(
            CardEdge.from_card_id == parent_card_id,
            CardEdge.edge_type == EdgeType.CONTAINS,
            CardEdge.active.is_(True),
        )
        result = await self.db.execute(stmt)
        current = result.scalar_one_or_none()
        return int(current or 0) + 1000

    async def _append_transition_log(self, *, card: Card, transition: dict[str, Any]) -> None:
        metadata = dict(card.metadata_ or {})
        transition_log = list(metadata.get("transition_log") or [])
        transition_log.append(transition)
        metadata["transition_log"] = transition_log[-50:]
        if "legacy_plan_id" not in metadata:
            metadata["legacy_plan_id"] = None
        card.metadata_ = metadata
        card.version += 1
        card.updated_by = CardCreatedBy.SYSTEM
        await self.db.flush()

    async def _sync_task_move(
        self,
        *,
        task_card: Card,
        old_plan_card: Card | None,
        new_plan_card: Card | None,
        new_phase_card: Card | None,
    ) -> tuple[int, int]:
        legacy_task_id = (task_card.metadata_ or {}).get("legacy_task_id")
        task: Task | None = None
        if legacy_task_id:
            task = await self.db.get(Task, UUID(str(legacy_task_id)))

        old_legacy_plan_id = self._legacy_plan_id(old_plan_card)
        new_legacy_plan_id = self._legacy_plan_id(new_plan_card)
        if task:
            task.plan_id = UUID(new_legacy_plan_id) if new_legacy_plan_id else None
            task_card_meta = dict(task_card.metadata_ or {})
            task_card_meta["legacy_plan_id"] = new_legacy_plan_id
            task_card.metadata_ = task_card_meta
            task_card.version += 1
            task_card.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()

        moved_occurrence_count = 0
        cancelled_occurrence_count = 0
        from app.models.card_protocol import TaskOccurrence  # local import to avoid cycle

        occ_stmt = select(TaskOccurrence).where(
            TaskOccurrence.series_card_id == task_card.id,
            TaskOccurrence.occurrence_status.in_(
                [
                    OccurrenceStatus.PLANNED,
                    OccurrenceStatus.READY,
                    OccurrenceStatus.DEFERRED,
                ]
            ),
        )
        result = await self.db.execute(occ_stmt)
        for occurrence in result.scalars().all():
            if new_plan_card:
                occurrence.plan_card_id = new_plan_card.id
                occurrence.phase_card_id = new_phase_card.id if new_phase_card else None
                moved_occurrence_count += 1
            else:
                occurrence.plan_card_id = None
                occurrence.phase_card_id = None
                occurrence.occurrence_status = OccurrenceStatus.CANCELLED
                cancelled_occurrence_count += 1
        await self.db.flush()

        if task:
            if old_legacy_plan_id:
                await PlanService.update_progress(self.db, UUID(old_legacy_plan_id), task.user_id)
            if new_legacy_plan_id and new_legacy_plan_id != old_legacy_plan_id:
                await PlanService.update_progress(self.db, UUID(new_legacy_plan_id), task.user_id)
            await self._sync_legacy_plan_state_indexes(
                task=task,
                old_legacy_plan_id=old_legacy_plan_id,
                new_legacy_plan_id=new_legacy_plan_id,
            )
        return moved_occurrence_count, cancelled_occurrence_count

    async def _refresh_related_plan_artifacts(self, old_plan_card: Card | None, new_plan_card: Card | None) -> None:
        service = MainChainArtifactService(self.db, self.event_bus)
        refreshed: set[UUID] = set()
        for plan_card in (old_plan_card, new_plan_card):
            if not plan_card or plan_card.id in refreshed:
                continue
            refreshed.add(plan_card.id)
            await service.refresh_active_phase_pack(
                plan_card_id=plan_card.id,
                generated_reason="card_moved",
            )

    def _legacy_plan_id(self, plan_card: Card | None) -> str | None:
        if not plan_card:
            return None
        return (plan_card.metadata_ or {}).get("legacy_plan_id")

    async def _sync_legacy_plan_state_indexes(
        self,
        *,
        task: Task,
        old_legacy_plan_id: str | None,
        new_legacy_plan_id: str | None,
    ) -> None:
        sync_service = TaskStateSyncService(self.db)
        refreshed: set[str] = set()
        for raw_plan_id in (old_legacy_plan_id, new_legacy_plan_id):
            if not raw_plan_id or raw_plan_id in refreshed:
                continue
            refreshed.add(raw_plan_id)
            try:
                plan_id = UUID(raw_plan_id)
            except ValueError:
                continue
            await sync_service.rebuild_task_index(task.user_id, plan_id)
            await sync_service.sync_task_summaries(task.user_id, plan_id)

    async def _build_tree_node(
        self,
        card: Card,
        *,
        max_depth: int,
        current_depth: int,
        order_index: int | None,
    ) -> CardTreeNode:
        occurrence_count = None
        if card.card_type == CardType.TASK:
            from app.models.card_protocol import TaskOccurrence

            stmt = select(func.count(TaskOccurrence.id)).where(TaskOccurrence.series_card_id == card.id)
            result = await self.db.execute(stmt)
            occurrence_count = int(result.scalar_one() or 0)

        node = CardTreeNode(
            card_id=str(card.id),
            card_type=card.card_type.value,
            lifecycle_status=card.lifecycle_status.value,
            metadata=dict(card.metadata_ or {}),
            tags=list(card.tags or []),
            order_index=order_index,
            occurrence_count=occurrence_count,
        )
        if current_depth >= max_depth:
            return node

        children = await self.edge_service.get_children(card.id, edge_type=EdgeType.CONTAINS, active_only=True)
        for edge, child in children:
            node.children.append(
                await self._build_tree_node(
                    child,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    order_index=edge.order_index,
                )
            )
        return node
