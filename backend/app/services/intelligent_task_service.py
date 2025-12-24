"""
Intelligent Task Service
Handles LLM-driven task assistance, intent recognition, and suggestions.
"""
import json
from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_client import llm_client
from app.services.galaxy_service import GalaxyService
from app.schemas.task import TaskSuggestionResponse, SuggestedNode


class IntelligentTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.galaxy_service = GalaxyService(db)

    async def get_suggestions(
        self, 
        user_id: UUID, 
        input_text: str
    ) -> TaskSuggestionResponse:
        """
        Get intelligent suggestions for a task based on user input.
        """
        # 1. Use LLM to recognize intent and extract keywords/nodes
        intent_data = await self._recognize_intent(input_text)
        
        # 2. Match extracted nodes with existing knowledge graph
        suggested_nodes = []
        
        # Search for existing nodes using semantic search for each extracted term
        for term in intent_data.get("keywords", []):
            search_results = await self.galaxy_service.semantic_search(
                user_id=user_id,
                query=term,
                limit=2,
                threshold=0.4
            )
            
            for res in search_results:
                # Avoid duplicates
                if not any(n.id == res.node.id for n in suggested_nodes):
                    suggested_nodes.append(SuggestedNode(
                        id=res.node.id,
                        name=res.node.name,
                        reason=f"与'{term}'高度相关",
                        is_new=False
                    ))

        # 3. Add potential new nodes suggested by LLM if not enough matches
        if len(suggested_nodes) < 3:
            for node_name in intent_data.get("potential_nodes", []):
                # Check if it already exists (simple name check)
                existing = await self.galaxy_service.keyword_search(user_id, node_name, limit=1)
                if not existing:
                    suggested_nodes.append(SuggestedNode(
                        name=node_name,
                        reason="AI 建议拓展的新知识点",
                        is_new=True
                    ))

        return TaskSuggestionResponse(
            intent=intent_data.get("intent", "学习探索"),
            suggested_nodes=suggested_nodes[:5],
            suggested_tags=intent_data.get("keywords", [])[:5],
            estimated_minutes=intent_data.get("estimated_minutes"),
            difficulty=intent_data.get("difficulty")
        )

    async def _recognize_intent(self, input_text: str) -> dict:
        """
        Internal method to call LLM for intent recognition.
        """
        prompt = f"""你是一个智能学习助手。请分析用户想要创建的任务意图，并提供相关的知识点和关键词建议。

用户输入: "{input_text}"

请返回以下 JSON 格式:
{{
  "intent": "简短的意图描述",
  "keywords": ["关键词1", "关键词2"],
  "potential_nodes": ["可能的知识节点1", "可能的知识节点2"],
  "estimated_minutes": 预计时长(整数),
  "difficulty": 建议难度(1-5)
}}
"""
        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response)
        except Exception:
            # Fallback
            return {{
                "intent": "日常学习",
                "keywords": [],
                "potential_nodes": [],
                "estimated_minutes": 25,
                "difficulty": 1
            }}
