from uuid import UUID
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus, NodeRelation
from app.models.subject import Subject
from app.schemas.galaxy import NodeWithStatus, GalaxyGraphResponse, NodeRelationInfo

class GraphStructureService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_node(
        self,
        user_id: UUID,
        title: str,
        summary: str,
        subject_id: Optional[int] = None,
        tags: List[str] = [],
        parent_node_id: Optional[UUID] = None
    ) -> KnowledgeNode:
        """Create a new knowledge node (Structure)"""
        node = KnowledgeNode(
            name=title,
            description=summary,
            subject_id=subject_id,
            keywords=tags,
            parent_id=parent_node_id,
            is_seed=False,
            source_type='user_created',
            importance_level=1
        )
        self.db.add(node)
        await self.db.flush() # Get ID

        # Initialize status
        status = UserNodeStatus(
            user_id=user_id,
            node_id=node.id,
            is_unlocked=True,
            mastery_score=0,
            first_unlock_at=datetime.utcnow()
        )
        self.db.add(status)
        
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def create_edge(
        self,
        user_id: UUID,
        source_id: UUID,
        target_id: UUID,
        relation_type: str
    ) -> NodeRelation:
        """Create a relation between nodes"""
        edge = NodeRelation(
            source_node_id=source_id,
            target_node_id=target_id,
            relation_type=relation_type,
            created_by='user'
        )
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge

    async def get_node_with_context(self, node_id: UUID) -> Optional[KnowledgeNode]:
        """Get node with parent and subject loaded"""
        stmt = (
            select(KnowledgeNode)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent),
                selectinload(KnowledgeNode.children)
            )
            .where(KnowledgeNode.id == node_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_node_neighbors(self, node_id: UUID, limit: int = 5) -> List[KnowledgeNode]:
        """Get connected neighbor nodes (undirected)"""
        # Find edges where node is source or target
        stmt = (
            select(NodeRelation)
            .where(
                or_(
                    NodeRelation.source_node_id == node_id,
                    NodeRelation.target_node_id == node_id
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        relations = result.scalars().all()
        
        neighbor_ids = []
        for rel in relations:
            if rel.source_node_id == node_id:
                neighbor_ids.append(rel.target_node_id)
            else:
                neighbor_ids.append(rel.source_node_id)
        
        if not neighbor_ids:
            return []
            
        nodes_stmt = select(KnowledgeNode).where(KnowledgeNode.id.in_(neighbor_ids))
        nodes_result = await self.db.execute(nodes_stmt)
        return list(nodes_result.scalars().all())

    async def update_node_positions(self, updates: List[dict]) -> int:
        """
        Batch update node positions.
        updates: list of {'id': UUID, 'x': float, 'y': float}
        """
        # SQLAlchemy 2.0 bulk update
        from sqlalchemy import update
        
        count = 0
        # Process in chunks if needed, but for now simple loop or bulk
        # Since updates are individual per ID, using mappings is best
        
        # Transform to list of dicts for update
        update_data = [
            {'id': item['id'], 'position_x': item['x'], 'position_y': item['y']}
            for item in updates
        ]
        
        if not update_data:
            return 0
            
        await self.db.execute(
            update(KnowledgeNode),
            update_data
        )
        await self.db.commit()
        return len(update_data)

    async def get_nodes_in_bounds(
        self, 
        min_x: float, 
        max_x: float, 
        min_y: float, 
        max_y: float,
        limit: int = 1000
    ) -> List[KnowledgeNode]:
        """Get nodes within a bounding box (Viewport Query)"""
        stmt = (
            select(KnowledgeNode)
            .where(
                and_(
                    KnowledgeNode.position_x >= min_x,
                    KnowledgeNode.position_x <= max_x,
                    KnowledgeNode.position_y >= min_y,
                    KnowledgeNode.position_y <= max_y
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_graph_view(
        self,
        user_id: UUID,
        sector_code: Optional[str] = None,
        include_locked: bool = True,
        zoom_level: float = 1.0
    ) -> GalaxyGraphResponse:
        """Fetch graph structure for visualization"""
        # 1. Query nodes with status
        query = (
            select(KnowledgeNode, UserNodeStatus)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id
                )
            )
            .outerjoin(Subject, KnowledgeNode.subject_id == Subject.id)
        )

        if sector_code:
            query = query.where(Subject.sector_code == sector_code)
        
        # LOD Filtering
        if zoom_level < 0.5:
            query = query.where(
                or_(
                    KnowledgeNode.importance_level >= 3,
                    KnowledgeNode.is_seed == True,
                    UserNodeStatus.is_unlocked == True 
                )
            )

        result = await self.db.execute(query)
        nodes_with_status = result.all()

        if not include_locked:
            nodes_with_status = [
                (node, status) for node, status in nodes_with_status
                if status and status.is_unlocked
            ]

        # 2. Query Relations
        node_ids = [node.id for node, _ in nodes_with_status]
        relations = []
        if node_ids:
            relations_query = select(NodeRelation).where(
                and_(
                    NodeRelation.source_node_id.in_(node_ids),
                    NodeRelation.target_node_id.in_(node_ids)
                )
            )
            relations_result = await self.db.execute(relations_query)
            relations = relations_result.scalars().all()

        # Note: stats are calculated in StatsService, here we return partial or delegate
        # Since we are splitting, this method returns the structural part.
        # However, GalaxyGraphResponse includes user_stats. 
        # We will handle the composition in the Facade.
        
        return nodes_with_status, relations
