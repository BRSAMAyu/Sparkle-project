"""
Knowledge Retrieval Service (RAG)
Wraps GalaxyService to provide context for the AI Agent
"""
from typing import List, Optional
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.galaxy_service import GalaxyService
from app.services.llm_service import llm_service
from app.schemas.galaxy import SearchResultItem

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
