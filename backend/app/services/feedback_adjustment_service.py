"""
Feedback-Driven Adjustment Service - 用户反馈闭环系统

将用户完成任务后的反馈转化为实际的动作：
- 任务难度动态调整
- 时间估计校准
- 任务删除/修改
- 剩余方案优化

Design:
用户完成任务
    ↓
FeedbackEvent (类型+数据)
    ↓
FeedbackDrivenAdjustmentService
    ├─ DifficultyCalibrator → 调整剩余任务难度
    ├─ TimeEstimateCalibrator → 校准时间估计
    └─ TaskAdjuster → 删除/修改任务
    ↓
AdjustmentAction[] (实际执行)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.services.plan_state_service import PlanStateService


class FeedbackType(str, Enum):
    """反馈类型枚举"""
    TASK_COMPLETED = "task_completed"
    TASK_TOO_HARD = "task_too_hard"
    TASK_TOO_EASY = "task_too_easy"
    TIME_UNDERESTIMATE = "time_underestimate"
    TIME_OVERESTIMATE = "time_overestimate"
    WANT_MORE_PRACTICE = "want_more_practice"
    SKIP_SIMILAR = "skip_similar"
    TOPIC_MASTERED = "topic_mastered"
    TASK_SKIPPED = "task_skipped"
    NEGATIVE_FEEDBACK = "negative_feedback"


@dataclass
class FeedbackEvent:
    """反馈事件"""
    event_id: str
    user_id: UUID
    plan_id: UUID
    task_id: UUID | None

    feedback_type: FeedbackType
    timestamp: datetime

    # 反馈详情
    rating: int | None = None  # 1-5 星评分
    actual_duration_minutes: int | None = None
    difficulty_perception: str | None = None  # "easy", "medium", "hard"
    comment: str | None = None

    # 相关任务信息
    task_type: str | None = None
    knowledge_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "user_id": str(self.user_id),
            "plan_id": str(self.plan_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "feedback_type": self.feedback_type.value,
            "timestamp": self.timestamp.isoformat(),
            "rating": self.rating,
            "actual_duration_minutes": self.actual_duration_minutes,
            "difficulty_perception": self.difficulty_perception,
            "comment": self.comment,
            "task_type": self.task_type,
            "knowledge_nodes": self.knowledge_nodes
        }


@dataclass
class AdjustmentAction:
    """调整动作"""
    action_type: str  # "delete_task", "modify_task", "adjust_difficulty", "adjust_estimate"
    target_task_ids: list[UUID]
    parameters: dict[str, Any]
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target_task_ids": [str(tid) for tid in self.target_task_ids],
            "parameters": self.parameters,
            "reason": self.reason,
            "confidence": self.confidence
        }


class DifficultyCalibrator:
    """难度校准器"""

    def __init__(self):
        self._history: dict[str, list[dict]] = {}  # task_type -> [{expected, perceived, time_ratio}]

    def record(
        self,
        task_type: str,
        expected_difficulty: int,
        perceived_difficulty: str,
        completion_time_ratio: float
    ):
        """记录难度反馈"""
        if task_type not in self._history:
            self._history[task_type] = []

        self._history[task_type].append({
            "expected": expected_difficulty,
            "perceived": perceived_difficulty,
            "time_ratio": completion_time_ratio,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 保留最近20条记录
        if len(self._history[task_type]) > 20:
            self._history[task_type] = self._history[task_type][-20:]

    def get_adjustment(self, task_type: str) -> int:
        """
        获取难度调整值 (-2 到 +2)

        Args:
            task_type: 任务类型

        Returns:
            int: 调整值
        """
        history = self._history.get(task_type, [])
        if len(history) < 3:
            return 0

        # 计算平均感知难度
        adjustments = []
        for record in history:
            expected = record["expected"]
            perceived = record["perceived"]
            time_ratio = record["time_ratio"]

            # 基于感知难度调整
            if perceived == "hard" and expected < 4:
                adjustments.append(1)
            elif perceived == "easy" and expected > 2:
                adjustments.append(-1)
            else:
                adjustments.append(0)

            # 基于时间比率调整（时间远超预期说明偏难）
            if time_ratio > 1.5:
                adjustments.append(1)
            elif time_ratio < 0.7:
                adjustments.append(-1)

        if not adjustments:
            return 0

        avg_adjustment = sum(adjustments) / len(adjustments)
        return max(-2, min(2, round(avg_adjustment)))


class TimeEstimateCalibrator:
    """时间估计校准器"""

    def __init__(self):
        self._history: dict[str, list[tuple]] = {}  # task_type -> [(estimated, actual)]

    def record(self, task_type: str, estimated: int, actual: int):
        """记录时间反馈"""
        if task_type not in self._history:
            self._history[task_type] = []

        self._history[task_type].append((estimated, actual))

        # 保留最近20条记录
        if len(self._history[task_type]) > 20:
            self._history[task_type] = self._history[task_type][-20:]

    def get_adjustment_factor(self, task_type: str) -> float:
        """
        获取时间调整系数

        Args:
            task_type: 任务类型

        Returns:
            float: 调整系数（如 1.3 表示需要增加30%时间）
        """
        history = self._history.get(task_type, [])
        if len(history) < 3:
            return 1.0

        # 计算平均比率
        ratios = []
        for estimated, actual in history:
            if estimated > 0:
                ratios.append(actual / estimated)

        if not ratios:
            return 1.0

        avg_ratio = sum(ratios) / len(ratios)

        # 限制在合理范围
        return max(0.5, min(2.0, avg_ratio))


class FeedbackDrivenAdjustmentService:
    """
    反馈驱动的调整服务

    职责:
    1. 处理用户反馈事件
    2. 生成调整动作
    3. 应用调整到数据库
    4. 记录到 PlanState
    """

    def __init__(
        self,
        db: AsyncSession,
        plan_state_service: PlanStateService
    ):
        self.db = db
        self.plan_state_service = plan_state_service
        self.difficulty_calibrator = DifficultyCalibrator()
        self.time_calibrator = TimeEstimateCalibrator()

        logger.info("FeedbackDrivenAdjustmentService initialized")

    async def process_feedback(
        self,
        event: FeedbackEvent
    ) -> list[AdjustmentAction]:
        """
        处理反馈事件并生成调整动作

        Args:
            event: 反馈事件

        Returns:
            List[AdjustmentAction]: 生成的调整动作列表
        """
        actions = []

        if event.feedback_type == FeedbackType.TASK_COMPLETED:
            actions.extend(await self._handle_task_completed(event))

        elif event.feedback_type == FeedbackType.TASK_TOO_HARD:
            actions.extend(await self._handle_difficulty_feedback(event, "hard"))

        elif event.feedback_type == FeedbackType.TASK_TOO_EASY:
            actions.extend(await self._handle_difficulty_feedback(event, "easy"))

        elif event.feedback_type in [FeedbackType.TIME_UNDERESTIMATE, FeedbackType.TIME_OVERESTIMATE]:
            actions.extend(await self._handle_time_feedback(event))

        elif event.feedback_type == FeedbackType.SKIP_SIMILAR:
            actions.extend(await self._handle_skip_similar(event))

        elif event.feedback_type == FeedbackType.TOPIC_MASTERED:
            actions.extend(await self._handle_topic_mastered(event))

        # 应用调整动作
        for action in actions:
            await self._apply_action(action, event.user_id, event.plan_id)

        # 记录反馈到 PlanState
        await self._record_feedback_with_actions(event, actions)

        return actions

    async def _handle_task_completed(
        self,
        event: FeedbackEvent
    ) -> list[AdjustmentAction]:
        """处理任务完成反馈"""
        actions = []

        # 时间校准
        if event.actual_duration_minutes and event.task_id:
            task = await self._get_task(event.task_id, event.user_id)
            if task and task.estimated_minutes:
                ratio = event.actual_duration_minutes / task.estimated_minutes

                # 记录校准数据
                self.time_calibrator.record(
                    task_type=task.type.value,
                    estimated=task.estimated_minutes,
                    actual=event.actual_duration_minutes
                )

                # 如果偏差较大，调整剩余同类任务
                if ratio > 1.5 or ratio < 0.6:
                    similar_tasks = await self._find_similar_pending_tasks(
                        event.plan_id,
                        task,
                        event.user_id
                    )

                    if similar_tasks:
                        adjustment_factor = self.time_calibrator.get_adjustment_factor(task.type.value)
                        if abs(adjustment_factor - 1.0) > 0.2:  # 偏差超过20%
                            actions.append(AdjustmentAction(
                                action_type="adjust_estimate",
                                target_task_ids=[t.id for t in similar_tasks],
                                parameters={"time_factor": adjustment_factor},
                                reason=f"Time calibration: {adjustment_factor:.2f}x based on completed task",
                                confidence=0.8
                            ))

        # 低评分触发难度调整
        if event.rating and event.rating <= 2:
            actions.extend(await self._suggest_task_modifications(event))

        return actions

    async def _handle_difficulty_feedback(
        self,
        event: FeedbackEvent,
        difficulty: str
    ) -> list[AdjustmentAction]:
        """处理难度反馈"""
        actions = []

        if not event.task_id:
            return actions

        task = await self._get_task(event.task_id, event.user_id)
        if not task:
            return actions

        # 记录难度校准数据
        time_ratio = 1.0
        if event.actual_duration_minutes and task.estimated_minutes:
            time_ratio = event.actual_duration_minutes / task.estimated_minutes

        self.difficulty_calibrator.record(
            task_type=task.type.value,
            expected_difficulty=task.difficulty or 3,
            perceived_difficulty=difficulty,
            completion_time_ratio=time_ratio
        )

        # 查找并调整相似任务
        similar_tasks = await self._find_similar_pending_tasks(
            event.plan_id,
            task,
            event.user_id
        )

        if similar_tasks:
            adjustment = self.difficulty_calibrator.get_adjustment(task.type.value)
            if adjustment != 0:
                actions.append(AdjustmentAction(
                    action_type="adjust_difficulty",
                    target_task_ids=[t.id for t in similar_tasks],
                    parameters={
                        "difficulty_delta": adjustment,
                        "perceived_as": difficulty
                    },
                    reason=f"Difficulty calibration: {adjustment:+d} based on user feedback",
                    confidence=0.75
                ))

        return actions

    async def _handle_time_feedback(
        self,
        event: FeedbackEvent
    ) -> list[AdjustmentAction]:
        """处理时间估计反馈"""
        actions = []

        if not event.task_id or not event.actual_duration_minutes:
            return actions

        task = await self._get_task(event.task_id, event.user_id)
        if not task or not task.estimated_minutes:
            return actions

        # 记录时间校准数据
        self.time_calibrator.record(
            task_type=task.type.value,
            estimated=task.estimated_minutes,
            actual=event.actual_duration_minutes
        )

        # 查找相似任务并调整
        similar_tasks = await self._find_similar_pending_tasks(
            event.plan_id,
            task,
            event.user_id
        )

        if similar_tasks:
            adjustment_factor = self.time_calibrator.get_adjustment_factor(task.type.value)
            actions.append(AdjustmentAction(
                action_type="adjust_estimate",
                target_task_ids=[t.id for t in similar_tasks],
                parameters={"time_factor": adjustment_factor},
                reason=f"Time estimate calibration: {adjustment_factor:.2f}x",
                confidence=0.8
            ))

        return actions

    async def _handle_skip_similar(
        self,
        event: FeedbackEvent
    ) -> list[AdjustmentAction]:
        """处理跳过相似任务请求"""
        if not event.task_id:
            return []

        task = await self._get_task(event.task_id, event.user_id)
        if not task:
            return []

        # 查找相似待完成任务
        similar_tasks = await self._find_similar_pending_tasks(
            event.plan_id,
            task,
            event.user_id
        )

        if similar_tasks:
            return [AdjustmentAction(
                action_type="delete_task",
                target_task_ids=[t.id for t in similar_tasks],
                parameters={"reason": "user_skip_similar"},
                reason=f"User requested to skip {len(similar_tasks)} similar tasks",
                confidence=0.9
            )]

        return []

    async def _handle_topic_mastered(
        self,
        event: FeedbackEvent
    ) -> list[AdjustmentAction]:
        """处理主题已掌握反馈"""
        actions = []

        if not event.knowledge_nodes:
            return actions

        # 查找与这些知识节点相关的待完成任务
        related_tasks = await self._find_tasks_by_knowledge_nodes(
            event.plan_id,
            event.knowledge_nodes,
            event.user_id
        )

        if related_tasks:
            # 保留30%作为复习，删除其余
            actions.append(AdjustmentAction(
                action_type="reduce_tasks",
                target_task_ids=[t.id for t in related_tasks],
                parameters={
                    "keep_ratio": 0.3,
                    "prefer_harder": True
                },
                reason=f"Topic mastered: {', '.join(event.knowledge_nodes[:3])}",
                confidence=0.85
            ))

        return actions

    async def _suggest_task_modifications(
        self,
        event: FeedbackEvent
    ) -> list[AdjustmentAction]:
        """基于低评分建议任务修改"""
        actions = []

        if not event.task_id:
            return actions

        task = await self._get_task(event.task_id, event.user_id)
        if not task:
            return actions

        # 查找相似任务并降低难度
        similar_tasks = await self._find_similar_pending_tasks(
            event.plan_id,
            task,
            event.user_id
        )

        if similar_tasks and event.rating and event.rating <= 2:
            actions.append(AdjustmentAction(
                action_type="adjust_difficulty",
                target_task_ids=[t.id for t in similar_tasks],
                parameters={
                    "difficulty_delta": -1,
                    "reason": f"Low rating ({event.rating}/5) on similar task"
                },
                reason="Reducing difficulty due to low user rating",
                confidence=0.7
            ))

        return actions

    async def _apply_action(
        self,
        action: AdjustmentAction,
        user_id: UUID,
        plan_id: UUID
    ) -> bool:
        """应用调整动作到数据库"""
        try:
            if action.action_type == "delete_task":
                # 软删除任务
                for task_id in action.target_task_ids:
                    await self.db.execute(
                        update(Task)
                        .where(Task.id == task_id, Task.user_id == user_id)
                        .values(
                            deleted_at=datetime.utcnow(),
                            status=TaskStatus.ABANDONED.value
                        )
                    )
                await self.db.commit()

                # 更新 PlanState task_index
                await self.plan_state_service.upsert_plan_state(
                    user_id, plan_id,
                    patch={
                        "task_index": {
                            "total": {"$dec": len(action.target_task_ids)}
                        }
                    }
                )

            elif action.action_type == "adjust_estimate":
                # 调整时间估计
                factor = action.parameters.get("time_factor", 1.0)
                for task_id in action.target_task_ids:
                    task = await self._get_task(task_id, user_id)
                    if task and task.estimated_minutes:
                        new_estimate = max(5, int(task.estimated_minutes * factor))
                        await self.db.execute(
                            update(Task)
                            .where(Task.id == task_id, Task.user_id == user_id)
                            .values(estimated_minutes=new_estimate)
                        )
                await self.db.commit()

            elif action.action_type == "adjust_difficulty":
                # 调整难度
                delta = action.parameters.get("difficulty_delta", 0)
                for task_id in action.target_task_ids:
                    task = await self._get_task(task_id, user_id)
                    if task and task.difficulty is not None:
                        new_difficulty = max(1, min(5, task.difficulty + delta))
                        await self.db.execute(
                            update(Task)
                            .where(Task.id == task_id, Task.user_id == user_id)
                            .values(difficulty=new_difficulty)
                        )
                await self.db.commit()

            elif action.action_type == "reduce_tasks":
                # 减少任务数量（保留部分）
                keep_ratio = action.parameters.get("keep_ratio", 0.5)
                prefer_harder = action.parameters.get("prefer_harder", False)

                tasks = [await self._get_task(tid, user_id) for tid in action.target_task_ids]
                tasks = [t for t in tasks if t and t.status == TaskStatus.PENDING]

                if prefer_harder:
                    tasks.sort(key=lambda t: t.difficulty or 0, reverse=True)

                keep_count = max(1, int(len(tasks) * keep_ratio))
                tasks_to_delete = tasks[keep_count:]

                for task in tasks_to_delete:
                    await self.db.execute(
                        update(Task)
                        .where(Task.id == task.id, Task.user_id == user_id)
                        .values(deleted_at=datetime.utcnow(), status=TaskStatus.ABANDONED.value)
                    )
                await self.db.commit()

            logger.info(f"Applied action: {action.action_type} to {len(action.target_task_ids)} tasks")
            return True

        except Exception as e:
            logger.error(f"Failed to apply action {action.action_type}: {e}")
            await self.db.rollback()
            return False

    async def _record_feedback_with_actions(
        self,
        event: FeedbackEvent,
        actions: list[AdjustmentAction]
    ) -> None:
        """记录反馈和动作到 PlanState"""
        {
            **event.to_dict(),
            "applied_actions": [action.to_dict() for action in actions]
        }

        await self.plan_state_service.append_feedback(
            user_id=event.user_id,
            plan_id=event.plan_id,
            feedback_type=event.feedback_type.value,
            content=f"Applied {len(actions)} adjustments",
            task_id=event.task_id,
            applied_adjustment={"actions": [action.to_dict() for action in actions]}
        )

    # ==================== Helper Methods ====================

    async def _get_task(self, task_id: UUID, user_id: UUID) -> Task | None:
        """获取任务"""
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == user_id,
                Task.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def _find_similar_pending_tasks(
        self,
        plan_id: UUID,
        reference_task: Task,
        user_id: UUID
    ) -> list[Task]:
        """查找相似的待完成任务"""
        # 相似条件: 同一计划、同一类型、待完成
        result = await self.db.execute(
            select(Task).where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
                Task.type == reference_task.type,
                Task.status == TaskStatus.PENDING,
                Task.id != reference_task.id,
                Task.deleted_at.is_(None)
            ).order_by(Task.created_at).limit(10)
        )
        return list(result.scalars().all())

    async def _find_tasks_by_knowledge_nodes(
        self,
        plan_id: UUID,
        knowledge_nodes: list[str],
        user_id: UUID
    ) -> list[Task]:
        """查找与知识节点相关的任务"""
        # 通过 tags 字段查找（假设知识节点存储在 tags 中）
        result = await self.db.execute(
            select(Task).where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING,
                Task.deleted_at.is_(None)
            )
        )

        all_tasks = list(result.scalars().all())

        # 过滤包含相关知识节点的任务
        matching_tasks = []
        for task in all_tasks:
            task_tags = task.tags or {}
            task_nodes = task_tags.get("knowledge_nodes", [])
            if any(node in task_nodes for node in knowledge_nodes):
                matching_tasks.append(task)

        return matching_tasks
