"""知识星图核心服务 (Galaxy Service) - Facade Pattern
Refactored to delegate to specialized services:
- GraphStructureService: CRUD, Relations
- KnowledgeRetrievalService: Search, Embedding
- GalaxyStatsService: Spark, Stats, Prediction
"""
import asyncio
import json
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger

from app.models.galaxy import KnowledgeNode, NodeRelation
from app.models.outbox import EventOutbox
from app.schemas.galaxy import (
    GalaxyGraphResponse, SparkResult, SearchResultItem, 
    GalaxyUserStats, NodeWithStatus, NodeRelationInfo
)
from app.services.galaxy.structure_service import GraphStructureService
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.embedding_service import embedding_service
from app.core.cache import cached
from app.core.event_bus import event_bus, KnowledgeNodeUpdated

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

        # 2. Async Background Processing (Managed)
        from app.core.task_manager import task_manager
        # from app.core.celery_app import schedule_long_task

        # 方案1: 使用 TaskManager (快速任务, < 10秒)
        await task_manager.spawn(
            self._process_node_background(node.id, title, summary),
            task_name="node_embedding",
            user_id=str(user_id)
        )

        # 方案2: 使用 Celery (长时任务, 需要持久化) - 可选
        # schedule_long_task(
        #     "generate_node_embedding",
        #     args=(str(node.id), title, summary, str(user_id)),
        #     queue="high_priority"
        # )

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


    async def update_node_mastery(self, user_id: UUID, node_id: UUID, new_mastery: int, reason: str, version: Optional[datetime] = None, request_id: Optional[str] = None, revision: Optional[int] = None):
        """
        Update node mastery with Outbox pattern and version checking to prevent race conditions
        """
        # 1. Get current state from user_node_status
        query_current = text("""
            SELECT mastery_score, updated_at, revision
            FROM user_node_status 
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await self.db.execute(query_current, {"user_id": user_id, "node_id": node_id})
        current = result.fetchone()
        
        current_revision = 0
        if not current:
            # If status doesn't exist, create one (initial unlock)
            old_mastery = 0
            # We skip version check for new entries or use a very old one
        else:
            old_mastery = current[0]
            current_updated_at = current[1]
            current_revision = current[2] or 0
            
            # 2. Conflict Resolution (Logical Clock Priority)
            if revision is not None:
                # Client provided a revision, ensure we are not overwriting a newer one (or equal, if not idempotent)
                # Ideally, client revision should be base_revision + 1. 
                # If client revision < current_revision, it's a stale update.
                if revision <= current_revision:
                     logger.warning(f"Ignoring stale update (Revision) for node {node_id}. Client {revision} <= Server {current_revision}")
                     return {"success": False, "reason": "stale_revision", "current_revision": current_revision}
            
            # Fallback to Physical Clock if revision not provided (Legacy)
            elif version and current_updated_at and version <= current_updated_at:
                logger.warning(f"Ignoring stale update (Time) for node {node_id}. Incoming version {version} <= current {current_updated_at}")
                return {"success": False, "reason": "stale_update", "current_revision": current_revision}

        # Calculate new revision
        new_revision = current_revision + 1
        if revision is not None and revision > current_revision:
             # Adopt client revision if it's logically ahead (or simply increment server's)
             # To maintain strict monotonicity, usually server authoritative revision = max(client, server) + 1 
             # But here we just want to increment.
             new_revision = current_revision + 1

        # 3. Transactional Update
        try:
            # A. Update Global Stats (Collaborative Sparking)
            # Increment global count if this is the first time the user unlocks it
            is_new_spark = (old_mastery == 0 and new_mastery > 0)
            if is_new_spark:
                global_update = text("""
                    UPDATE knowledge_nodes 
                    SET global_spark_count = global_spark_count + 1 
                    WHERE id = :node_id
                """)
                await self.db.execute(global_update, {"node_id": node_id})

            # B. Update Individual Data (UPSERT pattern)
            # Added revision column update
            upsert_query = text("""
                INSERT INTO user_node_status (user_id, node_id, mastery_score, updated_at, last_study_at, is_unlocked, revision)
                VALUES (:user_id, :node_id, :mastery, :updated_at, :updated_at, true, :revision)
                ON CONFLICT (user_id, node_id) DO UPDATE SET
                    mastery_score = EXCLUDED.mastery_score,
                    updated_at = EXCLUDED.updated_at,
                    last_study_at = EXCLUDED.updated_at,
                    is_unlocked = true,
                    revision = EXCLUDED.revision
                WHERE user_node_status.revision < EXCLUDED.revision OR (user_node_status.revision = EXCLUDED.revision AND user_node_status.updated_at < EXCLUDED.updated_at)
            """)
            
            update_time = version or datetime.utcnow()
            
            await self.db.execute(upsert_query, {
                "user_id": user_id, 
                "node_id": node_id, 
                "mastery": new_mastery,
                "updated_at": update_time,
                "revision": new_revision
            })
            
            # C. Audit Log
            audit_query = text("""
                INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision)
                VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, :revision)
            """)
            await self.db.execute(audit_query, {
                "node_id": node_id,
                "user_id": user_id,
                "old_mastery": int(old_mastery),
                "new_mastery": new_mastery,
                "reason": reason,
                "request_id": request_id,
                "revision": new_revision
            })
            
            # 4. Invalidate Semantic Cache (User specific)
            from app.services.semantic_cache_service import semantic_cache_service
            if semantic_cache_service:
                # We invalidate all cache for this user since we don't know which queries 
                # might be affected by this specific node's mastery change.
                # In a more advanced version, we could use tags or query-to-node mapping.
                # await semantic_cache_service.invalidate_user_cache(str(user_id))
                pass # Pattern for broad invalidation if needed, or rely on TTL.
                # Actually, mastery score might not change the retrieved nodes, just their status.
                # Since status is re-fetched in hybrid_search, we might not need to invalidate nodes cache!

            
            # 5. Add to Outbox
            outbox_event = EventOutbox(
                topic="galaxy.node.mastery_updated",
                payload={
                    "user_id": str(user_id),
                    "node_id": str(node_id),
                    "mastery_score": new_mastery,
                    "revision": new_revision,
                    "timestamp": datetime.utcnow().isoformat()
                },
                created_at=datetime.utcnow() # Explicitly set for partitioning
            )
            self.db.add(outbox_event)
            
            await self.db.flush()
            
            return {
                "success": True, 
                "old_mastery": int(old_mastery),
                "new_mastery": new_mastery,
                "current_revision": new_revision
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update node mastery: {e}")
            raise e

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
