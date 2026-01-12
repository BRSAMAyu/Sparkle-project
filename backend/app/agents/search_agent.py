"""
Search Agent - 检索智能体

基于知识星图检索，为其他智能体提供证据和上下文。
"""

from typing import List, Dict, Any
from uuid import UUID
from loguru import logger

from .base_agent import BaseAgent, AgentRole, AgentContext, AgentResponse
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.llm_service import llm_service


class SearchAgent(BaseAgent):
    """检索专家智能体"""

    def __init__(self):
        super().__init__()
        self.role = AgentRole.SEARCH
        self.name = "Search Expert"
        self.description = "Retrieves relevant knowledge graph nodes and summarizes evidence"
        self.capabilities = [
            "Hybrid search over knowledge graph",
            "Summarize evidence with citations",
            "Provide structured search results"
        ]

    def can_handle(self, query: str) -> float:
        search_keywords = ["查找", "搜索", "资料", "来源", "证据", "引用", "文献", "依据", "reference"]
        query_lower = query.lower()
        matches = sum(1 for kw in search_keywords if kw in query_lower)
        return min(matches * 0.25, 1.0)

    async def process(self, context: AgentContext) -> AgentResponse:
        logger.info(f"SearchAgent processing: {context.user_query[:50]}...")

        search_results: List[Dict[str, Any]] = []
        summary_text = ""

        if context.db_session:
            try:
                retrieval = KnowledgeRetrievalService(context.db_session)
                user_id = UUID(context.user_id)
                results = await retrieval.hybrid_search(
                    user_id=user_id,
                    query=context.user_query,
                    limit=5,
                    threshold=0.3
                )

                for item in results:
                    search_results.append({
                        "node_id": str(item.node.id),
                        "name": item.node.name,
                        "description": item.node.description,
                        "similarity": item.similarity
                    })
            except Exception as e:
                logger.error(f"SearchAgent retrieval failed: {e}")

        if search_results:
            citations = "\n".join([
                f"- {r['name']}: {r.get('description', '')[:80]}"
                for r in search_results
            ])
            prompt = f"""You are a research assistant.

Summarize the following evidence for the user query:

User Query: {context.user_query}

Evidence:
{citations}

Return a concise summary with 2-4 bullet points and mention the most relevant items."""
            summary_text = await llm_service.chat(
                messages=[
                    {"role": "system", "content": "You summarize evidence succinctly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
        else:
            summary_text = "暂无可用的知识星图检索结果，我将基于通用知识进行回答。"

        return self.format_response(
            text=summary_text,
            reasoning="Retrieved knowledge graph evidence and summarized key points",
            confidence=0.85 if search_results else 0.5,
            metadata={"search_results": search_results}
        )
