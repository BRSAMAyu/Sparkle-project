"""
CardService — CRUD and lifecycle management for canonical cards.

Phase 1 scope: PLAN, PHASE, TASK, KNOWLEDGE card types.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardCreatedBy,
    CardLifecycleStatus,
    CardType,
    CardVisibility,
    CardSourceType,
)
from app.core.event_bus import EventBus


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

        if metadata is not None:
            # Merge metadata rather than replace
            existing = card.metadata_ or {}
            existing.update(metadata)
            card.metadata_ = existing
        if tags is not None:
            card.tags = tags
        for key, value in kwargs.items():
            if hasattr(card, key) and key not in ("id", "created_at"):
                setattr(card, key, value)

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
                },
            )
        return card

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
        card = await self.get_card(card_id)
        if not card:
            return None
        card.lifecycle_status = CardLifecycleStatus.ARCHIVED
        card.archived_at = datetime.utcnow()
        card.version += 1
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.archived",
                {"card_id": str(card.id), "card_type": card.card_type.value},
            )
        return card

    async def cancel(self, card_id: uuid.UUID) -> Card | None:
        return await self._transition(card_id, CardLifecycleStatus.CANCELLED)

    async def _transition(self, card_id: uuid.UUID, target: CardLifecycleStatus) -> Card | None:
        card = await self.get_card(card_id)
        if not card:
            return None
        card.lifecycle_status = target
        card.version += 1
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.lifecycle_changed",
                {
                    "card_id": str(card.id),
                    "card_type": card.card_type.value,
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
