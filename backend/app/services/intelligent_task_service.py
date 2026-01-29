"""
Intelligent Task Service
Handles LLM-driven task assistance, intent recognition, and suggestions.
"""
import json
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.task import SuggestedNode, TaskSuggestionResponse
from app.services.galaxy_service import GalaxyService


class IntelligentTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.galaxy_service = GalaxyService(db)

    async def get_task_nudges(self, db: AsyncSession, user_id: UUID,
                              task_data: dict) -> list[dict]:
        """
        获取任务创建时的 Nudge 建议

        Args:
            db: Database session
            user_id: User ID
            task_data: Task data including estimated_minutes, etc.

        Returns:
            List of nudge suggestions
        """
        nudges = []

        # 1. 检查规划乐观偏差模式
        from app.services.cognitive_service import CognitiveService
        cognitive_service = CognitiveService(db)
        patterns = await cognitive_service.get_user_patterns(user_id, min_confidence=0.6)

        for pattern in patterns:
            if "optimism" in pattern.pattern_name.lower() or "planning" in pattern.pattern_name.lower():
                estimated = task_data.get("estimated_minutes")
                if estimated:
                    # 建议增加时间缓冲
                    suggested = int(estimated * 1.3)
                    nudges.append({
                        "type": "time_adjustment",
                        "title": "检测到规划乐观偏差",
                        "message": f"根据您的历史行为模式，建议将预估时间调整为 {suggested} 分钟",
                        "suggested_value": suggested,
                        "pattern_id": str(pattern.id),
                        "confidence": pattern.confidence_score
                    })

            # 检查任务放弃模式
            if "abandon" in pattern.pattern_name.lower() or "procrastination" in pattern.pattern_name.lower():
                nudges.append({
                    "type": "start_now",
                    "title": "避免任务放弃",
                    "message": "根据历史数据，建议立即开始任务以降低放弃风险",
                    "pattern_id": str(pattern.id),
                    "confidence": pattern.confidence_score
                })

        return nudges

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
        Uses Xiaomi MIMO model for fast response.
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
            # 使用 MIMO 模型进行快速意图识别
            headers = {
                "Authorization": f"Bearer {settings.XIAOMI_MIMO_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": settings.XIAOMI_CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": settings.XIAOMI_TEMPERATURE,
                "response_format": {"type": "json_object"}
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.XIAOMI_MIMO_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                raise ValueError(f"Unexpected response format: {data}")

        except Exception:
            # Fallback to default values
            return {
                "intent": "日常学习",
                "keywords": [],
                "potential_nodes": [],
                "estimated_minutes": 25,
                "difficulty": 1
            }
