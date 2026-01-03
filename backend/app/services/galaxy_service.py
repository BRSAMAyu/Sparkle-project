"""知识星图核心服务 (Galaxy Service) - Facade Pattern
Refactored to delegate to specialized services:
- GraphStructureService: CRUD, Relations
- KnowledgeRetrievalService: Search, Embedding
- GalaxyStatsService: Spark, Stats, Prediction
"""
import asyncio
from uuid import UUID
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.galaxy import KnowledgeNode, NodeRelation
from app.schemas.galaxy import (
    GalaxyGraphResponse, SparkResult, SearchResultItem, 
    GalaxyUserStats, NodeWithStatus, NodeRelationInfo
)
from app.services.galaxy.structure_service import GraphStructureService
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.embedding_service import embedding_service
from app.core.cache import cached

class GalaxyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.structure = GraphStructureService(db)
        self.retrieval = KnowledgeRetrievalService(db)
        self.stats = GalaxyStatsService(db)

    # --- Delegated to GraphStructureService ---

    async def create_node(
        self,
        user_id: UUID,
        title: str,
        summary: str,
        subject_id: Optional[int] = None,
        tags: List[str] = [],
        parent_node_id: Optional[UUID] = None
    ) -> KnowledgeNode:
        """
        Create a new knowledge node.
        Async pipeline:
        1. Write basic info to DB (Fast)
        2. Spawn background task for Embedding & Deduplication (Slow)
        """
        # 1. Fast Write
        node = await self.structure.create_node(
            user_id, title, summary, subject_id, tags, parent_node_id
        )
        
        # 2. Async Background Processing (Fire & Forget)
        # Note: We pass the node ID to avoid detached instance issues
        asyncio.create_task(self._process_node_background(node.id, title, summary))
        
        return node

    async def create_edge(
        self,
        user_id: UUID,
        source_id: UUID,
        target_id: UUID,
        relation_type: str
    ) -> NodeRelation:
        return await self.structure.create_edge(user_id, source_id, target_id, relation_type)

    async def get_node_neighbors(self, node_id: UUID, limit: int = 5) -> List[KnowledgeNode]:
        """Get connected neighbor nodes (Graph RAG support)"""
        return await self.structure.get_node_neighbors(node_id, limit)

    async def update_node_positions(self, updates: List[dict]) -> int:
        """Batch update node positions"""
        return await self.structure.update_node_positions(updates)

    async def get_nodes_in_bounds(
        self, 
        min_x: float, 
        max_x: float, 
        min_y: float, 
        max_y: float
    ) -> List[KnowledgeNode]:
        """Get nodes within viewport"""
        return await self.structure.get_nodes_in_bounds(min_x, max_x, min_y, max_y)

    @cached(ttl=600, key_builder=lambda self, user_id, sector_code=None, include_locked=True, zoom_level=1.0: f"{user_id}:{sector_code}:{include_locked}:{zoom_level < 0.5}")
    async def get_galaxy_graph(
        self,
        user_id: UUID,
        sector_code: Optional[str] = None,
        include_locked: bool = True,
        zoom_level: float = 1.0
    ) -> GalaxyGraphResponse:
        # 1. Get Structure
        nodes_with_status, relations = await self.structure.get_graph_view(
            user_id, sector_code, include_locked, zoom_level
        )
        
        # 2. Get Stats (Parallelizable if needed, but fast enough)
        user_stats = await self.stats.calculate_user_stats(user_id)
        
        # 3. Assemble
        return GalaxyGraphResponse(
            nodes=[
                NodeWithStatus.from_models(node, status)
                for node, status in nodes_with_status
            ],
            relations=[
                NodeRelationInfo(
                    source_node_id=rel.source_node_id,
                    target_node_id=rel.target_node_id,
                    relation_type=rel.relation_type,
                    strength=rel.strength
                )
                for rel in relations
            ],
            user_stats=user_stats
        )

    # --- Delegated to KnowledgeRetrievalService ---

    async def keyword_search(
         self,
         user_id: UUID,
         query: str,
         subject_id: Optional[int] = None,
         limit: int = 20
    ) -> List[KnowledgeNode]:
        return await self.retrieval.keyword_search(user_id, query, subject_id, limit)

    async def hybrid_search(
        self,
        user_id: UUID,
        query: str,
        vector_query: Optional[str] = None,
        subject_id: Optional[int] = None,
        limit: int = 5,
        threshold: float = 0.3,
        use_reranker: bool = True
    ) -> List[SearchResultItem]:
        return await self.retrieval.hybrid_search(
            user_id, query, vector_query, subject_id, limit, threshold, use_reranker
        )

    async def semantic_search(
        self,
        user_id: UUID,
        query: str,
        subject_id: Optional[int] = None,
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[SearchResultItem]:
        # Reuse hybrid search logic or semantic_search_nodes but format as SearchResultItem
        # The original semantic_search in galaxy_service.py returned SearchResultItem.
        # KnowledgeRetrievalService has semantic_search_nodes returning KnowledgeNode.
        # We should map or use retrieval's hybrid search (which is better).
        # For backward compatibility, let's reimplement simple vector search here using retrieval service's primitive
        
        nodes = await self.retrieval.semantic_search_nodes(query, subject_id, limit, threshold)
        
        results = []
        for node in nodes:
            # We need user status to format properly
            status = await self.retrieval._get_user_status(user_id, node.id)
            results.append(self.retrieval._format_search_result(node, status, 0.0)) # Score missing
            
        return results

    async def semantic_search_nodes(
        self,
        query: str,
        subject_id: Optional[int] = None,
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[KnowledgeNode]:
        return await self.retrieval.semantic_search_nodes(query, subject_id, limit, threshold)

    async def auto_classify_task(
        self,
        task_title: str,
        task_description: Optional[str] = None
    ) -> Optional[UUID]:
        # Logic was in galaxy_service.py, moving here or to retrieval
        search_text = f"{task_title} {task_description or ''}"
        nodes = await self.retrieval.semantic_search_nodes(search_text, limit=1)
        if nodes:
            return nodes[0].id
        
        # Fallback keyword
        nodes_kw = await self.retrieval.keyword_search(UUID('00000000-0000-0000-0000-000000000000'), task_title.split()[0], limit=1)
        if nodes_kw:
            return nodes_kw[0].id
            
        return None

    # --- Delegated to GalaxyStatsService ---

    async def spark_node(
        self,
        user_id: UUID,
        node_id: UUID,
        study_minutes: int,
        task_id: Optional[UUID] = None,
        trigger_expansion: bool = True
    ) -> SparkResult:
        return await self.stats.spark_node(user_id, node_id, study_minutes, task_id, trigger_expansion)

    async def predict_next_node(self, user_id: UUID) -> Optional[NodeWithStatus]:
        return await self.stats.predict_next_node(user_id)

    async def get_heatmap_data(self, user_id: UUID) -> List[dict]:
        """Get forget curve heatmap data"""
        return await self.stats.get_heatmap_data(user_id)

    async def auto_link_nodes(self, node_id: UUID) -> int:
        """Run auto-link worker logic for a node"""
        # Note: In Facade we access ExpansionService via stats service or structure?
        # Actually ExpansionService is initialized in GalaxyService directly usually or via Stats
        # Looking at __init__, it's not there.
        # But StatsService has it.
        return await self.stats.expansion_service.auto_link_nodes(node_id)

    # --- Async Background Processing ---

    async def _process_node_background(self, node_id: UUID, title: str, summary: str):
        """
        Background Worker for Node Processing:
        1. Generate Embedding
        2. Deduplication Check (Notify if duplicate)
        """
        logger.info(f"Starting background processing for node {node_id}")
        
        # We need a new session for background task as the original request session might be closed
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            try:
                # 1. Generate Embedding
                text = f"{title}\n{summary}"
                embedding = await embedding_service.get_embedding(text)
                
                # Update Node
                node = await session.get(KnowledgeNode, node_id)
                if node:
                    node.embedding = embedding
                    session.add(node)
                    await session.commit()
                    logger.info(f"Generated embedding for node {node_id}")
                    
                    # 2. Check Deduplication (Post-creation check)
                    # Find similar nodes (excluding self)
                    retrieval = KnowledgeRetrievalService(session)
                    similar = await retrieval.semantic_search_nodes(title, limit=2, threshold=0.1)
                    
                    for sim in similar:
                        if sim.id != node_id:
                            logger.warning(f"Potential duplicate found for {node_id}: {sim.id} ({sim.name})")
                            # TODO: Create Notification for user to merge
                            # notification_service.create_system_notification(...)
                            break
                            
            except Exception as e:
                logger.error(f"Background processing failed for node {node_id}: {e}")