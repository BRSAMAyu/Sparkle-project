
import json
from uuid import UUID
from typing import Dict, Any, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import llm_service
from app.services.task_service import TaskService
from app.services.cognitive_service import CognitiveService
from app.schemas.task import TaskCreate
from app.schemas.cognitive import CognitiveFragmentCreate
from app.models.task import TaskType

class OmniBarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dispatch(self, user_id: UUID, text: str) -> Dict[str, Any]:
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
                # Map LLM data to TaskCreate schema
                # Ensure valid task type, default to learning if invalid or missing
                task_type_str = task_data.get("type", "learning")
                try:
                    task_type = TaskType(task_type_str)
                except ValueError:
                    task_type = TaskType.learning

                task_in = TaskCreate(
                    title=task_data.get("title", text[:50]),
                    type=task_type,
                    estimated_minutes=int(task_data.get("estimated_minutes", 30)),
                    priority=int(task_data.get("priority", 0)),
                    difficulty=1, # Default
                    energy_cost=1 # Default
                )
                
                # TaskService methods are static
                task = await TaskService.create(db=self.db, obj_in=task_in, user_id=user_id)
                return {"action_type": "TASK", "data": task}
            except Exception as e:
                logger.error(f"Failed to create task from omnibar: {e}")
                # Fallback to CHAT
                return {"action_type": "CHAT", "data": {"message": f"I tried to create a task but failed: {e}. Let's chat instead."}}

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

    async def _classify_intent(self, text: str) -> Dict[str, Any]:
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
        
        try:
            response = await llm_service.chat(messages, temperature=0.1)
            # Clean json
            cleaned = response.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"OmniBar classification failed: {e}")
            return {"type": "CHAT"}
