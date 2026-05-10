"""Aggregate anonymous community error patterns and annotate knowledge nodes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import _utcnow
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode


class CommunityErrorAggregationService:
    """Extracts anonymous common error patterns per knowledge node and
    writes aggregated community_signal data."""

    MIN_USERS_FOR_AGGREGATION = 3
    MIN_ERRORS_FOR_PATTERN = 2
    MAX_PATTERNS_PER_NODE = 5
    SIGNAL_TTL_DAYS = 30

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def aggregate_and_annotate_node(self, node_id: UUID) -> dict | None:
        rows = await self.db.execute(
            select(
                ErrorRecord.knowledge_node_id,
                ErrorRecord.error_type,
                ErrorRecord.error_category,
                func.count(ErrorRecord.id).label("error_count"),
                func.count(func.distinct(ErrorRecord.user_id)).label("user_count"),
            )
            .where(
                ErrorRecord.knowledge_node_id == node_id,
                ErrorRecord.created_at >= _utcnow() - timedelta(days=self.SIGNAL_TTL_DAYS),
                ErrorRecord.deleted_at.is_(None),
            )
            .group_by(
                ErrorRecord.knowledge_node_id,
                ErrorRecord.error_type,
                ErrorRecord.error_category,
            )
            .order_by(desc("error_count"))
            .limit(self.MAX_PATTERNS_PER_NODE)
        )

        patterns = []
        for row in rows:
            if row.user_count < self.MIN_USERS_FOR_AGGREGATION:
                continue
            patterns.append({
                "error_type": row.error_type,
                "error_category": row.error_category,
                "count": row.error_count,
                "user_count": row.user_count,
            })

        if not patterns:
            return None

        signal = {
            "common_mistake_patterns": patterns,
            "aggregated_at": _utcnow().isoformat(),
            "privacy_level": "aggregate_only",
        }

        node = await self.db.get(KnowledgeNode, node_id)
        if node is None:
            return None

        node.community_signal = signal
        await self.db.flush()
        return signal

    async def aggregate_for_nodes_with_recent_errors(self) -> int:
        recent_cutoff = _utcnow() - timedelta(days=7)
        node_ids = await self.db.execute(
            select(func.distinct(ErrorRecord.knowledge_node_id))
            .where(
                ErrorRecord.created_at >= recent_cutoff,
                ErrorRecord.knowledge_node_id.isnot(None),
                ErrorRecord.deleted_at.is_(None),
            )
        )
        updated = 0
        for (node_id,) in node_ids:
            try:
                result = await self.aggregate_and_annotate_node(node_id)
                if result:
                    updated += 1
            except Exception as exc:
                logger.debug(f"Failed to aggregate community errors for node {node_id}: {exc}")
        return updated
