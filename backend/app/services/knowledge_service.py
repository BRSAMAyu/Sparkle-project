"""
Knowledge Retrieval Service (RAG)
Wraps GalaxyService to provide context for the AI Agent
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from uuid import UUID

from google.protobuf import json_format
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.metrics import RAG_RETRIEVAL_LATENCY
from app.core.sse import sse_manager
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus
from app.models.subject import Subject
from app.schemas.galaxy import SearchResultItem
from app.services.embedding_service import embedding_service
from app.services.galaxy.rag_router import RagRouter
from app.services.galaxy_service import GalaxyService
from app.services.llm_fallback_utils import hyde_llm


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

    async def _resolve_subject_id(self, subject: str | None) -> int | None:
        if not subject:
            return None
        stmt = select(Subject.id).where(Subject.name == subject).limit(1)
        return await self.db.scalar(stmt)

    async def find_node_by_name(self, user_id: UUID, name: str) -> KnowledgeNode | None:
        stmt = (
            select(KnowledgeNode)
            .join(
                UserNodeStatus,
                UserNodeStatus.node_id == KnowledgeNode.id,
            )
            .where(
                UserNodeStatus.user_id == user_id,
                KnowledgeNode.name == name,
            )
            .limit(1)
        )
        return await self.db.scalar(stmt)

    async def create_node(
        self,
        *,
        user_id: UUID,
        name: str,
        subject: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> KnowledgeNode:
        return await self.galaxy_service.create_node(
            user_id=user_id,
            title=name,
            summary=description,
            subject_id=await self._resolve_subject_id(subject),
            tags=tags or [],
        )

    async def update_node_mastery(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        mastery_delta: float = 0.1,
    ):
        status = await self.db.scalar(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id,
            )
        )
        current_mastery = float(getattr(status, "mastery_score", 0) or 0)
        new_mastery = max(0, min(100, round(current_mastery + mastery_delta * 100)))
        return await self.galaxy_service.update_node_mastery(
            user_id=user_id,
            node_id=node_id,
            new_mastery=new_mastery,
            reason="knowledge_service_increment",
        )

    async def create_or_update_link(
        self,
        *,
        user_id: UUID,
        source_name: str,
        target_name: str,
        relation_type: str,
        strength: float = 0.5,
    ) -> bool:
        source_node = await self.find_node_by_name(user_id, source_name)
        if source_node is None:
            source_node = await self.create_node(
                user_id=user_id,
                name=source_name,
                subject=source_name if relation_type == "contains" else None,
                description="",
                tags=[source_name],
            )

        target_node = await self.find_node_by_name(user_id, target_name)
        if target_node is None:
            target_node = await self.create_node(
                user_id=user_id,
                name=target_name,
                description="",
                tags=[target_name],
            )

        relation = await self.db.scalar(
            select(NodeRelation).where(
                NodeRelation.source_node_id == source_node.id,
                NodeRelation.target_node_id == target_node.id,
            )
        )
        if relation:
            changed = False
            if relation.relation_type != relation_type:
                relation.relation_type = relation_type
                changed = True
            if float(relation.strength or 0) < strength:
                relation.strength = strength
                changed = True
            if changed:
                self.db.add(relation)
                await self.db.flush()
                await self.db.commit()
                from app.services.expansion_service import ExpansionService

                await ExpansionService(self.db)._invalidate_after_graph_mutation(user_id)
            return changed

        self.db.add(
            NodeRelation(
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                relation_type=relation_type,
                strength=strength,
                created_by="knowledge_service",
            )
        )
        await self.db.flush()
        await self.db.commit()
        from app.services.expansion_service import ExpansionService

        await ExpansionService(self.db)._invalidate_after_graph_mutation(user_id)
        return True

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
            response = await hyde_llm.call(messages, fallback="", temperature=0.7)
            return response if response else query
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
                except TimeoutError:
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
            results: list[SearchResultItem] = await self.galaxy_service.hybrid_search(
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
            try:
                payload = json_format.MessageToDict(
                    evidence_pack,
                    preserving_proto_field_name=True,
                    including_default_value_fields=False,
                )
            except TypeError:
                payload = json_format.MessageToDict(
                    evidence_pack,
                    preserving_proto_field_name=True,
                )

            await sse_manager.send_to_user(str(user_id), "evidence_pack", payload)

            # Format as context string
            context_lines = ["Relevant Knowledge Base (Graph Augmented):"]
            for item in results:
                node = item.node
                status = item.user_status

                status_str = "Unknown"
                if status:
                    status_str = f"Unlocked (Mastery: {status.mastery_score}%)" if status.is_unlocked else "Locked"

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

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        subject_id: int | None = None
    ) -> list[KnowledgeSearchHit]:
        """
        Minimal vector search for GraphRAG path.

        Returns:
            List of KnowledgeSearchHit with similarity scores.
        """
        if not query:
            return []

        try:
            start_time = time.time()
            query_embedding = await embedding_service.get_embedding(query, text_type="query")
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

            hits: list[KnowledgeSearchHit] = []
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

    async def get_knowledge_version(self) -> str | None:
        """
        Return cached knowledge version used for semantic cache keys.
        """
        try:
            return await self.galaxy_service.retrieval._get_knowledge_version()
        except Exception as e:
            logger.warning(f"Failed to fetch knowledge version: {e}")
            return None
