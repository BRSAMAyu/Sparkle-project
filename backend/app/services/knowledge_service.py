"""
Knowledge Retrieval Service (RAG)
Wraps GalaxyService to provide context for the AI Agent
"""
from typing import List
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.galaxy_service import GalaxyService
from app.schemas.galaxy import SearchResultItem

class KnowledgeService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.galaxy_service = GalaxyService(db_session)

    async def retrieve_context(self, user_id: UUID, query: str, limit: int = 5) -> str:
        """
        Retrieve relevant knowledge context for the LLM.
        Returns a formatted string of knowledge nodes.
        """
        try:
            results: List[SearchResultItem] = await self.galaxy_service.semantic_search(
                user_id=user_id,
                query=query,
                limit=limit,
                threshold=0.4 # Somewhat loose to get context
            )
            
            if not results:
                return ""
            
            # Format as context string
            context_lines = ["Relevant Knowledge Base:"]
            for item in results:
                node = item.node
                status = item.user_status
                
                status_str = "Unknown"
                if status:
                    if status.is_unlocked:
                        status_str = f"Unlocked (Mastery: {status.mastery_score}%)"
                    else:
                        status_str = "Locked"
                
                line = f"- [{node.name}]: {node.description or 'No description'} (Status: {status_str})"
                context_lines.append(line)
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge context: {e}")
            return ""