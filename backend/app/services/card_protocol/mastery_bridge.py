"""
Card Protocol Writeback Bridge — Error Analysis → Knowledge Mastery.

This fixes breakpoint 2 from the product consensus:
  "error analysis does not sufficiently write back to mastery"

Currently: ErrorCreated event → mastery penalty (-10%) → done.
Missing: No EVIDENCE_FOR edge connecting the error to the knowledge gap.

This bridge:
  1. Creates a KNOWLEDGE card for the error's root cause (if not existing)
  2. Creates an EVIDENCE_FOR edge only if a canonical error card exists
  3. Otherwise writes structured evidence metadata onto the knowledge card

The existing mastery penalty flow (via GalaxyService.handle_error_created)
continues unchanged. This bridge adds the card graph layer on top.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardType,
    CardLifecycleStatus,
    CardCreatedBy,
    CardSourceType,
    CardVisibility,
    CardEdge,
    EdgeType,
)
from app.services.card_service import CardService
from app.services.card_edge_service import CardEdgeService
from app.core.event_bus import EventBus


class ErrorMasteryBridge:
    """Bridges error analysis into the card protocol's evidence layer.

    Usage:
        # In galaxy_event_consumer.py, after handle_error_created:
        bridge = ErrorMasteryBridge(db, event_bus)
        await bridge.on_error_created(user_id, error_id, linked_node_ids, analysis)
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)

    async def on_error_created(
        self,
        *,
        user_id: uuid.UUID,
        error_id: uuid.UUID,
        linked_node_ids: list[uuid.UUID],
        analysis: dict | None = None,
        subject: str | None = None,
        chapter: str | None = None,
        error_type: str | None = None,
        root_cause: str | None = None,
    ) -> dict:
        """Create card protocol evidence for an error event.

        Returns a summary of what was created.
        """
        summary = {"knowledge_cards": 0, "evidence_edges": 0, "metadata_writebacks": 0, "errors": []}

        if not linked_node_ids:
            return summary

        error_card = await self._find_error_card(user_id=user_id, error_id=error_id)

        # 1. For each linked knowledge node, ensure a KNOWLEDGE card exists
        #    and write evidence in a taxonomy-safe way.
        for node_id in linked_node_ids:
            try:
                knowledge_card, created = await self._ensure_knowledge_card(user_id, node_id)
                if not knowledge_card:
                    continue
                if created:
                    summary["knowledge_cards"] += 1

                evidence_payload = {
                    "source_type": "error_record",
                    "source_id": str(error_id),
                    "error_type": error_type,
                    "root_cause": root_cause,
                    "subject": subject,
                    "chapter": chapter,
                    "diagnosis": analysis or {},
                    "recorded_at": datetime.utcnow().isoformat(),
                }

                if error_card:
                    existing_edge = await self._find_evidence_edge(
                        evidence_card_id=error_card.id,
                        knowledge_card_id=knowledge_card.id,
                        error_id=error_id,
                    )
                    if not existing_edge:
                        await self.edge_service.add_evidence(
                            evidence_card_id=error_card.id,
                            target_card_id=knowledge_card.id,
                            metadata=evidence_payload,
                            weight=-0.1,
                        )
                        summary["evidence_edges"] += 1

                await self._record_knowledge_evidence(knowledge_card, evidence_payload)
                summary["metadata_writebacks"] += 1

            except Exception as exc:
                err_msg = f"Failed to create evidence for node {node_id}: {exc}"
                logger.warning(err_msg)
                summary["errors"].append(err_msg)

        logger.info(
            "ErrorMasteryBridge: processed error {} → {} knowledge cards, {} evidence edges",
            error_id,
            summary["knowledge_cards"],
            summary["evidence_edges"],
        )
        return summary

    async def _ensure_knowledge_card(
        self, user_id: uuid.UUID, knowledge_node_id: uuid.UUID
    ) -> tuple[Card | None, bool]:
        """Find or create a KNOWLEDGE card for a galaxy knowledge node."""
        # Look for existing
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
            return existing, False

        # Create new
        card = await self.card_service.create_card(
            card_type=CardType.KNOWLEDGE,
            owner_id=user_id,
            holder_id=user_id,
            metadata={
                "knowledge_node_id": str(knowledge_node_id),
                "mastery_state": "learning",
                "evidence_count": 0,
                "error_count": 0,
            },
            tags=["knowledge", "galaxy"],
            source_type=CardSourceType.GENERATED,
            created_by=CardCreatedBy.SYSTEM,
            visibility=CardVisibility.PRIVATE,
            lifecycle_status=CardLifecycleStatus.ACTIVE,
        )
        return card, True

    async def _find_error_card(self, *, user_id: uuid.UUID, error_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.owner_id == user_id,
                Card.metadata_["error_id"].as_string() == str(error_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_evidence_edge(
        self,
        *,
        evidence_card_id: uuid.UUID,
        knowledge_card_id: uuid.UUID,
        error_id: uuid.UUID,
    ) -> CardEdge | None:
        """Find an existing evidence edge for this error on this card."""
        stmt = (
            select(CardEdge)
            .where(
                CardEdge.from_card_id == evidence_card_id,
                CardEdge.to_card_id == knowledge_card_id,
                CardEdge.edge_type == EdgeType.EVIDENCE_FOR,
                CardEdge.active.is_(True),
                CardEdge.metadata_["source_id"].as_string() == str(error_id),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _record_knowledge_evidence(self, knowledge_card: Card, evidence_payload: dict) -> None:
        existing_meta = dict(knowledge_card.metadata_ or {})
        evidence_log = list(existing_meta.get("error_evidence_log") or [])
        evidence_log.append(evidence_payload)
        existing_meta["error_evidence_log"] = evidence_log[-20:]
        existing_meta["last_error_evidence"] = evidence_payload
        existing_meta["error_count"] = int(existing_meta.get("error_count") or 0) + 1
        existing_meta["evidence_count"] = int(existing_meta.get("evidence_count") or 0) + 1
        existing_meta["mastery_state"] = "at_risk"

        await self.card_service.update_card(
            knowledge_card.id,
            metadata=existing_meta,
            updated_by=CardCreatedBy.SYSTEM,
        )
