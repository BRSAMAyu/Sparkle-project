"""
Knowledge Retrieval Service (RAG)
Wraps GalaxyService to provide context for the AI Agent
"""
from dataclasses import dataclass
import time
from typing import List, Optional
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.galaxy_service import GalaxyService
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.schemas.galaxy import SearchResultItem
from app.models.galaxy import KnowledgeNode
from app.core.metrics import RAG_RETRIEVAL_LATENCY


@dataclass
class KnowledgeSearchHit:
    id: UUID
    name: str
    description: str
    similarity: float

class KnowledgeService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.galaxy_service = GalaxyService(db_session)

    async def _generate_hypothetical_answer(self, query: str) -> str:
        """
        HyDE (Hypothetical Document Embeddings) Strategy:
        Ask LLM to generate a hypothetical answer to the query.
        This answer is then used for vector retrieval, matching 'answer to answer'
        instead of 'question to answer'.
        """
        try:
            prompt = (
                f"Please write a brief, hypothetical passage that answers the following question. "
                f"Focus on including relevant keywords and concepts that might appear in a textbook or knowledge base. "
                f"Question: {query}"
            )
            
            # Use a fast, cheap call if possible, or just the standard chat
            messages = [{"role": "user", "content": prompt}]
            response = await llm_service.chat(messages, temperature=0.7)
            return response
        except Exception as e:
            logger.warning(f"HyDE generation failed, falling back to original query: {e}")
            return query

    async def generate_hypothetical_answer(self, query: str) -> str:
        """
        Public wrapper for HyDE generation.
        """
        return await self._generate_hypothetical_answer(query)

    async def retrieve_context(self, user_id: UUID, query: str, limit: int = 5) -> str:
        """
        Retrieve relevant knowledge context for the LLM using Hybrid Search (RAG v2.0).
        Returns a formatted string of knowledge nodes.
        """
        try:
            # 1. Query Expansion / HyDE
            # Generate a hypothetical answer to improve vector search alignment
            hypothetical_answer = await self._generate_hypothetical_answer(query)
            logger.debug(f"HyDE generated: {hypothetical_answer[:100]}...")

            # 2. Hybrid Search
            # Use hypothetical_answer for vector search, original query for keyword search & reranking
            results: List[SearchResultItem] = await self.galaxy_service.hybrid_search(
                user_id=user_id,
                query=query,
                vector_query=hypothetical_answer,
                limit=limit,
                threshold=0.4 # Slightly looser for hybrid search
            )
            
            if not results:
                return ""
            
            # Format as context string
            context_lines = ["Relevant Knowledge Base (Graph Augmented):"]
            for item in results:
                node = item.node
                status = item.user_status
                
                status_str = "Unknown"
                if status:
                    if status.is_unlocked:
                        status_str = f"Unlocked (Mastery: {status.mastery_score}%)"
                    else:
                        status_str = "Locked"
                
                # Basic Node Info
                line = f"- [{node.name}]: {node.description or 'No description'} (Status: {status_str})"
                if node.parent_name:
                    line += f" (Parent: {node.parent_name})"
                
                # [Graph RAG] Fetch Neighbors
                try:
                    neighbors = await self.galaxy_service.get_node_neighbors(node.id, limit=5)
                    if neighbors:
                        # Limit to top 3 related nodes to save tokens
                        top_neighbors = neighbors[:3]
                        neighbor_names = [n.name for n in top_neighbors]
                        line += f" [Related: {', '.join(neighbor_names)}]"
                except Exception as e:
                    logger.warning(f"Failed to fetch neighbors for {node.id}: {e}")

                context_lines.append(line)
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge context: {e}")
            return ""

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        subject_id: Optional[int] = None
    ) -> List[KnowledgeSearchHit]:
        """
        Minimal vector search for GraphRAG path.

        Returns:
            List of KnowledgeSearchHit with similarity scores.
        """
        if not query:
            return []

        try:
            start_time = time.time()
            query_embedding = await embedding_service.get_embedding(query)
            stmt = (
                select(
                    KnowledgeNode,
                    KnowledgeNode.embedding.cosine_distance(query_embedding).label("distance")
                )
                .options(
                    selectinload(KnowledgeNode.subject),
                    selectinload(KnowledgeNode.parent)
                )
                .where(KnowledgeNode.embedding.isnot(None))
            )
            if subject_id:
                stmt = stmt.where(KnowledgeNode.subject_id == subject_id)

            stmt = stmt.order_by("distance").limit(top_k)
            result = await self.db.execute(stmt)
            rows = result.all()

            hits: List[KnowledgeSearchHit] = []
            for node, distance in rows:
                if distance is None:
                    continue
                similarity = max(0.0, 1.0 - float(distance))
                if similarity < min_similarity:
                    continue
                hits.append(
                    KnowledgeSearchHit(
                        id=node.id,
                        name=node.name,
                        description=node.description or "",
                        similarity=similarity
                    )
                )

            RAG_RETRIEVAL_LATENCY.labels(source="pgvector", stage="retrieve").observe(
                time.time() - start_time
            )
            return hits
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def get_knowledge_version(self) -> Optional[str]:
        """
        Return cached knowledge version used for semantic cache keys.
        """
        try:
            return await self.galaxy_service.retrieval._get_knowledge_version()
        except Exception as e:
            logger.warning(f"Failed to fetch knowledge version: {e}")
            return None
