import re
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.task import TaskCreate
from app.services.cognitive_service import CognitiveService
from app.services.llm_service import llm_service
from app.services.task_service import TaskService


class OmniBarService:
    _TASK_PREFIXES = (
        "提醒我",
        "帮我提醒",
        "请提醒我",
        "记得提醒我",
        "创建任务",
        "帮我创建任务",
        "新建任务",
        "添加任务",
        "加个任务",
        "创建一个任务",
        "记个待办",
        "加个待办",
        "remind me",
        "create a task",
        "create task",
        "add a task",
        "add task",
        "todo",
    )
    _TASK_KEYWORDS = (
        "提醒",
        "任务",
        "待办",
        "todo",
        "remind",
        "schedule",
        "复习",
        "学习",
        "刷题",
        "练习",
    )
    _TASK_TYPE_HINTS = {
        "复习": "learning",
        "学习": "learning",
        "背": "learning",
        "阅读": "learning",
        "刷题": "training",
        "练习": "training",
        "训练": "training",
        "运动": "training",
        "锻炼": "training",
        "写总结": "reflection",
        "复盘": "reflection",
        "反思": "reflection",
        "联系": "social",
        "沟通": "social",
        "约": "social",
    }

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
                cognitive_service = CognitiveService(self.db)
                fragment = await cognitive_service.create_fragment(
                    user_id=user_id,
                    content=text,
                    source_type="capsule",
                    resource_type="text",
                )
                return {"action_type": "CAPSULE", "data": fragment}
            except Exception as e:
                logger.error(f"Failed to create capsule: {e}")
                return {"action_type": "CHAT", "data": {"message": "Failed to save thought capsule."}}

        else: # CHAT
            return {"action_type": "CHAT", "data": {"initial_message": text}}

    async def _classify_intent(self, text: str) -> dict[str, Any]:
        rule_based = self._rule_based_classify_intent(text)
        if rule_based is not None:
            return rule_based

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
            return self._fallback_after_llm(text, None)
        return self._fallback_after_llm(text, result)

    def _fallback_after_llm(
        self,
        text: str,
        result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if result is None:
            return {"type": "CHAT"}

        intent_type = str(result.get("type", "CHAT")).upper()
        if intent_type != "CHAT":
            return result

        rule_based = self._rule_based_classify_intent(text)
        if rule_based is not None:
            logger.info("OmniBar rule fallback promoted CHAT -> TASK for explicit reminder/task input")
            return rule_based

        return result

    def _rule_based_classify_intent(self, text: str) -> dict[str, Any] | None:
        normalized = (text or "").strip()
        if not normalized:
            return None

        lower = normalized.lower()
        has_explicit_prefix = any(lower.startswith(prefix.lower()) for prefix in self._TASK_PREFIXES)
        has_task_keyword = any(keyword in lower for keyword in self._TASK_KEYWORDS)

        if not has_explicit_prefix and not has_task_keyword:
            return None

        title = self._normalize_task_title(normalized)
        estimated_minutes = self._extract_estimated_minutes(normalized)
        task_type = self._infer_task_type(normalized)

        return {
            "type": "TASK",
            "data": {
                "title": title,
                "type": task_type,
                "estimated_minutes": estimated_minutes,
                "priority": 2 if has_explicit_prefix else 1,
            },
        }

    def _normalize_task_title(self, text: str) -> str:
        normalized = text.strip()

        for prefix in self._TASK_PREFIXES:
            if normalized.lower().startswith(prefix.lower()):
                normalized = normalized[len(prefix):].strip(" ，,：:。.!！")
                break

        normalized = re.sub(r"^(请|帮我|麻烦你)\s*", "", normalized)
        normalized = normalized.strip()
        return normalized or text[:50]

    @staticmethod
    def _extract_estimated_minutes(text: str) -> int:
        minute_match = re.search(r"(\d{1,3})\s*(分钟|min|mins|minutes?)", text, re.IGNORECASE)
        if minute_match:
            return max(1, int(minute_match.group(1)))

        hour_match = re.search(r"(\d{1,2})\s*(小时|hour|hours?)", text, re.IGNORECASE)
        if hour_match:
            return max(1, int(hour_match.group(1)) * 60)

        return 30

    def _infer_task_type(self, text: str) -> str:
        for keyword, task_type in self._TASK_TYPE_HINTS.items():
            if keyword in text:
                return task_type
        return "learning"
