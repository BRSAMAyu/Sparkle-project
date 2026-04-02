"""
CardEdgeService — Graph relationship management for canonical cards.

Phase 1 scope: CONTAINS, REFERENCES, DEPENDS_ON, EVIDENCE_FOR, ENABLES, BLOCKS edges.
CardEdges connect canonical cards only. TaskOccurrence provenance lives on the occurrence record.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardEdge,
    EdgeType,
    BindingMode,
)
from app.core.event_bus import EventBus


class CardEdgeService:
    """Service for managing card graph relationships."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # Create edge
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
        edge = CardEdge(
            from_card_id=from_card_id,
            to_card_id=to_card_id,
            edge_type=edge_type,
            binding_mode=binding_mode,
            order_index=order_index,
            weight=weight,
            temporal_window=temporal_window,
            metadata_=metadata or {},
            active=True,
        )
        self.db.add(edge)
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card_edge.created",
                {
                    "edge_id": str(edge.id),
                    "from_card_id": str(from_card_id),
                    "to_card_id": str(to_card_id),
                    "edge_type": edge_type.value,
                },
            )
        return edge

    # ------------------------------------------------------------------
    # Read edges
    # ------------------------------------------------------------------

    async def get_edge(self, edge_id: uuid.UUID) -> CardEdge | None:
        stmt = select(CardEdge).where(CardEdge.id == edge_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_children(
        self,
        card_id: uuid.UUID,
        edge_type: EdgeType | None = None,
        active_only: bool = True,
    ) -> list[tuple[CardEdge, Card]]:
        """Get child cards with their edges (outgoing from card_id)."""
        stmt = (
            select(CardEdge, Card)
            .join(Card, Card.id == CardEdge.to_card_id)
            .where(CardEdge.from_card_id == card_id)
        )
        if edge_type:
            stmt = stmt.where(CardEdge.edge_type == edge_type)
        if active_only:
            stmt = stmt.where(CardEdge.active.is_(True))
            stmt = stmt.where(Card.not_deleted_filter())
        stmt = stmt.order_by(CardEdge.order_index)
        result = await self.db.execute(stmt)
        return [(edge, card) for edge, card in result.all()]

    async def get_parents(
        self,
        card_id: uuid.UUID,
        edge_type: EdgeType | None = None,
        active_only: bool = True,
    ) -> list[tuple[CardEdge, Card]]:
        """Get parent cards with their edges (incoming to card_id)."""
        stmt = (
            select(CardEdge, Card)
            .join(Card, Card.id == CardEdge.from_card_id)
            .where(CardEdge.to_card_id == card_id)
        )
        if edge_type:
            stmt = stmt.where(CardEdge.edge_type == edge_type)
        if active_only:
            stmt = stmt.where(CardEdge.active.is_(True))
            stmt = stmt.where(Card.not_deleted_filter())
        result = await self.db.execute(stmt)
        return [(edge, card) for edge, card in result.all()]

    async def get_evidence_for(self, card_id: uuid.UUID) -> list[tuple[CardEdge, Card]]:
        """Get all evidence cards pointing TO this card."""
        return await self.get_parents(card_id, edge_type=EdgeType.EVIDENCE_FOR)

    async def get_dependencies(self, card_id: uuid.UUID) -> list[tuple[CardEdge, Card]]:
        """Get all cards this card DEPENDS_ON."""
        return await self.get_children(card_id, edge_type=EdgeType.DEPENDS_ON)

    async def get_blockers(self, card_id: uuid.UUID) -> list[tuple[CardEdge, Card]]:
        """Get all cards that BLOCK this card."""
        return await self.get_parents(card_id, edge_type=EdgeType.BLOCKS)

    # ------------------------------------------------------------------
    # Update / deactivate edges
    # ------------------------------------------------------------------

    async def deactivate_edge(self, edge_id: uuid.UUID) -> CardEdge | None:
        edge = await self.get_edge(edge_id)
        if not edge:
            return None
        edge.active = False
        edge.removed_at = datetime.utcnow()
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card_edge.deactivated",
                {
                    "edge_id": str(edge.id),
                    "from_card_id": str(edge.from_card_id),
                    "to_card_id": str(edge.to_card_id),
                    "edge_type": edge.edge_type.value,
                },
            )
        return edge

    async def replace_children(
        self,
        parent_card_id: uuid.UUID,
        edge_type: EdgeType,
        new_child_ids: list[uuid.UUID],
        binding_mode: BindingMode = BindingMode.OWNED,
    ) -> list[CardEdge]:
        """Deactivate all existing children of a given type, then create new edges.

        Used when replanning: replace the current phase's task set.
        """
        # Deactivate existing
        stmt = select(CardEdge).where(
            CardEdge.from_card_id == parent_card_id,
            CardEdge.edge_type == edge_type,
            CardEdge.active.is_(True),
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().all()
        now = datetime.utcnow()
        for edge in existing:
            edge.active = False
            edge.removed_at = now
        await self.db.flush()

        # Create new
        new_edges = []
        for idx, child_id in enumerate(new_child_ids):
            edge = await self.create_edge(
                from_card_id=parent_card_id,
                to_card_id=child_id,
                edge_type=edge_type,
                binding_mode=binding_mode,
                order_index=idx,
            )
            new_edges.append(edge)

        return new_edges

    # ------------------------------------------------------------------
    # Evidence edges (for the growth loop)
    # ------------------------------------------------------------------

    async def add_evidence(
        self,
        *,
        evidence_card_id: uuid.UUID,
        target_card_id: uuid.UUID,
        metadata: dict | None = None,
        weight: float | None = None,
    ) -> CardEdge:
        """Create an EVIDENCE_FOR edge from an evidence card to a target.

        This is the core of the growth loop's evidence layer.
        """
        return await self.create_edge(
            from_card_id=evidence_card_id,
            to_card_id=target_card_id,
            edge_type=EdgeType.EVIDENCE_FOR,
            binding_mode=BindingMode.REFERENCE,
            metadata=metadata,
            weight=weight,
        )

    async def get_evidence_chain(self, card_id: uuid.UUID) -> dict:
        """Get the full evidence chain for a card: evidence pointing to it and evidence it points to."""
        incoming = await self.get_evidence_for(card_id)
        outgoing_stmt = (
            select(CardEdge, Card)
            .join(Card, Card.id == CardEdge.to_card_id)
            .where(
                CardEdge.from_card_id == card_id,
                CardEdge.edge_type == EdgeType.EVIDENCE_FOR,
                CardEdge.active.is_(True),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(outgoing_stmt)
        outgoing = [(edge, card) for edge, card in result.all()]

        return {
            "card_id": card_id,
            "evidence_for_this": [(str(e.id), str(c.id), e.metadata_) for e, c in incoming],
            "this_is_evidence_for": [(str(e.id), str(c.id), e.metadata_) for e, c in outgoing],
        }
