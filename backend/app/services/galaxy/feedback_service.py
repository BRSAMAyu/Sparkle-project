"""
GalaxyFeedbackService - 知识星图反馈收集服务

负责收集用户学习行为的隐式反馈，实时更新知识节点掌握度
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import (
    KnowledgeNode, UserNodeStatus, ExpansionFeedback,
    StudyRecord
)
from app.core.event_bus import event_bus, NodeMasteryUpdatedEvent


class FeedbackType:
    """反馈类型"""
    TASK_COMPLETED = "task_completed"    # 任务完成: +0.8分
    ERROR_CREATED = "error_created"       # 错题: -0.3分
    STUDY_SESSION = "study_session"       # 学习时长: 基于时间
    QUIZ_PASSED = "quiz_passed"           # 测验通过: +1.0分
    QUIZ_FAILED = "quiz_failed"           # 测验失败: -0.5分


class GalaxyFeedbackService:
    """知识星图反馈收集服务

    处理用户学习行为产生的隐式反馈，并更新知识节点掌握度。

    反馈流程：
    1. 收集隐式反馈（任务完成、错题创建等）
    2. 计算反馈分数
    3. 记录到数据库
    4. 更新掌握度
    5. 发布掌握度更新事件
    """

    # 反馈分数配置
    FEEDBACK_SCORES = {
        FeedbackType.TASK_COMPLETED: 0.8,
        FeedbackType.ERROR_CREATED: -0.3,
        FeedbackType.QUIZ_PASSED: 1.0,
        FeedbackType.QUIZ_FAILED: -0.5,
    }

    # 掌握度范围
    MIN_MASTERY = 0
    MAX_MASTERY = 100

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client

    async def collect_implicit_feedback(
        self,
        event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        收集隐式反馈并更新掌握度

        Args:
            event_data: {
                "type": "task_completed" | "error_created" | "study_session" | "quiz_passed" | "quiz_failed",
                "user_id": UUID,
                "node_id": UUID,
                "task_id": Optional[UUID],
                "duration_minutes": Optional[int],
                "score": Optional[float],  # 对于quiz事件
            }

        Returns:
            更新结果: {"node_id": str, "old_mastery": int, "new_mastery": int, "delta": int}
        """
        event_type = event_data.get("type")
        user_id = event_data.get("user_id")
        node_id = event_data.get("node_id")

        if not all([event_type, user_id, node_id]):
            logger.warning(f"Missing required fields in event_data: {event_data}")
            return None

        # 计算反馈分数
        implicit_score = await self._calculate_feedback_score(event_data)

        # 记录反馈到数据库
        await self._record_feedback(
            user_id=user_id,
            node_id=node_id,
            feedback_type="implicit",
            implicit_score=implicit_score,
            source=event_type,
            metadata=event_data
        )

        # 更新掌握度
        result = await self._update_mastery_from_feedback(
            user_id=user_id,
            node_id=node_id,
            score=implicit_score,
            reason=f"implicit_feedback_{event_type}"
        )

        return result

    async def collect_explicit_feedback(
        self,
        user_id: UUID,
        node_id: UUID,
        rating: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        收集显式反馈（用户主动评分）

        Args:
            user_id: 用户ID
            node_id: 知识节点ID
            rating: 评分 (1-5)
            metadata: 额外的元数据

        Returns:
            更新结果
        """
        if not 1 <= rating <= 5:
            logger.warning(f"Invalid rating: {rating}, must be between 1-5")
            return None

        # 显式反馈分数：1-5 映射到 -2.0 到 +2.0
        explicit_score = (rating - 3) * 1.0

        # 记录反馈
        await self._record_feedback(
            user_id=user_id,
            node_id=node_id,
            feedback_type="explicit",
            rating=rating,
            implicit_score=explicit_score,
            source="user_rating",
            metadata=metadata
        )

        # 更新掌握度
        result = await self._update_mastery_from_feedback(
            user_id=user_id,
            node_id=node_id,
            score=explicit_score,
            reason=f"explicit_feedback_rating_{rating}"
        )

        return result

    async def _calculate_feedback_score(self, event_data: Dict[str, Any]) -> float:
        """计算反馈分数"""
        event_type = event_data.get("type")

        if event_type == FeedbackType.STUDY_SESSION:
            # 学习时长反馈：30分钟=1.0分
            duration = event_data.get("duration_minutes", 0)
            return min(duration / 30.0, 1.0)

        # 使用预定义分数
        return self.FEEDBACK_SCORES.get(event_type, 0.0)

    async def _record_feedback(
        self,
        user_id: UUID,
        node_id: UUID,
        feedback_type: str,
        implicit_score: float,
        source: str,
        rating: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ):
        """记录反馈到数据库"""
        try:
            feedback = ExpansionFeedback(
                user_id=user_id,
                trigger_node_id=node_id,
                feedback_type=feedback_type,
                implicit_score=implicit_score,
                rating=rating,
                meta_data={
                    "source": source,
                    **(metadata or {})
                }
            )
            self.db.add(feedback)
            await self.db.commit()

            logger.debug(
                f"Recorded feedback: user={user_id}, node={node_id}, "
                f"score={implicit_score}, source={source}"
            )
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            await self.db.rollback()

    async def _update_mastery_from_feedback(
        self,
        user_id: UUID,
        node_id: UUID,
        score: float,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """根据反馈更新掌握度"""
        try:
            # 获取当前状态
            query = select(UserNodeStatus).where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id == node_id
                )
            )
            result = await self.db.execute(query)
            status = result.scalar_one_or_none()

            if not status:
                # 创建新状态
                status = UserNodeStatus(
                    user_id=user_id,
                    node_id=node_id,
                    mastery_score=max(self.MIN_MASTERY, min(self.MAX_MASTERY, int(score * 10))),
                    is_unlocked=True,
                    first_unlock_at=datetime.utcnow(),
                    last_study_at=datetime.utcnow()
                )
                self.db.add(status)
                await self.db.commit()

                # 发布掌握度更新事件
                await self._publish_mastery_event(
                    user_id=user_id,
                    node_id=node_id,
                    old_mastery=0,
                    new_mastery=status.mastery_score,
                    reason=reason
                )

                return {
                    "node_id": str(node_id),
                    "old_mastery": 0,
                    "new_mastery": status.mastery_score,
                    "delta": status.mastery_score
                }

            old_mastery = status.mastery_score
            new_mastery = max(self.MIN_MASTERY, min(self.MAX_MASTERY, int(old_mastery + score * 10)))

            if new_mastery != old_mastery:
                status.mastery_score = new_mastery
                status.last_study_at = datetime.utcnow()
                await self.db.commit()

                # 发布掌握度更新事件
                await self._publish_mastery_event(
                    user_id=user_id,
                    node_id=node_id,
                    old_mastery=old_mastery,
                    new_mastery=new_mastery,
                    reason=reason
                )

                return {
                    "node_id": str(node_id),
                    "old_mastery": old_mastery,
                    "new_mastery": new_mastery,
                    "delta": new_mastery - old_mastery
                }

        except Exception as e:
            logger.error(f"Failed to update mastery from feedback: {e}")
            await self.db.rollback()

        return None

    async def _publish_mastery_event(
        self,
        user_id: UUID,
        node_id: UUID,
        old_mastery: float,
        new_mastery: float,
        reason: str
    ):
        """发布掌握度更新事件到事件总线"""
        try:
            event = NodeMasteryUpdatedEvent(
                user_id=str(user_id),
                node_id=str(node_id),
                old_mastery=int(old_mastery),
                new_mastery=int(new_mastery),
                reason=reason
            )
            await event_bus.publish("node_mastery_updated", event.to_dict())
            logger.debug(f"Published mastery update event: user={user_id}, node={node_id}")
        except Exception as e:
            logger.error(f"Failed to publish mastery update event: {e}")

    async def batch_update_from_task(
        self,
        user_id: UUID,
        node_ids: List[UUID],
        task_id: UUID,
        study_minutes: int,
        difficulty: int
    ) -> List[Dict[str, Any]]:
        """
        批量更新多个节点的掌握度（任务完成时）

        Args:
            user_id: 用户ID
            node_ids: 关联的知识节点ID列表
            task_id: 任务ID
            study_minutes: 学习时长（分钟）
            difficulty: 任务难度 (1-5)

        Returns:
            更新结果列表
        """
        results = []

        for node_id in node_ids:
            try:
                # 使用 GalaxyStatsService 的 spark_node 方法进行正式更新
                from app.services.galaxy.stats_service import GalaxyStatsService
                stats_service = GalaxyStatsService(self.db)

                spark_result = await stats_service.spark_node(
                    user_id=user_id,
                    node_id=node_id,
                    study_minutes=study_minutes,
                    task_id=task_id,
                    trigger_expansion=True
                )

                results.append({
                    "node_id": str(node_id),
                    "old_mastery": spark_result.spark_event.old_mastery,
                    "new_mastery": spark_result.spark_event.new_mastery,
                    "delta": spark_result.spark_event.new_mastery - spark_result.spark_event.old_mastery
                })

            except Exception as e:
                logger.error(f"Failed to update node {node_id} from task: {e}")

        return results

    async def get_feedback_summary(
        self,
        user_id: UUID,
        node_id: UUID
    ) -> Dict[str, Any]:
        """
        获取节点反馈摘要

        Args:
            user_id: 用户ID
            node_id: 知识节点ID

        Returns:
            反馈摘要统计
        """
        from sqlalchemy import func

        query = select(
            func.count().label('total_count'),
            func.avg(ExpansionFeedback.implicit_score).label('avg_implicit_score'),
            func.avg(ExpansionFeedback.rating).label('avg_rating')
        ).where(
            and_(
                ExpansionFeedback.user_id == user_id,
                ExpansionFeedback.trigger_node_id == node_id
            )
        )

        result = await self.db.execute(query)
        row = result.one_or_none()

        if row and row.total_count > 0:
            return {
                "total_count": row.total_count,
                "avg_implicit_score": float(row.avg_implicit_score or 0),
                "avg_rating": float(row.avg_rating or 0)
            }

        return {
            "total_count": 0,
            "avg_implicit_score": 0.0,
            "avg_rating": 0.0
        }
