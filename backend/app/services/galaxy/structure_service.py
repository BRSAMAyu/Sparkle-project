from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus
from app.models.sector import SectorCode
from app.models.subject import Subject
from app.services.node_sector_service import build_sector_visuals, node_belongs_to_sector, parse_sector_code


class GraphNodeAccessDenied(PermissionError):
    """Raised when the caller does not have access to a KnowledgeNode."""


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GraphStructureService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _filter_accessible_node_ids(
        self,
        node_ids: list[UUID],
        user_id: UUID,
    ) -> set[UUID]:
        """Return the subset of ``node_ids`` the user is allowed to read/write.

        Access rule (R7-P0-1, R7-P0-2): a node is accessible iff
          (a) it is a seed/system node (``is_seed=True`` or ``source_type='seed'``), OR
          (b) the user has a ``UserNodeStatus`` row for it.
        """
        if not node_ids:
            return set()

        accessible: set[UUID] = set()
        seed_rows = await self.db.execute(
            select(KnowledgeNode.id).where(
                KnowledgeNode.id.in_(node_ids),
                or_(
                    KnowledgeNode.is_seed.is_(True),
                    KnowledgeNode.source_type == "seed",
                ),
            )
        )
        accessible.update(row[0] for row in seed_rows)

        user_rows = await self.db.execute(
            select(UserNodeStatus.node_id).where(
                UserNodeStatus.node_id.in_(node_ids),
                UserNodeStatus.user_id == user_id,
            )
        )
        accessible.update(row[0] for row in user_rows)
        return accessible

    async def create_node(
        self,
        user_id: UUID,
        title: str,
        summary: str,
        subject_id: int | None = None,
        tags: list[str] | None = None,
        parent_node_id: UUID | None = None,
    ) -> KnowledgeNode:
        """Create a new knowledge node (Structure)"""
        if tags is None:
            tags = []
        subject = await self.db.get(Subject, subject_id) if subject_id is not None else None
        parent = await self.db.get(KnowledgeNode, parent_node_id) if parent_node_id is not None else None
        fallback_sector = (
            parse_sector_code(getattr(subject, "sector_code", None))
            or parse_sector_code(getattr(parent, "dominant_sector_code", None))
            or SectorCode.VOID
        )
        visuals = build_sector_visuals(
            title,
            importance_level=1,
            sector_weights={fallback_sector.value: 100},
        )
        node = KnowledgeNode(
            name=title,
            description=summary,
            subject_id=subject_id,
            keywords=tags,
            parent_id=parent_node_id,
            is_seed=False,
            source_type="user_created",
            importance_level=1,
            sector_weights={fallback_sector.value: 100},
            dominant_sector_code=visuals.dominant_sector_code.value,
            sector_classification_status="completed",
            sector_classification_model="structure_service",
            sector_classified_at=_utcnow(),
            position_x=visuals.position_x,
            position_y=visuals.position_y,
        )
        self.db.add(node)
        await self.db.flush()  # Get ID

        # Initialize status
        status = UserNodeStatus(
            user_id=user_id,
            node_id=node.id,
            is_unlocked=True,
            mastery_score=0,
            bkt_mastery_prob=0.0,
            first_unlock_at=_utcnow(),
        )
        self.db.add(status)

        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def create_edge(self, user_id: UUID, source_id: UUID, target_id: UUID, relation_type: str) -> NodeRelation:
        """Create a relation between nodes.

        R7-P0-1: the calling user MUST have access (seed node or own UserNodeStatus)
        to BOTH endpoints; otherwise raises ``GraphNodeAccessDenied``. Prevents
        arbitrary cross-tenant edges in the shared knowledge graph.
        """
        accessible = await self._filter_accessible_node_ids([source_id, target_id], user_id)
        missing = {source_id, target_id} - accessible
        if missing:
            logger.warning(
                f"create_edge denied: user={user_id} lacks access to nodes={missing} "
                f"(source={source_id}, target={target_id})"
            )
            raise GraphNodeAccessDenied(f"User {user_id} cannot create edge involving inaccessible nodes")

        edge = NodeRelation(
            source_node_id=source_id, target_node_id=target_id, relation_type=relation_type, created_by="user"
        )
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge

    async def get_node_with_context(
        self,
        node_id: UUID,
        user_id: UUID | None = None,
    ) -> KnowledgeNode | None:
        """Get node with parent and subject loaded.

        R7-P0-2: when ``user_id`` is supplied, returns ``None`` if the user has
        no access to ``node_id`` (no UserNodeStatus and not a seed). When not
        supplied a warning is logged but the node is returned (back-compat).
        """
        stmt = (
            select(KnowledgeNode)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent),
                selectinload(KnowledgeNode.children),
            )
            .where(KnowledgeNode.id == node_id)
        )
        result = await self.db.execute(stmt)
        node = result.scalar_one_or_none()
        if node is None:
            return None

        if user_id is not None:
            accessible = await self._filter_accessible_node_ids([node_id], user_id)
            if node_id not in accessible:
                logger.info(f"get_node_with_context: user={user_id} denied access to node={node_id}")
                return None
        else:
            logger.warning("get_node_with_context called without user_id; access check skipped")

        return node

    async def get_node_neighbors(
        self,
        node_id: UUID,
        limit: int = 5,
        user_id: UUID | None = None,
    ) -> list[KnowledgeNode]:
        """Get connected neighbor nodes (undirected).

        R7-P0-2: when ``user_id`` is supplied, neighbors are filtered to those
        the user can access (seed or has UserNodeStatus). Also the starting
        ``node_id`` itself must be accessible — otherwise an empty list is
        returned. When ``user_id`` is None, a warning is logged.
        """
        if user_id is not None:
            accessible_start = await self._filter_accessible_node_ids([node_id], user_id)
            if node_id not in accessible_start:
                logger.info(f"get_node_neighbors: user={user_id} denied access to anchor node={node_id}")
                return []
        else:
            logger.warning("get_node_neighbors called without user_id; access check skipped")

        # Find edges where node is source or target
        stmt = (
            select(NodeRelation)
            .where(or_(NodeRelation.source_node_id == node_id, NodeRelation.target_node_id == node_id))
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

        if user_id is not None:
            accessible_neighbors = await self._filter_accessible_node_ids(neighbor_ids, user_id)
            neighbor_ids = [nid for nid in neighbor_ids if nid in accessible_neighbors]
            if not neighbor_ids:
                return []

        nodes_stmt = select(KnowledgeNode).where(KnowledgeNode.id.in_(neighbor_ids))
        nodes_result = await self.db.execute(nodes_stmt)
        return list(nodes_result.scalars().all())

    async def update_node_positions(self, updates: list[dict], user_id: str | None = None) -> int:
        """
        Batch update node positions.
        updates: list of {'id': UUID, 'x': float, 'y': float}
        user_id: Required — only nodes owned by this user can be moved.
        """
        from sqlalchemy import update

        if not updates:
            return 0

        if user_id is None:
            raise PermissionError("user_id is required for position updates")

        node_ids = [item["id"] for item in updates]
        from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument

        # KnowledgeNode 本身无 user_id：归属经 KnowledgeNodeDocument 判定
        ownership_stmt = (
            select(KnowledgeNode.id)
            .join(
                KnowledgeNodeDocument,
                KnowledgeNodeDocument.node_id == KnowledgeNode.id,
            )
            .where(
                KnowledgeNode.id.in_(node_ids),
                KnowledgeNodeDocument.user_id == user_id,
            )
        )
        owned = set((await self.db.execute(ownership_stmt)).scalars().all())
        unauthorized = set(node_ids) - owned
        if unauthorized:
            raise PermissionError(f"User does not own nodes: {unauthorized}")

        # Process in chunks if needed, but for now simple loop or bulk
        # Since updates are individual per ID, using mappings is best

        # Transform to list of dicts for update
        update_data = [{"id": item["id"], "position_x": item["x"], "position_y": item["y"]} for item in updates]

        if not update_data:
            return 0

        await self.db.execute(update(KnowledgeNode), update_data)
        await self.db.commit()
        return len(update_data)

    async def get_nodes_in_bounds(
        self, min_x: float, max_x: float, min_y: float, max_y: float, limit: int = 1000
    ) -> list[KnowledgeNode]:
        """Get nodes within a bounding box (Viewport Query)"""
        stmt = (
            select(KnowledgeNode)
            .where(
                and_(
                    KnowledgeNode.position_x >= min_x,
                    KnowledgeNode.position_x <= max_x,
                    KnowledgeNode.position_y >= min_y,
                    KnowledgeNode.position_y <= max_y,
                    or_(KnowledgeNode.status.is_(None), KnowledgeNode.status == "published"),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_graph_viewport(
        self,
        user_id: UUID,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        limit: int = 800,
    ):
        """Fetch a viewport-limited graph slice with user status and local relations."""
        query = (
            select(KnowledgeNode, UserNodeStatus)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent),
            )
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id,
                ),
            )
            .where(
                and_(
                    KnowledgeNode.position_x >= min_x,
                    KnowledgeNode.position_x <= max_x,
                    KnowledgeNode.position_y >= min_y,
                    KnowledgeNode.position_y <= max_y,
                    or_(KnowledgeNode.status.is_(None), KnowledgeNode.status == "published"),
                )
            )
            .order_by(KnowledgeNode.importance_level.desc(), KnowledgeNode.global_spark_count.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        nodes_with_status = result.all()

        node_ids = [node.id for node, _ in nodes_with_status]
        relations: list[NodeRelation] = []
        if node_ids:
            relations_query = select(NodeRelation).where(
                and_(
                    NodeRelation.source_node_id.in_(node_ids),
                    NodeRelation.target_node_id.in_(node_ids),
                )
            )
            relations_result = await self.db.execute(relations_query)
            relations = list(relations_result.scalars().all())

        return nodes_with_status, relations

    async def get_graph_view(
        self, user_id: UUID, sector_code: str | None = None, include_locked: bool = True, zoom_level: float = 1.0
    ) -> tuple[Sequence[tuple[KnowledgeNode, UserNodeStatus | None]], Sequence[NodeRelation]]:
        """Fetch graph structure for visualization"""
        # 1. Query nodes with status
        query = (
            select(KnowledgeNode, UserNodeStatus)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent),
            )
            .outerjoin(
                UserNodeStatus, and_(UserNodeStatus.node_id == KnowledgeNode.id, UserNodeStatus.user_id == user_id)
            )
            .outerjoin(Subject, KnowledgeNode.subject_id == Subject.id)
            .where(
                or_(
                    KnowledgeNode.status.is_(None),
                    KnowledgeNode.status == "published",
                    and_(
                        KnowledgeNode.status == "draft",
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.is_unlocked.is_(True),
                    ),
                )
            )
        )

        # LOD Filtering
        if zoom_level < 0.5:
            query = query.where(
                or_(KnowledgeNode.importance_level >= 3, KnowledgeNode.is_seed, UserNodeStatus.is_unlocked)
            )

        result = await self.db.execute(query)
        nodes_with_status: list[tuple[KnowledgeNode, UserNodeStatus | None]] = [
            (node, status) for node, status in result.all()
        ]

        if sector_code:
            nodes_with_status = [
                (node, status) for node, status in nodes_with_status if node_belongs_to_sector(node, sector_code)
            ]

        if not include_locked:
            nodes_with_status = [(node, status) for node, status in nodes_with_status if status and status.is_unlocked]

        # 2. Query Relations
        node_ids = [node.id for node, _ in nodes_with_status]
        relations: list[NodeRelation] = []
        if node_ids:
            relations_query = select(NodeRelation).where(
                and_(NodeRelation.source_node_id.in_(node_ids), NodeRelation.target_node_id.in_(node_ids))
            )
            relations_result = await self.db.execute(relations_query)
            relations = list(relations_result.scalars().all())

        # Note: stats are calculated in StatsService, here we return partial or delegate
        # Since we are splitting, this method returns the structural part.
        # However, GalaxyGraphResponse includes user_stats.
        # We will handle the composition in the Facade.

        return nodes_with_status, relations
