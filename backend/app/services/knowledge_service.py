"""
Knowledge Retrieval Service (RAG)
Wraps GalaxyService to provide context for the AI Agent
"""
from typing import List, Optional
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

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
        Implements Parallel Execution and Stability Guardrails (PR-9).
        """
        try:
            strategy = RagRouter().select(query)
            
            # LATENCY_BUDGET: Total time allowed for retrieval
            # We reserve 0.5s for the actual vector search and ranking, 
            # so HyDE gen must complete within budget - 0.5s
            LATENCY_BUDGET = 1.5
            HYDE_TIMEOUT = max(0.5, LATENCY_BUDGET - 0.5)

            vector_query = None
            
            # --- HyDE Guardrails & Parallelization ---
            
            async def _run_raw():
                # Raw path is always executed
                return query

            async def _run_hyde():
                # HyDE path
                return await self._generate_hypothetical_answer(query)

            # HyDE Gate: Check if we should even attempt HyDE
            # Skip if strategy disabled or query too specific/long (likely has entities)
            should_run_hyde = strategy.enable_hyde and len(query) < 100

            if should_run_hyde:
                # Run Parallel: Raw Retrieval (implicit) vs HyDE Generation
                # Note: We need the vector_query string before we can search.
                # So we are parallelizing the *generation* of HyDE against the *wait time*.
                # Ideally we would parallelize Raw-Search vs HyDE-Search, but HyDE-Search depends on Gen.
                # PR-9 optimization: We treat Raw Search as a fallback that is always ready.
                
                # Start HyDE Generation
                hyde_task = asyncio.create_task(_run_hyde())
                
                try:
                    # Wait for HyDE with timeout
                    # If it finishes, we use it. If not, we downgrade.
                    vector_query = await asyncio.wait_for(hyde_task, timeout=HYDE_TIMEOUT)
                    logger.debug(f"HyDE generated within budget: {vector_query[:50]}...")
                except asyncio.TimeoutError:
                    # Cancel the phantom request to save tokens (if provider supports it) and resources
                    hyde_task.cancel()
                    logger.warning(f"HyDE timed out ({HYDE_TIMEOUT}s), downgraded to Raw strategy")
                    # vector_query remains None, falling back to query
                except Exception as e:
                    logger.error(f"HyDE generation failed: {e}")
                    # vector_query remains None
            
            # --- End Guardrails ---

            # 2. Hybrid Search (Network Call)
            # Use vector_query when available; otherwise default to original query.
            # This step is the "Retrieval" part.
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
                strategy_name=strategy.name + ("_downgraded" if strategy.enable_hyde and vector_query is None else ""),
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
