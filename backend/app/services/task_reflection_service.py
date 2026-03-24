from __future__ import annotations

from datetime import timezone, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.services.cognitive_service import CognitiveService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TaskReflectionService:
    """Generate lightweight reflection prompts and persist reflection answers."""

    PLAN_COOLDOWN = timedelta(hours=24)
    ELIGIBLE_CATEGORIES = {
        TaskFeedbackCategory.TOO_DIFFICULT.value,
        TaskFeedbackCategory.UNCLEAR.value,
        "abandoned",
    }
    PROMPT_TEMPLATES = {
        TaskFeedbackCategory.TOO_DIFFICULT.value: {
            "question": "你觉得难在哪里？是概念没理解、题量太大、还是注意力不够集中？",
            "options": ["概念没理解", "题量太大", "注意力不够集中"],
        },
        TaskFeedbackCategory.UNCLEAR.value: {
            "question": "是任务描述不清楚，还是你不确定从哪里开始？",
            "options": ["任务描述不清楚", "不知道从哪里开始", "缺少示例"],
        },
        "abandoned": {
            "question": "是这个任务不重要了，还是遇到了阻力让你暂时放下？",
            "options": ["任务已经不重要", "遇到了阻力", "时间安排冲突"],
        },
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.system_updates = SystemUpdateService(redis)

    async def maybe_enqueue_reflection_prompt(
        self,
        *,
        user_id: UUID,
        task: Task,
        feedback: TaskFeedback | None,
        category: str | None,
        time_spent_minutes: int | None,
    ) -> dict[str, object] | None:
        normalized = str(category or "").strip().lower()
        if normalized not in self.ELIGIBLE_CATEGORIES:
            return None
        if (time_spent_minutes or 0) <= 10:
            return None
        if not task.plan_id:
            return None
        if await self._on_cooldown(user_id=user_id, plan_id=task.plan_id):
            return None

        prompt = self._build_prompt(
            category=normalized,
            task_id=task.id,
            plan_id=task.plan_id,
            feedback_id=getattr(feedback, "id", None),
            task_title=task.title,
        )
        try:
            await self.system_updates.enqueue(
                user_id,
                build_system_update(
                    update_type="reflection_prompt",
                    category="reflection",
                    title="想更精准地帮你调整一下",
                    description=prompt["question"],
                    priority="medium",
                    metadata={
                        "widget_type": "reflection_card",
                        "reflection_prompt": prompt,
                    },
                ),
            )
            await self._mark_prompted(user_id=user_id, plan_id=task.plan_id)
        except Exception as exc:
            logger.warning(f"Failed to enqueue reflection prompt: {exc}")
        return prompt

    async def create_abandon_feedback_and_prompt(
        self,
        *,
        user_id: UUID,
        task: Task,
        reason: str | None,
        time_spent_minutes: int | None,
    ) -> tuple[TaskFeedback, dict[str, object] | None]:
        result = await self.db.execute(
            select(TaskFeedback).where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.task_id == task.id,
            )
        )
        feedback = result.scalar_one_or_none()
        if feedback is None:
            feedback = TaskFeedback(
                user_id=user_id,
                task_id=task.id,
                feedback_text=reason,
                category="abandoned",
                task_difficulty_snapshot=task.difficulty,
                task_type_snapshot=task.type.value if task.type else None,
                actual_minutes_snapshot=time_spent_minutes,
            )
            self.db.add(feedback)
            await self.db.flush()
        prompt = await self.maybe_enqueue_reflection_prompt(
            user_id=user_id,
            task=task,
            feedback=feedback,
            category="abandoned",
            time_spent_minutes=time_spent_minutes,
        )
        return feedback, prompt

    async def submit_reflection_answer(
        self,
        *,
        user_id: UUID,
        feedback_id: UUID,
        selected_option: str | None,
        free_text: str | None,
    ) -> dict[str, object]:
        result = await self.db.execute(
            select(TaskFeedback, Task)
            .join(Task, Task.id == TaskFeedback.task_id)
            .where(
                TaskFeedback.id == feedback_id,
                TaskFeedback.user_id == user_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            raise ValueError("Feedback not found")
        feedback, task = row

        prompt = self._build_prompt(
            category=str(feedback.category or "").strip().lower() or "abandoned",
            task_id=task.id,
            plan_id=task.plan_id,
            feedback_id=feedback.id,
            task_title=task.title,
        )
        payload = {
            "prompt": prompt,
            "selected_option": (selected_option or "").strip() or None,
            "free_text": (free_text or "").strip() or None,
            "submitted_at": _utcnow().isoformat(),
            "status": "completed",
        }
        feedback.reflection_payload = payload
        await self.db.flush()

        fragment_parts = [
            f"任务《{task.title}》的反思反馈：",
            prompt["question"],
        ]
        if payload["selected_option"]:
            fragment_parts.append(f"用户选择：{payload['selected_option']}")
        if payload["free_text"]:
            fragment_parts.append(f"补充说明：{payload['free_text']}")

        cognitive_service = CognitiveService(self.db)
        fragment = await cognitive_service.create_fragment(
            user_id=user_id,
            content=" ".join(fragment_parts),
            source_type="reflection_auto",
            context_tags={
                "task_id": str(task.id),
                "plan_id": str(task.plan_id) if task.plan_id else "",
                "feedback_id": str(feedback.id),
                "selected_option": payload["selected_option"],
                "reflection_category": str(feedback.category or ""),
            },
            error_tags=[f"reflection.{str(feedback.category or 'unknown')}"],
            severity=2,
            task_id=task.id,
            source_event_id=f"reflection_auto:{feedback.id}",
        )
        await cognitive_service.analyze_behavior(user_id, fragment.id)
        return payload

    def _build_prompt(
        self,
        *,
        category: str,
        task_id: UUID,
        plan_id: UUID | None,
        feedback_id: UUID | None,
        task_title: str,
    ) -> dict[str, object]:
        template = self.PROMPT_TEMPLATES.get(category) or self.PROMPT_TEMPLATES["abandoned"]
        return {
            "task_id": str(task_id),
            "plan_id": str(plan_id) if plan_id else "",
            "feedback_id": str(feedback_id) if feedback_id else "",
            "task_title": task_title,
            "category": category,
            "question": template["question"],
            "options": template["options"],
        }

    async def _on_cooldown(self, *, user_id: UUID, plan_id: UUID) -> bool:
        if not self.redis:
            return False
        key = f"reflection_prompt:{user_id}:{plan_id}"
        try:
            return bool(await self.redis.exists(key))
        except Exception:
            return False

    async def _mark_prompted(self, *, user_id: UUID, plan_id: UUID) -> None:
        if not self.redis:
            return
        key = f"reflection_prompt:{user_id}:{plan_id}"
        try:
            await self.redis.setex(key, int(self.PLAN_COOLDOWN.total_seconds()), "1")
        except Exception as exc:
            logger.warning(f"Failed to set reflection cooldown: {exc}")
