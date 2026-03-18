"""
Task Feedback Service

处理任务反馈，更新用户推断偏好
"""
from __future__ import annotations
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.event_bus import event_bus
from app.models.task import Task, TaskStatus
from app.models.task_feedback import TaskFeedback
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.personalization.preference_service import PreferenceService
from app.services.task_reflection_service import TaskReflectionService


class TaskFeedbackService:
    """
    任务反馈服务

    核心功能：
    - 提交反馈
    - 验证任务状态（必须是COMPLETED）
    - 更新用户推断偏好
    """

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)

    async def submit_feedback(
        self,
        user_id: UUID,
        task_id: UUID,
        completion_quality: int | None = None,
        feedback_text: str | None = None,
        category: str | None = None,
    ) -> tuple[TaskFeedback, dict[str, Any] | None]:
        """
        提交任务反馈

        Args:
            user_id: 用户ID
            task_id: 任务ID
            completion_quality: 完成质量评分 (1-5)
            feedback_text: 用户文字反馈
            category: 反馈分类

        Returns:
            反馈对象
        """
        # 验证任务并获取任务状态快照
        task = await self._get_and_validate_task(task_id, user_id)

        # 检查是否已有反馈
        existing_feedback = await self._get_existing_feedback(user_id, task_id)

        if existing_feedback:
            # 更新现有反馈
            feedback = await self._update_feedback(
                existing_feedback,
                completion_quality,
                feedback_text,
                category,
            )
            logger.info(f"[TaskFeedback] Updated feedback for task {task_id}")
        else:
            # 创建新反馈
            feedback = await self._create_feedback(
                user_id,
                task_id,
                completion_quality,
                feedback_text,
                category,
                task,
            )
            logger.info(f"[TaskFeedback] Created new feedback for task {task_id}")

        await self.db.flush()

        # 计算偏好变化
        depth_delta, difficulty_delta = feedback.calculate_preference_deltas()
        feedback.inferred_depth_delta = depth_delta
        feedback.inferred_difficulty_delta = difficulty_delta

        # 更新用户推断偏好
        await self._update_inferred_preferences(user_id, depth_delta, difficulty_delta)

        # Adaptive replanning based on feedback signals
        if task.plan_id:
            try:
                adaptive_replanner = AdaptiveReplanner(self.db, self.redis)
                await adaptive_replanner.on_task_feedback(
                    user_id=user_id,
                    plan_id=task.plan_id,
                    task_id=task_id,
                    category=feedback.category,
                    difficulty_delta=difficulty_delta,
                )
            except Exception as e:
                logger.warning(f"[TaskFeedback] Adaptive replanning failed: {e}")

        reflection_prompt = None
        try:
            reflection_service = TaskReflectionService(self.db, self.redis)
            reflection_prompt = await reflection_service.maybe_enqueue_reflection_prompt(
                user_id=user_id,
                task=task,
                feedback=feedback,
                category=feedback.category,
                time_spent_minutes=task.actual_minutes,
            )
        except Exception as e:
            logger.warning(f"[TaskFeedback] Reflection prompt generation failed: {e}")

        await self.db.commit()
        await self.db.refresh(
            feedback,
            attribute_names=[
                "id",
                "user_id",
                "task_id",
                "completion_quality",
                "feedback_text",
                "category",
                "inferred_depth_delta",
                "inferred_difficulty_delta",
                "task_difficulty_snapshot",
                "task_type_snapshot",
                "actual_minutes_snapshot",
                "created_at",
                "updated_at",
            ],
        )

        await event_bus.publish(
            "task.feedback_submitted",
            {
                "event_type": "task.feedback_submitted",
                "user_id": str(user_id),
                "task_id": str(task_id),
                "plan_id": str(task.plan_id) if task.plan_id else "",
                "category": feedback.category or "",
                "feedback_text": feedback.feedback_text or "",
            },
        )

        return feedback, reflection_prompt

    async def _get_and_validate_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        获取并验证任务状态

        任务必须存在、属于用户、且状态为COMPLETED
        """
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == user_id,
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status != TaskStatus.COMPLETED:
            raise ValueError(f"Task {task_id} is not completed (status: {task.status.value})")

        return task

    async def _get_existing_feedback(self, user_id: UUID, task_id: UUID) -> TaskFeedback | None:
        """查询现有反馈"""
        result = await self.db.execute(
            select(TaskFeedback)
            .options(
                load_only(
                    TaskFeedback.id,
                    TaskFeedback.user_id,
                    TaskFeedback.task_id,
                    TaskFeedback.completion_quality,
                    TaskFeedback.feedback_text,
                    TaskFeedback.category,
                    TaskFeedback.inferred_depth_delta,
                    TaskFeedback.inferred_difficulty_delta,
                    TaskFeedback.task_difficulty_snapshot,
                    TaskFeedback.task_type_snapshot,
                    TaskFeedback.actual_minutes_snapshot,
                    TaskFeedback.created_at,
                    TaskFeedback.updated_at,
                )
            )
            .where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.task_id == task_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_feedback(
        self,
        user_id: UUID,
        task_id: UUID,
        completion_quality: int | None,
        feedback_text: str | None,
        category: str | None,
        task: Task,
    ) -> TaskFeedback:
        """创建新反馈"""
        feedback = TaskFeedback(
            user_id=user_id,
            task_id=task_id,
            completion_quality=completion_quality,
            feedback_text=feedback_text,
            category=category,
            # 保存任务状态快照
            task_difficulty_snapshot=task.difficulty,
            task_type_snapshot=task.type.value if task.type else None,
            actual_minutes_snapshot=task.actual_minutes,
        )
        self.db.add(feedback)
        return feedback

    async def _update_feedback(
        self,
        feedback: TaskFeedback,
        completion_quality: int | None,
        feedback_text: str | None,
        category: str | None,
    ) -> TaskFeedback:
        """更新现有反馈"""
        if completion_quality is not None:
            feedback.completion_quality = completion_quality
        if feedback_text is not None:
            feedback.feedback_text = feedback_text
        if category is not None:
            feedback.category = category
        return feedback

    async def _update_inferred_preferences(
        self,
        user_id: UUID,
        depth_delta: float | None,
        difficulty_delta: float | None,
    ):
        """
        更新用户推断偏好

        基于反馈计算出的偏好变化，更新用户的推断偏好设置
        """
        if depth_delta is None and difficulty_delta is None:
            return

        updates = {}
        if depth_delta is not None:
            # 平滑更新，避免剧烈波动
            updates["depth_preference"] = depth_delta * 0.1
        if difficulty_delta is not None:
            updates["task_difficulty_preference"] = difficulty_delta * 0.1

        await self.preference_service.update_inferred(user_id, updates)
        logger.debug(f"[TaskFeedback] Updated inferred preferences for user {user_id}: {updates}")

    async def get_task_feedbacks(
        self,
        task_id: UUID,
    ) -> list[TaskFeedback]:
        """获取任务的所有反馈"""
        result = await self.db.execute(
            select(TaskFeedback).where(TaskFeedback.task_id == task_id)
        )
        return list(result.scalars().all())

    async def get_user_task_feedback_stats(
        self,
        user_id: UUID,
    ) -> dict[str, Any]:
        """
        获取用户任务反馈统计

        Returns:
            {
                "total_feedbacks": int,
                "avg_completion_quality": float,
                "category_distribution": dict,
                "recent_feedbacks": list,
            }
        """
        result = await self.db.execute(
            select(TaskFeedback).where(TaskFeedback.user_id == user_id)
        )
        feedbacks = result.scalars().all()

        total = len(feedbacks)
        qualities = [f.completion_quality for f in feedbacks if f.completion_quality is not None]
        avg_quality = sum(qualities) / len(qualities) if qualities else None

        category_dist = {}
        for f in feedbacks:
            if f.category:
                category_dist[f.category] = category_dist.get(f.category, 0) + 1

        # 获取最近的反馈（最多10条）
        recent_result = await self.db.execute(
            select(TaskFeedback)
            .where(TaskFeedback.user_id == user_id)
            .order_by(TaskFeedback.created_at.desc())
            .limit(10)
        )
        recent_feedbacks = list(recent_result.scalars().all())

        return {
            "total_feedbacks": total,
            "avg_completion_quality": avg_quality,
            "category_distribution": category_dist,
            "recent_feedbacks": recent_feedbacks,
        }
