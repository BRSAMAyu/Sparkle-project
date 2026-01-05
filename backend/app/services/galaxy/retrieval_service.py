import asyncio
from dataclasses import dataclass
from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from redis.commands.search.query import Query

from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service
from app.core.redis_search_client import redis_search_client
from app.schemas.galaxy import SearchResultItem, NodeBase, UserStatusInfo, SectorCode
try:
    from app.services.semantic_cache_service import semantic_cache_service
except ImportError:
    # Handle circular import or missing dependency during tests
    semantic_cache_service = None

class KnowledgeRetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
        """
        RAG v2.0 Hybrid Search with Cache Stampede Protection.
        """
        if not semantic_cache_service:
            return await self._execute_hybrid_search(user_id, query, vector_query, subject_id, limit, threshold, use_reranker)

        # Use get_with_lock to prevent redundant heavy retrieval tasks
        return await semantic_cache_service.get_with_lock(
            query=query,
            factory_func=self._execute_hybrid_search,
            user_id=str(user_id), # Optional: could be global if knowledge is shared
            # factory_func arguments
            user_id_uuid=user_id,
            query_str=query,
            vector_query=vector_query,
            subject_id=subject_id,
            limit=limit,
            threshold=threshold,
            use_reranker=use_reranker
        )

    async def _execute_hybrid_search(
        self,
        user_id_uuid: UUID,
        query_str: str,
        vector_query: Optional[str] = None,
        subject_id: Optional[int] = None,
        limit: int = 5,
        threshold: float = 0.3,
        use_reranker: bool = True
    ) -> List[SearchResultItem]:
        """
        Internal implementation of hybrid search.
        """
        # 2. Prepare Queries
        actual_vector_text = vector_query if vector_query else query_str
        query_embedding = await embedding_service.get_embedding(actual_vector_text)
        
        # 3. Parallel Retrieval
        vector_limit = limit * 10
        keyword_limit = limit * 10
        
        cleaned_query = " ".join([w for w in query_str.split() if len(w) > 1]) or "*"
            
        bm25_q = (
            Query(cleaned_query)
            .paging(0, keyword_limit)
            .return_fields("id", "parent_id", "content", "parent_name", "importance")
            .dialect(2)
        )

        vector_task = redis_search_client.hybrid_search(
            text_query="*", 
            vector=query_embedding,
            top_k=vector_limit
        )
        keyword_task = redis_search_client.search(bm25_q)
        
        vector_res, keyword_res = await asyncio.gather(vector_task, keyword_task)
        
        vec_docs = vector_res.docs if vector_res else []
        kw_docs = keyword_res.docs if keyword_res else []
        
        # 4. RRF Fusion
        fused_results = rerank_service.reciprocal_rank_fusion([vec_docs, kw_docs])
        candidates = [item for item, score in fused_results]
        
        # 5. Reranking
        if use_reranker and candidates:
            final_chunks = await rerank_service.rerank(query_str, candidates, top_k=limit)
        else:
            final_chunks = candidates[:limit]
            
        # 6. Fetch Nodes from DB
        parent_ids = list(set([chunk.parent_id for chunk in final_chunks]))
        if not parent_ids:
            return []
            
        stmt = (
            select(KnowledgeNode)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(KnowledgeNode.id.in_(parent_ids))
        )
        result = await self.db.execute(stmt)
        nodes_list = result.scalars().all()
        nodes_map = {str(node.id): node for node in nodes_list}
        
        # 7. Assemble Result
        search_results = []
        seen_parents = set()
        
        for chunk in final_chunks:
            pid = chunk.parent_id
            if pid not in nodes_map or pid in seen_parents:
                continue
            
            seen_parents.add(pid)
            node = nodes_map[pid]
            
            user_status = await self._get_user_status(user_id_uuid, node.id)
            search_results.append(self._format_search_result(node, user_status, 1.0))
            
        return search_results

    async def document_vector_search(
        self,
        user_id: UUID,
        query: str,
        file_ids: List[UUID],
        vector_query: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.3
    ) -> List["DocumentChunkResult"]:
        """
        Vector search over document chunks with forced file scope.
        """
        if not query or not file_ids:
            return []

        actual_vector_text = vector_query if vector_query else query
        query_embedding = await embedding_service.get_embedding(actual_vector_text)

        stmt = (
            select(
                DocumentChunk,
                StoredFile.file_name,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )
            .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
            .where(DocumentChunk.user_id == user_id)
            .where(DocumentChunk.file_id.in_(file_ids))
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(limit * 5)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        results: List[DocumentChunkResult] = []
        for chunk, file_name, distance in rows:
            if distance is None:
                continue
            if distance <= threshold:
                score = max(0.0, 1.0 - float(distance))
                results.append(DocumentChunkResult(chunk=chunk, file_name=file_name, score=score))

        return results[:limit]

    async def semantic_search_nodes(
        self,
        query: str,
        subject_id: Optional[int] = None,
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[KnowledgeNode]:
        """Internal semantic search that returns KnowledgeNode models"""
        query_embedding = await embedding_service.get_embedding(query)
        
        search_query = (
            select(
                KnowledgeNode,
                KnowledgeNode.embedding.cosine_distance(query_embedding).label('distance')
            )
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(KnowledgeNode.embedding.isnot(None))
        )
        
        if subject_id:
            search_query = search_query.where(KnowledgeNode.subject_id == subject_id)
            
        search_query = (
            search_query
            .order_by('distance')
            .limit(limit)
        )

        result = await self.db.execute(search_query)
        matches = result.all()
        
        return [node for node, distance in matches if distance <= threshold]


@dataclass
class DocumentChunkResult:
    chunk: DocumentChunk
    file_name: str
    score: float

    async def keyword_search(
         self,
         user_id: UUID,
         query: str,
         subject_id: Optional[int] = None,
         limit: int = 20
    ) -> List[KnowledgeNode]:
        """Keyword search for nodes (Sparse Retrieval)"""
        from sqlalchemy import or_, func, text
        
        # Optimized JSONB search using @> operator for exact tags match 
        # and jsonb_path_exists for partial match inside array if needed (requires PG 12+)
        # Here we use a hybrid approach:
        # 1. ILIKE for Name/Description
        # 2. @> for exact keyword match (using GIN index)
        # 3. Fallback to jsonb_path_exists for partial keyword match if simple containment fails
        
        # Note: 'keywords' is a JSONB array of strings. 
        # To search for "rust" in ["rust", "python"], we can use: keywords @> '["rust"]'
        
        stmt = (
            select(KnowledgeNode)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(
                or_(
                    KnowledgeNode.name.ilike(f"%{query}%"),
                    KnowledgeNode.description.ilike(f"%{query}%"),
                    # JSONB Containment (Fast GIN Index) - Exact match for a tag
                    KnowledgeNode.keywords.contains([query]),
                    # JSONB Path for partial match (Slower but accurate)
                    # Checks if any element in the array matches the regex pattern
                    func.jsonb_path_exists(
                        KnowledgeNode.keywords, 
                        f'$[*] ? (@ like_regex "{query}" flag "i")'
                    )
                )
            )
        )
        
        if subject_id:
             stmt = stmt.where(KnowledgeNode.subject_id == subject_id)
        
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # --- Helpers ---
    async def _get_user_status(self, user_id: UUID, node_id: UUID) -> Optional[UserNodeStatus]:
        stmt = select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id == node_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _format_search_result(self, node: KnowledgeNode, status: Optional[UserNodeStatus], score: float) -> SearchResultItem:
        sector_code_str = node.subject.sector_code if node.subject else 'VOID'
        try:
            sector_enum = SectorCode(sector_code_str)
        except ValueError:
            sector_enum = SectorCode.VOID

        node_base = NodeBase(
            id=node.id,
            name=node.name,
            name_en=node.name_en,
            description=node.description,
            importance_level=node.importance_level,
            sector_code=sector_enum,
            is_seed=node.is_seed,
            parent_name=node.parent.name if node.parent else None
        )

        user_status_info = None
        if status:
            # Note: We duplicate logic from StatsService for formatting to avoid circular deps
            # Ideally this formatting logic belongs to a Schema Mapper
            brightness = 0.3 + (status.mastery_score / 100.0) * 0.7
            if not status.is_unlocked: brightness = 0.2
            
            from app.schemas.galaxy import NodeStatus
            visual_status = NodeStatus.UNLIT
            if status.is_unlocked:
                if status.mastery_score >= 80: visual_status = NodeStatus.BRILLIANT
                elif status.mastery_score > 0: visual_status = NodeStatus.GLIMMER
            else:
                visual_status = NodeStatus.LOCKED

            user_status_info = UserStatusInfo(
                mastery_score=status.mastery_score,
                total_study_minutes=status.total_study_minutes,
                study_count=status.study_count,
                is_unlocked=status.is_unlocked,
                is_collapsed=status.is_collapsed,
                is_favorite=status.is_favorite,
                last_study_at=status.last_study_at,
                next_review_at=status.next_review_at,
                decay_paused=status.decay_paused,
                status=visual_status,
                brightness=brightness
            )

        return SearchResultItem(
            node=node_base,
            similarity=score,
            user_status=user_status_info
        )
