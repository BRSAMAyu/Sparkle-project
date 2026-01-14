"""
Knowledge Retrieval Service (RAG)
Wraps GalaxyService to provide context for the AI Agent
"""
from typing import List, Optional
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from app.services.galaxy_service import GalaxyService
from app.services.llm_service import llm_service
from app.schemas.galaxy import SearchResultItem
from app.services.galaxy.rag_router import RagRouter
from app.core.sse import sse_manager
from google.protobuf import json_format

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
            strategy = RagRouter().select(query)

            vector_query = None
            if strategy.enable_hyde:
                vector_query = await self._generate_hypothetical_answer(query)
                logger.debug(f"HyDE generated: {vector_query[:100]}...")

            # 2. Hybrid Search
            # Use vector_query when enabled; otherwise default to original query.
            results: List[SearchResultItem] = await self.galaxy_service.hybrid_search(
                user_id=user_id,
                query=query,
                vector_query=vector_query,
                limit=limit,
                threshold=0.4,
                use_reranker=strategy.use_reranker,
            )
            
            if not results:
                return ""

            request_id = str(uuid.uuid4())
            trace_id = str(uuid.uuid4())
            evidence_pack = self.galaxy_service.build_evidence_pack(
                results,
                request_id=request_id,
                trace_id=trace_id,
                query=query,
                strategy_name=strategy.name,
            )
            await sse_manager.send_to_user(
                str(user_id),
                "evidence_pack",
                json_format.MessageToDict(
                    evidence_pack,
                    preserving_proto_field_name=True,
                    including_default_value_fields=False,
                ),
            )
            
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
                
                if strategy.enable_graph:
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
