from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus


class GraphStructureEvolutionService:
    """Helpers for graph-strength and lightweight node-signal updates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def adjust_neighbor_relation_strengths(self, node_id: UUID, delta: float, limit: int = 24) -> int:
        result = await self.db.execute(
            select(NodeRelation)
            .where(or_(NodeRelation.source_node_id == node_id, NodeRelation.target_node_id == node_id))
            .limit(limit)
        )
        relations = list(result.scalars().all())
        for relation in relations:
            relation.strength = max(0.05, min(1.0, float(relation.strength or 0.5) + delta))
            self.db.add(relation)
        if relations:
            await self.db.commit()
        return len(relations)

    async def tag_node_signal(self, node_id: UUID, signal_tag: str, *, active: bool) -> bool:
        node = await self.db.get(KnowledgeNode, node_id)
        if not node:
            return False
        keywords = list(node.keywords or [])
        if active:
            if signal_tag not in keywords:
                keywords.append(signal_tag)
        else:
            keywords = [keyword for keyword in keywords if keyword != signal_tag]
        node.keywords = keywords
        self.db.add(node)
        await self.db.commit()
        return True

    async def upsert_relation(
        self,
        *,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
        strength_delta: float = 0.0,
        default_strength: float = 0.55,
        created_by: str = "graph_evolution",
    ) -> NodeRelation:
        result = await self.db.execute(
            select(NodeRelation).where(
                and_(
                    NodeRelation.source_node_id == source_id,
                    NodeRelation.target_node_id == target_id,
                    NodeRelation.relation_type == relation_type,
                )
            )
        )
        relation = result.scalar_one_or_none()
        if relation is None:
            relation = NodeRelation(
                source_node_id=source_id,
                target_node_id=target_id,
                relation_type=relation_type,
                strength=max(0.05, min(1.0, default_strength + strength_delta)),
                created_by=created_by,
            )
            self.db.add(relation)
        else:
            relation.strength = max(0.05, min(1.0, float(relation.strength or default_strength) + strength_delta))
            self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation

    async def record_engagement(self, *, user_id: UUID, node_id: UUID, minutes: int = 0) -> None:
        status = await self.db.get(UserNodeStatus, (user_id, node_id))
        if not status:
            status = UserNodeStatus(user_id=user_id, node_id=node_id, is_unlocked=True)
            self.db.add(status)
        status.total_minutes = int(status.total_minutes or 0) + max(0, minutes)
        status.total_study_minutes = int(status.total_study_minutes or 0) + max(0, minutes)
        self.db.add(status)
        await self.db.commit()
