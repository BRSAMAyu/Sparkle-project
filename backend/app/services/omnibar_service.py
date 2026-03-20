
import json
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.cognitive import CognitiveFragmentCreate
from app.schemas.task import TaskCreate
from app.services.cognitive_service import CognitiveService
from app.services.llm_service import llm_service
from app.services.task_service import TaskService


class OmniBarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dispatch(self, user_id: UUID, text: str) -> dict[str, Any]:
        """
        Dispatch user input to appropriate service
        Returns:
            {
                "action_type": "TASK" | "CAPSULE" | "CHAT",
                "data": ... (TaskDetail | CognitiveFragmentResponse | dict)
            }
        """
        # 1. LLM Classification
        classification = await self._classify_intent(text)
        action_type = classification.get("type", "CHAT")

        logger.info(f"OmniBar dispatching: {text} -> {action_type}")

        if action_type == "TASK":
            task_data = classification.get("data", {})
            try:
                task_in = TaskCreate(
                    title=task_data.get("title", text[:50]),
                    # Let TaskCreate normalize lower-case / alias task types.
                    type=task_data.get("type", "learning"),
                    estimated_minutes=int(task_data.get("estimated_minutes", 30)),
                    priority=int(task_data.get("priority", 1)),
                    difficulty=1,
                    energy_cost=1,
                )

                task = await TaskService.create(db=self.db, obj_in=task_in, user_id=user_id)
                return {"action_type": "TASK", "data": task}
            except Exception as e:
                logger.error(f"Failed to create task from omnibar: {e}")
                return {
                    "action_type": "CHAT",
                    "data": {
                        "message": "我尝试为你创建任务，但创建失败了，先切回聊天模式继续帮你处理。",
                        "error": str(e),
                    },
                }

        elif action_type == "CAPSULE":
            try:
                fragment_in = CognitiveFragmentCreate(
                    content=text,
                    source_type="capsule"
                )
                # Use CognitiveService instance as per its design
                cognitive_service = CognitiveService(self.db)
                fragment = await cognitive_service.create_fragment(
                    user_id=user_id,
                    data=fragment_in,
                    background_tasks=None # Force sync
                )
                return {"action_type": "CAPSULE", "data": fragment}
            except Exception as e:
                logger.error(f"Failed to create capsule: {e}")
                return {"action_type": "CHAT", "data": {"message": "Failed to save thought capsule."}}

        else: # CHAT
            return {"action_type": "CHAT", "data": {"initial_message": text}}

    async def _classify_intent(self, text: str) -> dict[str, Any]:
        from app.services.llm_fallback_utils import omnibar_llm

        system_prompt = """
        You are the Omni-Bar Intent Classifier for the Sparkle App.
        Analyze the user's input and classify into:
        1. 'CAPSULE': Thoughts, emotions, complaints, ideas, random musings. (e.g., 'I'm anxious', 'Good idea for project', 'Why is math so hard?').
        2. 'TASK': Explicit commands to create a task or reminder. (e.g., 'Remind me to study', 'Plan math revision', 'Create task for history').
        3. 'CHAT': Questions, conversation, requests for advice, or anything complex requiring multi-turn dialogue.

        If TASK, extract: title, type (learning/training/reflection/social), estimated_minutes (int, default 30), priority (1-3).

        Return JSON ONLY: { "type": "...", "data": ... }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        result = await omnibar_llm.json_call(
            messages,
            fallback={"type": "CHAT"},  # 默认降级到聊天模式
            temperature=0.1,
        )
        if result is None:
            return {"type": "CHAT"}
        return result
