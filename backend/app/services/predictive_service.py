"""
Predictive Learning Intelligence Service - 预测学习智能服务

功能：
- 参与度预测：预测用户下次活跃时间
- 难度预测：预测某话题对用户的难度
- 最佳学习时间推荐
- 辍学风险检测
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger
import statistics

from app.models.galaxy import UserNodeStatus, KnowledgeNode
from app.models.user import User
from app.models.tasks import Task
from app.models.study_records import StudyRecord


class EngagementForecast:
    """参与度预测结果"""
    def __init__(
        self,
        next_active_time: datetime,
        confidence: float,
        recommended_intervention: Optional[str] = None,
        risk_level: str = "low"
    ):
        self.next_active_time = next_active_time
        self.confidence = confidence
        self.recommended_intervention = recommended_intervention
        self.risk_level = risk_level

    def to_dict(self):
        return {
            "next_active_time": self.next_active_time.isoformat(),
            "confidence": self.confidence,
            "recommended_intervention": self.recommended_intervention,
            "risk_level": self.risk_level
        }


class DifficultyPrediction:
    """难度预测结果"""
    def __init__(
        self,
        topic_id: UUID,
        topic_name: str,
        predicted_difficulty: float,  # 0-1
        suggested_prerequisites: List[str],
        estimated_time_hours: float
    ):
        self.topic_id = topic_id
        self.topic_name = topic_name
        self.predicted_difficulty = predicted_difficulty
        self.suggested_prerequisites = suggested_prerequisites
        self.estimated_time_hours = estimated_time_hours

    def to_dict(self):
        return {
            "topic_id": str(self.topic_id),
            "topic_name": self.topic_name,
            "predicted_difficulty": round(self.predicted_difficulty, 2),
            "difficulty_level": self._get_difficulty_level(),
            "suggested_prerequisites": self.suggested_prerequisites,
            "estimated_time_hours": round(self.estimated_time_hours, 1)
        }

    def _get_difficulty_level(self) -> str:
        if self.predicted_difficulty < 0.3:
            return "easy"
        elif self.predicted_difficulty < 0.7:
            return "medium"
        else:
            return "hard"


class PredictiveService:
    """预测学习智能服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict_engagement(self, user_id: UUID) -> EngagementForecast:
        """
        预测用户下次参与时间

        分析因素：
        1. 一周内的活跃模式（星期几、时间段）
        2. 最近会话间隔
        3. 任务完成率
        4. 掌握度速度

        简化版本：基于历史平均间隔 + 时间模式
        """
        try:
            now = datetime.now(timezone.utc)

            # 1. 获取最近30天的学习记录
            query = (
                select(StudyRecord)
                .where(
                    and_(
                        StudyRecord.user_id == user_id,
                        StudyRecord.created_at >= now - timedelta(days=30)
                    )
                )
                .order_by(StudyRecord.created_at.desc())
            )
            result = await self.db.execute(query)
            recent_records = result.scalars().all()

            if len(recent_records) < 2:
                # 数据不足，返回默认预测
                return EngagementForecast(
                    next_active_time=now + timedelta(days=1),
                    confidence=0.3,
                    recommended_intervention="用户数据不足，建议发送欢迎消息",
                    risk_level="unknown"
                )

            # 2. 计算会话间隔
            intervals = []
            for i in range(len(recent_records) - 1):
                interval = (recent_records[i].created_at - recent_records[i + 1].created_at).total_seconds() / 3600
                intervals.append(interval)

            avg_interval_hours = statistics.mean(intervals) if intervals else 24
            std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 12

            # 3. 分析时间模式（星期几、时间段）
            weekday_pattern = self._analyze_weekday_pattern(recent_records)
            hour_pattern = self._analyze_hour_pattern(recent_records)

            # 4. 预测下次活跃时间
            # 基础：从最后一次活动开始 + 平均间隔
            last_activity = recent_records[0].created_at
            predicted_time = last_activity + timedelta(hours=avg_interval_hours)

            # 调整到最常见的星期和时间
            predicted_time = self._adjust_to_pattern(
                predicted_time,
                weekday_pattern,
                hour_pattern
            )

            # 5. 计算置信度
            # 基于间隔的稳定性
            confidence = max(0.5, 1.0 - (std_interval / avg_interval_hours))
            confidence = min(confidence, 0.95)  # 最高95%

            # 6. 辍学风险检测
            hours_since_last = (now - last_activity).total_seconds() / 3600
            risk_level = "low"
            intervention = None

            if hours_since_last > avg_interval_hours * 2:
                risk_level = "high"
                intervention = "用户活跃度下降，建议发送激励消息"
            elif hours_since_last > avg_interval_hours * 1.5:
                risk_level = "medium"
                intervention = "可以发送学习提醒"

            return EngagementForecast(
                next_active_time=predicted_time,
                confidence=confidence,
                recommended_intervention=intervention,
                risk_level=risk_level
            )

        except Exception as e:
            logger.error(f"参与度预测失败: {e}")
            return EngagementForecast(
                next_active_time=datetime.now(timezone.utc) + timedelta(days=1),
                confidence=0.0,
                recommended_intervention="预测失败",
                risk_level="unknown"
            )

    def _analyze_weekday_pattern(self, records: List[StudyRecord]) -> Dict[int, int]:
        """分析星期模式 (0=Monday, 6=Sunday)"""
        pattern = {i: 0 for i in range(7)}
        for record in records:
            weekday = record.created_at.weekday()
            pattern[weekday] += 1
        return pattern

    def _analyze_hour_pattern(self, records: List[StudyRecord]) -> Dict[int, int]:
        """分析小时模式 (0-23)"""
        pattern = {i: 0 for i in range(24)}
        for record in records:
            hour = record.created_at.hour
            pattern[hour] += 1
        return pattern

    def _adjust_to_pattern(
        self,
        predicted_time: datetime,
        weekday_pattern: Dict[int, int],
        hour_pattern: Dict[int, int]
    ) -> datetime:
        """根据模式调整预测时间"""
        # 找到最常见的星期和时间
        most_common_weekday = max(weekday_pattern, key=weekday_pattern.get)
        most_common_hour = max(hour_pattern, key=hour_pattern.get)

        # 调整到最常见的星期
        current_weekday = predicted_time.weekday()
        if current_weekday != most_common_weekday:
            days_diff = (most_common_weekday - current_weekday) % 7
            predicted_time += timedelta(days=days_diff)

        # 调整到最常见的小时
        predicted_time = predicted_time.replace(
            hour=most_common_hour,
            minute=0,
            second=0
        )

        return predicted_time

    async def predict_difficulty(
        self,
        user_id: UUID,
        topic_id: UUID
    ) -> DifficultyPrediction:
        """
        预测话题难度

        分析因素：
        1. 前置知识掌握度
        2. 类似话题的表现
        3. 话题的平均难度（基于所有用户）

        简化版本：基于前置知识完成度
        """
        try:
            # 1. 获取话题信息
            topic_query = select(KnowledgeNode).where(KnowledgeNode.id == topic_id)
            topic_result = await self.db.execute(topic_query)
            topic = topic_result.scalar_one_or_none()

            if not topic:
                raise ValueError(f"Topic {topic_id} not found")

            # 2. 查找前置知识
            # 简化：假设 importance 高的节点是前置知识
            prerequisite_query = (
                select(KnowledgeNode)
                .where(
                    and_(
                        KnowledgeNode.subject_id == topic.subject_id,
                        KnowledgeNode.importance > topic.importance
                    )
                )
            )
            prereq_result = await self.db.execute(prerequisite_query)
            prerequisites = prereq_result.scalars().all()

            # 3. 检查用户的前置知识掌握度
            prerequisite_names = []
            prerequisite_mastery = []

            for prereq in prerequisites[:5]:  # 最多5个前置
                status_query = select(UserNodeStatus).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.node_id == prereq.id
                    )
                )
                status_result = await self.db.execute(status_query)
                status = status_result.scalar_one_or_none()

                if status:
                    prerequisite_mastery.append(status.mastery_score)
                    if status.mastery_score < 60:
                        prerequisite_names.append(prereq.name)
                else:
                    prerequisite_names.append(prereq.name)
                    prerequisite_mastery.append(0)

            # 4. 计算预测难度
            # 0-1 scale
            if prerequisite_mastery:
                avg_prereq_mastery = statistics.mean(prerequisite_mastery)
                # 前置知识掌握度越低，难度越高
                predicted_difficulty = 1.0 - (avg_prereq_mastery / 100.0)
            else:
                # 没有前置知识，中等难度
                predicted_difficulty = 0.5

            # 5. 估算学习时间
            # 基于难度和话题重要性
            base_hours = topic.importance * 2  # 重要性 1-10 -> 2-20小时
            difficulty_multiplier = 1.0 + predicted_difficulty
            estimated_hours = base_hours * difficulty_multiplier

            return DifficultyPrediction(
                topic_id=topic_id,
                topic_name=topic.name,
                predicted_difficulty=predicted_difficulty,
                suggested_prerequisites=prerequisite_names,
                estimated_time_hours=estimated_hours
            )

        except Exception as e:
            logger.error(f"难度预测失败: {e}")
            # 返回默认中等难度
            return DifficultyPrediction(
                topic_id=topic_id,
                topic_name="Unknown",
                predicted_difficulty=0.5,
                suggested_prerequisites=[],
                estimated_time_hours=10.0
            )

    async def recommend_optimal_time(self, user_id: UUID) -> Dict[str, Any]:
        """
        推荐最佳学习时间

        基于历史学习效果（掌握度提升最快的时间段）
        """
        try:
            now = datetime.now(timezone.utc)

            # 获取最近30天的学习记录
            query = (
                select(StudyRecord)
                .where(
                    and_(
                        StudyRecord.user_id == user_id,
                        StudyRecord.created_at >= now - timedelta(days=30)
                    )
                )
            )
            result = await self.db.execute(query)
            records = result.scalars().all()

            if not records:
                return {
                    "recommended_hours": [9, 14, 19],  # 默认：早中晚
                    "recommended_weekdays": [1, 2, 3, 4],  # 周二到周五
                    "reason": "默认推荐（数据不足）"
                }

            # 分析各时间段的学习效果
            hour_performance = {i: [] for i in range(24)}
            weekday_performance = {i: [] for i in range(7)}

            for record in records:
                hour = record.created_at.hour
                weekday = record.created_at.weekday()

                # 假设 duration 和 mastery_gain 字段存在
                performance_score = getattr(record, 'mastery_gain', 1.0)

                hour_performance[hour].append(performance_score)
                weekday_performance[weekday].append(performance_score)

            # 找到表现最好的3个小时
            avg_hour_performance = {
                hour: statistics.mean(scores) if scores else 0
                for hour, scores in hour_performance.items()
            }
            best_hours = sorted(
                avg_hour_performance.keys(),
                key=lambda h: avg_hour_performance[h],
                reverse=True
            )[:3]

            # 找到表现最好的星期
            avg_weekday_performance = {
                day: statistics.mean(scores) if scores else 0
                for day, scores in weekday_performance.items()
            }
            best_weekdays = sorted(
                avg_weekday_performance.keys(),
                key=lambda d: avg_weekday_performance[d],
                reverse=True
            )[:4]

            return {
                "recommended_hours": best_hours,
                "recommended_weekdays": best_weekdays,
                "hour_performance": avg_hour_performance,
                "weekday_performance": avg_weekday_performance,
                "reason": "基于最近30天的学习效果分析"
            }

        except Exception as e:
            logger.error(f"最佳时间推荐失败: {e}")
            return {
                "recommended_hours": [9, 14, 19],
                "recommended_weekdays": [1, 2, 3, 4],
                "reason": f"推荐失败: {str(e)}"
            }

    async def detect_dropout_risk(self, user_id: UUID) -> Dict[str, Any]:
        """
        辍学风险检测

        风险指标：
        1. 最近活跃度下降
        2. 任务完成率低
        3. 学习时长减少
        4. 掌握度增长缓慢
        """
        try:
            now = datetime.now(timezone.utc)

            # 1. 最近活跃度
            recent_7d_query = select(func.count(StudyRecord.id)).where(
                and_(
                    StudyRecord.user_id == user_id,
                    StudyRecord.created_at >= now - timedelta(days=7)
                )
            )
            recent_7d_result = await self.db.execute(recent_7d_query)
            recent_7d_count = recent_7d_result.scalar() or 0

            previous_7d_query = select(func.count(StudyRecord.id)).where(
                and_(
                    StudyRecord.user_id == user_id,
                    StudyRecord.created_at >= now - timedelta(days=14),
                    StudyRecord.created_at < now - timedelta(days=7)
                )
            )
            previous_7d_result = await self.db.execute(previous_7d_query)
            previous_7d_count = previous_7d_result.scalar() or 0

            # 活跃度变化
            if previous_7d_count > 0:
                activity_change = (recent_7d_count - previous_7d_count) / previous_7d_count
            else:
                activity_change = 0.0

            # 2. 任务完成率
            incomplete_tasks_query = select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status != "completed",
                    Task.created_at >= now - timedelta(days=14)
                )
            )
            incomplete_result = await self.db.execute(incomplete_tasks_query)
            incomplete_count = incomplete_result.scalar() or 0

            total_tasks_query = select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.created_at >= now - timedelta(days=14)
                )
            )
            total_result = await self.db.execute(total_tasks_query)
            total_count = total_result.scalar() or 0

            completion_rate = (
                (total_count - incomplete_count) / total_count
                if total_count > 0
                else 0.5
            )

            # 3. 计算风险分数 (0-100)
            risk_score = 0

            # 活跃度下降 (40分)
            if activity_change < -0.5:
                risk_score += 40
            elif activity_change < -0.2:
                risk_score += 20

            # 任务完成率低 (30分)
            if completion_rate < 0.3:
                risk_score += 30
            elif completion_rate < 0.6:
                risk_score += 15

            # 最近无活动 (30分)
            if recent_7d_count == 0:
                risk_score += 30
            elif recent_7d_count < 3:
                risk_score += 10

            # 确定风险等级
            if risk_score >= 60:
                risk_level = "high"
                recommendation = "强烈建议发送激励消息或个性化学习建议"
            elif risk_score >= 30:
                risk_level = "medium"
                recommendation = "发送学习提醒和进度总结"
            else:
                risk_level = "low"
                recommendation = "保持当前节奏，定期鼓励"

            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "recommendation": recommendation,
                "metrics": {
                    "activity_change_percent": round(activity_change * 100, 1),
                    "completion_rate_percent": round(completion_rate * 100, 1),
                    "recent_7d_activities": recent_7d_count,
                    "previous_7d_activities": previous_7d_count
                }
            }

        except Exception as e:
            logger.error(f"辍学风险检测失败: {e}")
            return {
                "risk_score": 0,
                "risk_level": "unknown",
                "recommendation": "检测失败",
                "metrics": {}
            }
