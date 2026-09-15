"""
CardService — CRUD and lifecycle management for canonical cards.

Phase 1 scope: PLAN, PHASE, TASK, KNOWLEDGE card types.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
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

if TYPE_CHECKING:
    from app.models.card_protocol import CardSnapshot


class CardService:
    """Service for Card CRUD and lifecycle operations."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_card(
        self,
        *,
        card_type: CardType,
        owner_id: uuid.UUID,
        holder_id: uuid.UUID | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
        source_type: CardSourceType = CardSourceType.ORIGINAL,
        origin_card_id: uuid.UUID | None = None,
        origin_snapshot_id: uuid.UUID | None = None,
        created_by: CardCreatedBy = CardCreatedBy.AI,
        visibility: CardVisibility = CardVisibility.PRIVATE,
        lifecycle_status: CardLifecycleStatus = CardLifecycleStatus.DRAFT,
    ) -> Card:
        card = Card(
            card_type=card_type,
            owner_id=owner_id,
            holder_id=holder_id or owner_id,
            version=1,
            metadata_=metadata or {},
            tags=tags or [],
            source_type=source_type,
            origin_card_id=origin_card_id,
            origin_snapshot_id=origin_snapshot_id,
            created_by=created_by,
            updated_by=created_by,
            visibility=visibility,
            lifecycle_status=lifecycle_status,
        )
        self.db.add(card)
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.created",
                {
                    "card_id": str(card.id),
                    "card_type": card.card_type.value,
                    "owner_id": str(card.owner_id),
                },
            )
        return card

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_card(self, card_id: uuid.UUID) -> Card | None:
        stmt = select(Card).where(Card.id == card_id, Card.not_deleted_filter())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cards_by_owner(
        self,
        owner_id: uuid.UUID,
        card_type: CardType | None = None,
        status: CardLifecycleStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Card]:
        stmt = select(Card).where(Card.owner_id == owner_id, Card.not_deleted_filter())
        if card_type:
            stmt = stmt.where(Card.card_type == card_type)
        if status:
            stmt = stmt.where(Card.lifecycle_status == status)
        stmt = stmt.order_by(Card.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_plans(self, owner_id: uuid.UUID) -> list[Card]:
        """Get all active PLAN cards for a user."""
        stmt = (
            select(Card)
            .where(
                Card.owner_id == owner_id,
                Card.card_type == CardType.PLAN,
                Card.lifecycle_status == CardLifecycleStatus.ACTIVE,
                Card.not_deleted_filter(),
            )
            .order_by(Card.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_card(
        self,
        card_id: uuid.UUID,
        *,
        metadata: dict | None = None,
        tags: list[str] | None = None,
        updated_by: CardCreatedBy = CardCreatedBy.AI,
        **kwargs,
    ) -> Card | None:
        card = await self.get_card(card_id)
        if not card:
            return None

        changes: dict[str, object] = {}
        if metadata is not None:
            # Merge metadata rather than replace
            existing = dict(card.metadata_ or {})
            existing.update(metadata)
            card.metadata_ = existing
            changes["metadata"] = metadata
        if tags is not None:
            card.tags = tags
            changes["tags"] = tags
        for key, value in kwargs.items():
            if hasattr(card, key) and key not in ("id", "created_at"):
                setattr(card, key, value)
                changes[key] = value

        card.version += 1
        card.updated_by = updated_by
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.updated",
                {
                    "card_id": str(card.id),
                    "card_type": card.card_type.value,
                    "version": card.version,
                    "changes": changes,
                },
            )
        return card

    # ------------------------------------------------------------------
    # Delete / restore
    # ------------------------------------------------------------------

    async def delete_card(
        self,
        card_id: uuid.UUID,
        *,
        soft: bool = True,
        deactivate_edges: bool = True,
    ) -> bool:
        """Delete a card and optionally deactivate its active graph edges."""
        card = await self.get_card(card_id)
        if not card:
            return False

        deactivated_edge_ids: list[str] = []
        if deactivate_edges:
            edge_stmt = select(CardEdge).where(
                or_(
                    CardEdge.from_card_id == card_id,
                    CardEdge.to_card_id == card_id,
                ),
                CardEdge.active.is_(True),
            )
            result = await self.db.execute(edge_stmt)
            now = datetime.utcnow()
            for edge in result.scalars().all():
                edge.active = False
                edge.removed_at = now
                deactivated_edge_ids.append(str(edge.id))

        if soft:
            card.soft_delete()
        else:
            await self.db.delete(card)
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.deleted",
                {
                    "card_id": str(card_id),
                    "soft": soft,
                    "deactivated_edge_ids": deactivated_edge_ids,
                },
            )
        return True

    async def restore_card(self, card_id: uuid.UUID) -> Card | None:
        stmt = select(Card).where(Card.id == card_id)
        result = await self.db.execute(stmt)
        card = result.scalar_one_or_none()
        if not card or not card.is_deleted:
            return card
        card.restore()
        card.version += 1
        await self.db.flush()
        if self.event_bus:
            await self.event_bus.publish("card.restored", {"card_id": str(card.id)})
        return card

    # ------------------------------------------------------------------
    # Relationship facade
    # ------------------------------------------------------------------

    async def create_edge(
        self,
        *,
        from_card_id: uuid.UUID,
        to_card_id: uuid.UUID,
        edge_type: EdgeType,
        binding_mode: BindingMode = BindingMode.OWNED,
        order_index: int | None = None,
        weight: float | None = None,
        temporal_window: dict | None = None,
        metadata: dict | None = None,
    ) -> CardEdge:
        from app.services.card_edge_service import CardEdgeService

        return await CardEdgeService(self.db, self.event_bus).create_edge(
            from_card_id=from_card_id,
            to_card_id=to_card_id,
            edge_type=edge_type,
            binding_mode=binding_mode,
            order_index=order_index,
            weight=weight,
            temporal_window=temporal_window,
            metadata=metadata,
        )

    async def get_children(
        self,
        card_id: uuid.UUID,
        *,
        edge_type: EdgeType | None = None,
        active_only: bool = True,
    ) -> list[tuple[CardEdge, Card]]:
        from app.services.card_edge_service import CardEdgeService

        return await CardEdgeService(self.db, self.event_bus).get_children(
            card_id,
            edge_type=edge_type,
            active_only=active_only,
        )

    async def get_parents(
        self,
        card_id: uuid.UUID,
        *,
        edge_type: EdgeType | None = None,
        active_only: bool = True,
    ) -> list[tuple[CardEdge, Card]]:
        from app.services.card_edge_service import CardEdgeService

        return await CardEdgeService(self.db, self.event_bus).get_parents(
            card_id,
            edge_type=edge_type,
            active_only=active_only,
        )

    # ------------------------------------------------------------------
    # Snapshot facade
    # ------------------------------------------------------------------

    async def create_snapshot(
        self,
        *,
        card_id: uuid.UUID,
        include_children: bool = True,
        max_depth: int = 3,
    ) -> CardSnapshot:
        from app.services.card_protocol.card_snapshot_service import CardSnapshotService

        return await CardSnapshotService(self.db, self.event_bus).create_snapshot(
            card_id=card_id,
            include_children=include_children,
            max_depth=max_depth,
        )

    async def get_snapshots(
        self,
        card_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CardSnapshot]:
        from app.models.card_protocol import CardSnapshot

        stmt = (
            select(CardSnapshot)
            .where(
                CardSnapshot.root_card_id == card_id,
                CardSnapshot.not_deleted_filter(),
            )
            .order_by(CardSnapshot.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_snapshot(self, card_id: uuid.UUID) -> CardSnapshot | None:
        snapshots = await self.get_snapshots(card_id, limit=1)
        return snapshots[0] if snapshots else None

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    async def activate(self, card_id: uuid.UUID) -> Card | None:
        return await self._transition(card_id, CardLifecycleStatus.ACTIVE)

    async def pause(self, card_id: uuid.UUID) -> Card | None:
        return await self._transition(card_id, CardLifecycleStatus.PAUSED)

    async def complete(self, card_id: uuid.UUID) -> Card | None:
        return await self._transition(card_id, CardLifecycleStatus.COMPLETED)

    async def archive(self, card_id: uuid.UUID) -> Card | None:
        return await self._transition(card_id, CardLifecycleStatus.ARCHIVED)

    async def cancel(self, card_id: uuid.UUID) -> Card | None:
        return await self._transition(card_id, CardLifecycleStatus.CANCELLED)

    async def _transition(self, card_id: uuid.UUID, target: CardLifecycleStatus) -> Card | None:
        card = await self.get_card(card_id)
        if not card:
            return None
        old_status = card.lifecycle_status
        if old_status == target:
            return card
        card.lifecycle_status = target
        if target == CardLifecycleStatus.ARCHIVED:
            card.archived_at = datetime.utcnow()
        card.version += 1
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.lifecycle_changed",
                {
                    "card_id": str(card.id),
                    "card_type": card.card_type.value,
                    "old_status": old_status.value,
                    "new_status": target.value,
                },
            )
        return card

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def count_cards_by_status(self, owner_id: uuid.UUID) -> dict[str, int]:
        """Return counts of cards grouped by lifecycle_status."""
        from sqlalchemy import func

        stmt = (
            select(Card.lifecycle_status, func.count(Card.id))
            .where(Card.owner_id == owner_id, Card.not_deleted_filter())
            .group_by(Card.lifecycle_status)
        )
        result = await self.db.execute(stmt)
        return {status.value: count for status, count in result.all()}

    async def get_plan_with_phases(self, plan_card_id: uuid.UUID) -> dict | None:
        """Get a plan card with its phase children via edges."""
        from app.models.card_protocol import CardEdge, EdgeType

        plan = await self.get_card(plan_card_id)
        if not plan or plan.card_type != CardType.PLAN:
            return None

        stmt = (
            select(Card)
            .join(CardEdge, CardEdge.to_card_id == Card.id)
            .where(
                CardEdge.from_card_id == plan_card_id,
                CardEdge.edge_type == EdgeType.CONTAINS,
                CardEdge.active.is_(True),
                Card.card_type == CardType.PHASE,
                Card.not_deleted_filter(),
            )
            .order_by(CardEdge.order_index)
        )
        result = await self.db.execute(stmt)
        phases = list(result.scalars().all())

        return {"plan": plan, "phases": phases}
