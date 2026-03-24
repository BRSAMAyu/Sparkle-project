"""
Predictive Learning Intelligence Service - 预测学习智能服务

功能：
- 参与度预测：预测用户下次活跃时间
- 难度预测：预测某话题对用户的难度
- 最佳学习时间推荐
- 辍学风险检测
"""
from __future__ import annotations

import asyncio
import json
import statistics
from collections import defaultdict
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.cache import cache_service
from app.core.llm_router import llm_router
from app.config import settings
from app.models.candidate_action_feedback import CandidateActionFeedback
from app.models.event import TrackingEvent
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus
from app.services.llm_service import get_llm_service_for_specific_model
from app.tools.entity_cards import build_prediction_entity_card


class EngagementForecast:
    """参与度预测结果"""
    def __init__(
        self,
        next_active_time: datetime,
        confidence: float,
        recommended_intervention: str | None = None,
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
        suggested_prerequisites: list[str],
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
    LONG_HORIZON_CACHE_TTL_SECONDS = 60 * 60 * 6
    LONG_HORIZON_SOFT_STALE_SECONDS = 60 * 30
    REALTIME_FREE_TIMEOUT_SECONDS = 0.25
    REALTIME_FREE_FAST_TIMEOUT_SECONDS = 0.45
    REALTIME_FAST_TIMEOUT_SECONDS = 2.2

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _get_current_time() -> datetime:
        return datetime.now(timezone.utc)

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
            now = self._get_current_time().replace(tzinfo=None)

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
                next_active_time=self._get_current_time().replace(tzinfo=None) + timedelta(days=1),
                confidence=0.0,
                recommended_intervention="预测失败",
                risk_level="unknown"
            )

    def _analyze_weekday_pattern(self, records: list[StudyRecord]) -> dict[int, int]:
        """分析星期模式 (0=Monday, 6=Sunday)"""
        pattern = dict.fromkeys(range(7), 0)
        for record in records:
            weekday = record.created_at.weekday()
            pattern[weekday] += 1
        return pattern

    def _analyze_hour_pattern(self, records: list[StudyRecord]) -> dict[int, int]:
        """分析小时模式 (0-23)"""
        pattern = dict.fromkeys(range(24), 0)
        for record in records:
            hour = record.created_at.hour
            pattern[hour] += 1
        return pattern

    def _adjust_to_pattern(
        self,
        predicted_time: datetime,
        weekday_pattern: dict[int, int],
        hour_pattern: dict[int, int]
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

    async def recommend_optimal_time(self, user_id: UUID) -> dict[str, Any]:
        """
        推荐最佳学习时间

        基于历史学习效果（掌握度提升最快的时间段）
        """
        try:
            now = self._get_current_time().replace(tzinfo=None)

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
                    "best_hours": [9, 14, 19],  # 默认：早中晚
                    "best_weekdays": [1, 2, 3, 4],  # 周二到周五
                    "performance_by_hour": {str(hour): 0.0 for hour in range(24)},
                    "performance_by_weekday": {str(day): 0.0 for day in range(7)},
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
                "best_hours": best_hours,
                "best_weekdays": best_weekdays,
                "performance_by_hour": avg_hour_performance,
                "performance_by_weekday": avg_weekday_performance,
                "reason": "基于最近30天的学习效果分析"
            }

        except Exception as e:
            logger.error(f"最佳时间推荐失败: {e}")
            return {
                "best_hours": [9, 14, 19],
                "best_weekdays": [1, 2, 3, 4],
                "performance_by_hour": {str(hour): 0.0 for hour in range(24)},
                "performance_by_weekday": {str(day): 0.0 for day in range(7)},
                "reason": f"推荐失败: {str(e)}"
            }

    async def detect_dropout_risk(self, user_id: UUID) -> dict[str, Any]:
        """
        辍学风险检测

        风险指标：
        1. 最近活跃度下降
        2. 任务完成率低
        3. 学习时长减少
        4. 掌握度增长缓慢
        """
        try:
            now = self._get_current_time().replace(tzinfo=None)

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
                    Task.status != TaskStatus.COMPLETED,
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

    async def get_next_intent_forecast(self, user_id: UUID) -> dict[str, Any]:
        cache_key = f"predictive:next_intent:{user_id}"
        cached = await self._get_cached_forecast(cache_key)
        if cached is not None:
            return cached

        rule_based = self._finalize_prediction(
            user_id=user_id,
            forecast=await self._build_rule_based_next_intent(user_id),
            horizon="long_horizon",
            source="rules",
            tier="rules",
            fallback_used=True,
            surface="dashboard",
        )
        await self._cache_forecast(
            cache_key,
            rule_based,
            ttl_seconds=self.LONG_HORIZON_SOFT_STALE_SECONDS,
        )
        await self._schedule_long_horizon_refresh(user_id)
        return rule_based

    async def get_realtime_next_step_forecast(
        self,
        user_id: UUID,
        *,
        partial_text: str,
        active_plan_id: str | None = None,
        surface: str = "chat_input",
    ) -> dict[str, Any]:
        normalized_text = partial_text.strip()
        base = await self._build_rule_based_realtime_next_step(
            user_id,
            partial_text=normalized_text,
            active_plan_id=active_plan_id,
            surface=surface,
        )

        if len(normalized_text) < 3:
            return base

        forecast = await self._generate_realtime_llm_prediction(
            user_id,
            partial_text=normalized_text,
            base=base,
            surface=surface,
        )
        if forecast is not None:
            return forecast
        return base

    async def generate_long_horizon_forecast(self, user_id: UUID) -> dict[str, Any]:
        base = await self._build_rule_based_next_intent(user_id)
        model_candidates, route_reason = self._select_long_horizon_model_chain(base.get("signals", {}))
        messages = self._build_long_horizon_messages(base)

        try:
            for model_key in model_candidates:
                try:
                    llm = await get_llm_service_for_specific_model(
                        model_key,
                        agent_role=AgentRole.GENERATION,
                    )
                    payload = await self._request_prediction_payload(
                        llm=llm,
                        messages=messages,
                        temperature=0.2,
                    )
                    merged = self._merge_prediction_payload(base, payload)
                    if merged is None:
                        logger.info(
                            f"Long horizon model returned no usable payload for user {user_id}: {model_key}"
                        )
                        continue

                    enriched = self._finalize_prediction(
                        user_id=user_id,
                        forecast=merged,
                        horizon="long_horizon",
                        source="glm_batch",
                        tier=model_key,
                        fallback_used=False,
                        surface="dashboard",
                    )
                    await self._cache_forecast(
                        f"predictive:next_intent:{user_id}",
                        enriched,
                        ttl_seconds=self.LONG_HORIZON_CACHE_TTL_SECONDS,
                    )
                    logger.info(
                        f"Long horizon prediction ready for user {user_id}: "
                        f"model={model_key}, route={route_reason}"
                    )
                    return enriched
                except Exception as exc:
                    logger.warning(
                        f"Long horizon model attempt failed for user {user_id}: "
                        f"model={model_key}, route={route_reason}, error={exc}"
                    )
        except Exception as exc:
            logger.warning(f"Long horizon prediction failed for user {user_id}: {exc}")

        fallback = self._finalize_prediction(
            user_id=user_id,
            forecast=base,
            horizon="long_horizon",
            source="rules",
            tier="rules",
            fallback_used=True,
            surface="dashboard",
        )
        await self._cache_forecast(
            f"predictive:next_intent:{user_id}",
            fallback,
            ttl_seconds=self.LONG_HORIZON_CACHE_TTL_SECONDS,
        )
        return fallback

    async def _build_rule_based_next_intent(self, user_id: UUID) -> dict[str, Any]:
        now = self._get_current_time().replace(tzinfo=None)
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        pending_stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
            .order_by(Task.priority.desc(), Task.due_date, Task.created_at.desc())
            .limit(5)
        )
        pending_tasks = (await self.db.execute(pending_stmt)).scalars().all()

        completed_stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= last_24h,
        )
        completed_last_24h = int((await self.db.execute(completed_stmt)).scalar() or 0)

        focus_stmt = select(FocusSession).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= last_24h,
            FocusSession.status == FocusStatus.COMPLETED,
        )
        focus_sessions = (await self.db.execute(focus_stmt)).scalars().all()
        total_focus_minutes = sum(int(session.duration_minutes or 0) for session in focus_sessions)

        study_stmt = select(func.count(StudyRecord.id)).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= last_24h,
        )
        study_count = int((await self.db.execute(study_stmt)).scalar() or 0)
        study_7d_stmt = select(func.count(StudyRecord.id)).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= last_7d,
        )
        study_count_7d = int((await self.db.execute(study_7d_stmt)).scalar() or 0)

        top_task = pending_tasks[0] if pending_tasks else None
        overdue_count = sum(
            1
            for task in pending_tasks
            if task.due_date is not None and task.due_date < now.date()
        )

        if top_task is not None:
            reasons = [
                f"当前最高优先级待办是「{top_task.title}」",
                f"最近24小时已完成 {completed_last_24h} 个任务",
            ]
            if total_focus_minutes > 0:
                reasons.append(f"最近24小时专注了 {total_focus_minutes} 分钟")
            if overdue_count > 0:
                reasons.append(f"还有 {overdue_count} 个任务已逾期")
            forecast = {
                "title": "系统预测你接下来最想推进当前重点任务",
                "summary": f"建议直接回到「{top_task.title}」，先推进一个 25 分钟小段。",
                "confidence": 0.78 if int(top_task.priority or 0) >= 2 else 0.68,
                "predicted_action_type": "resume_priority_task",
                "predicted_window": "next_2h",
                "reasons": reasons,
                "suggested_prompt": f"帮我继续推进任务：{top_task.title}",
                "signals": {
                    "top_task_title": top_task.title,
                    "top_task_priority": int(top_task.priority or 0),
                    "pending_task_count": len(pending_tasks),
                    "overdue_count": overdue_count,
                    "completed_last_24h": completed_last_24h,
                    "focus_minutes_last_24h": total_focus_minutes,
                    "study_records_last_24h": study_count,
                    "study_records_last_7d": study_count_7d,
                },
                "explanations": {
                    "recent_24h": [
                        f"最近24小时完成了 {completed_last_24h} 个任务",
                        f"最近24小时专注了 {total_focus_minutes} 分钟",
                    ],
                    "recent_7d": [
                        f"最近7天累计留下了 {study_count_7d} 条学习记录",
                    ],
                    "profile": ["你最近更像在推进已有任务，而不是重新开新坑"],
                    "plan": [
                        f"当前还有 {len(pending_tasks)} 个待办未完成",
                        *([f"其中 {overdue_count} 个已经逾期"] if overdue_count > 0 else []),
                    ],
                    "focus": [
                        "先推进 25 分钟的小段，比直接做大块任务更容易进入状态",
                    ],
                },
            }
        else:
            forecast = {
                "title": "系统预测你接下来更适合做一次轻量复盘",
                "summary": "当前没有强约束待办，先用 10 分钟整理思路，会更容易进入下一轮行动。",
                "confidence": 0.61,
                "predicted_action_type": "light_review",
                "predicted_window": "next_6h",
                "reasons": [
                    f"最近24小时已完成 {completed_last_24h} 个任务",
                    f"最近24小时专注 {total_focus_minutes} 分钟",
                    f"最近24小时学习记录 {study_count} 条",
                ],
                "suggested_prompt": "帮我做一个 10 分钟轻量复盘，并建议下一步行动",
                "signals": {
                    "pending_task_count": len(pending_tasks),
                    "completed_last_24h": completed_last_24h,
                    "focus_minutes_last_24h": total_focus_minutes,
                    "study_records_last_24h": study_count,
                    "study_records_last_7d": study_count_7d,
                },
                "explanations": {
                    "recent_24h": [
                        f"最近24小时完成了 {completed_last_24h} 个任务",
                        f"最近24小时专注了 {total_focus_minutes} 分钟",
                    ],
                    "recent_7d": [
                        f"最近7天累计留下了 {study_count_7d} 条学习记录",
                    ],
                    "profile": ["你当前没有被高优先级任务强绑定，适合先整理节奏"],
                    "plan": ["当前没有明确的最高优先级待办需要立刻承接"],
                    "focus": ["短复盘能帮助系统更准确地给出下一步建议"],
                },
            }

        return forecast

    async def _build_rule_based_realtime_next_step(
        self,
        user_id: UUID,
        *,
        partial_text: str,
        active_plan_id: str | None,
        surface: str,
    ) -> dict[str, Any]:
        now = self._get_current_time().replace(tzinfo=None)
        normalized = partial_text.strip()
        lowered = normalized.lower()
        last_24h = now - timedelta(hours=24)

        pending_stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
            .order_by(Task.priority.desc(), Task.due_date, Task.created_at.desc())
            .limit(3)
        )
        pending_tasks = (await self.db.execute(pending_stmt)).scalars().all()
        top_task = pending_tasks[0] if pending_tasks else None

        focus_stmt = select(func.count(FocusSession.id)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= last_24h,
            FocusSession.status == FocusStatus.COMPLETED,
        )
        focus_count_last_24h = int((await self.db.execute(focus_stmt)).scalar() or 0)

        action_type = "continue_chat"
        title = "系统预测你接下来会继续让 AI 帮你推进这件事"
        summary = "这句话更像是一个需要立刻承接的意图，继续让 AI 帮你收束成下一步最省力。"
        suggested_prompt = normalized
        reasons = ["你正在连续输入，当前最需要的是立刻给出下一步动作"]
        confidence = 0.66
        primary_route = "/chat"

        if any(keyword in normalized for keyword in ["任务", "待办", "提醒", "todo", "task"]):
            action_type = "create_task"
            title = "系统预测你想先把这件事落成任务"
            summary = "这段输入更像一个可执行待办，直接落到任务列表会更容易继续推进。"
            suggested_prompt = normalized
            reasons = ["输入里出现了明确的任务/提醒语义"]
            confidence = 0.82
            primary_route = "/tasks/new"
        elif any(keyword in normalized for keyword in ["计划", "学习路径", "复习", "学", "study", "plan"]):
            action_type = "study_plan"
            title = "系统预测你想把它收成一个学习计划"
            summary = "当前输入更像在请求结构化规划，先收成计划会比直接闲聊更高效。"
            suggested_prompt = normalized if normalized else "请帮我制定一个可执行的学习计划"
            reasons = ["输入里有明显的规划/学习语义"]
            confidence = 0.78
        elif any(keyword in lowered for keyword in ["why", "error", "bug", "报错", "为什么", "问题", "错题"]):
            action_type = "error_diagnosis"
            title = "系统预测你接下来想做一次问题诊断"
            summary = "这更像是在定位问题根因，直接进入诊断型回答会更省时间。"
            suggested_prompt = normalized
            reasons = ["输入里出现了问题定位或报错语义"]
            confidence = 0.8
        elif any(keyword in normalized for keyword in ["翻译", "单词", "英文", "translate"]):
            action_type = "translate"
            title = "系统预测你接下来想要一个即时语言结果"
            summary = "这是时效性很强的即时需求，直接拿到结果比展开讨论更重要。"
            suggested_prompt = normalized
            reasons = ["输入里出现了翻译/语言学习语义"]
            confidence = 0.77
        elif top_task is not None and len(normalized) < 10:
            action_type = "resume_task"
            title = "系统预测你想继续当前重点任务"
            summary = f"你最近仍在围绕「{top_task.title}」推进，系统建议直接承接这条主线。"
            suggested_prompt = f"帮我继续推进任务：{top_task.title}"
            reasons = [f"当前最高优先级待办仍是「{top_task.title}」"]
            confidence = 0.72

        explanations = {
            "recent_24h": [
                f"最近24小时你完成了 {focus_count_last_24h} 次完整专注",
            ],
            "recent_7d": [
                f"当前仍有 {len(pending_tasks)} 个任务处于待推进状态",
            ],
            "profile": [
                "系统会优先把你的输入推向最省力、最容易继续行动的路径",
            ],
            "plan": [
                *([f"当前活跃计划 ID：{active_plan_id}"] if active_plan_id else []),
                *([f"最近最需要推进的任务是「{top_task.title}」"] if top_task else []),
            ],
            "focus": [
                "实时预测更看重 5 秒内可执行的下一步，而不是复杂分析",
            ],
        }

        return self._finalize_prediction(
            user_id=user_id,
            forecast={
                "title": title,
                "summary": summary,
                "confidence": confidence,
                "predicted_action_type": action_type,
                "predicted_window": "now",
                "reasons": reasons,
                "suggested_prompt": suggested_prompt,
                "signals": {
                    "active_plan_id": active_plan_id,
                    "surface": surface,
                    "input_text": normalized,
                    "pending_task_count": len(pending_tasks),
                    "focus_sessions_last_24h": focus_count_last_24h,
                    "top_task_title": top_task.title if top_task else None,
                },
                "explanations": explanations,
                "primary_route": primary_route,
            },
            horizon="realtime",
            source="rules",
            tier="rules",
            fallback_used=True,
            surface=surface,
        )

    async def _generate_realtime_llm_prediction(
        self,
        user_id: UUID,
        *,
        partial_text: str,
        base: dict[str, Any],
        surface: str,
    ) -> dict[str, Any] | None:
        messages = self._build_realtime_llm_messages(partial_text=partial_text, base=base)

        async def _attempt(
            model_key: str,
            *,
            source_tier: ModelTier,
            timeout_seconds: float,
        ) -> dict[str, Any] | None:
            llm = await get_llm_service_for_specific_model(
                model_key,
                agent_role=AgentRole.GENERATION,
            )
            payload = await self._request_prediction_payload(
                llm=llm,
                messages=messages,
                temperature=0.1,
                timeout_seconds=timeout_seconds,
            )
            merged = self._merge_prediction_payload(base, payload)
            if merged is None:
                return None
            return self._finalize_prediction(
                user_id=user_id,
                forecast=merged,
                horizon="realtime",
                source=source_tier.value,
                tier=model_key,
                fallback_used=False,
                surface=surface,
            )

        for model_key, source_tier, timeout_seconds in self._realtime_model_attempts():
            try:
                forecast = await _attempt(
                    model_key,
                    source_tier=source_tier,
                    timeout_seconds=timeout_seconds,
                )
                if forecast is not None:
                    logger.info(
                        f"Realtime prediction ready for user {user_id}: "
                        f"model={model_key}, tier={source_tier.value}"
                    )
                    return forecast
                logger.info(
                    f"Realtime prediction model returned no usable payload for user {user_id}: "
                    f"model={model_key}, tier={source_tier.value}"
                )
            except Exception as exc:
                logger.info(
                    f"Realtime prediction tier skipped for user {user_id}: "
                    f"model={model_key}, tier={source_tier.value}, error={exc}"
                )

        return None

    async def _request_prediction_payload(
        self,
        *,
        llm: Any,
        messages: list[dict[str, str]],
        temperature: float,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any] | None:
        async def _run() -> dict[str, Any] | None:
            raw = await llm.chat(
                messages=messages,
                temperature=temperature,
            )
            return self._parse_prediction_json(raw)

        if timeout_seconds is None:
            return await _run()
        return await asyncio.wait_for(_run(), timeout=timeout_seconds)

    def _parse_prediction_json(self, raw: Any) -> dict[str, Any] | None:
        if not isinstance(raw, str):
            return raw if isinstance(raw, dict) else None

        cleaned = raw.replace("```json", "").replace("```", "").strip()
        if not cleaned:
            return None

        try:
            payload = json.loads(cleaned)
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                payload = json.loads(cleaned[start:end + 1])
                return payload if isinstance(payload, dict) else None
            except json.JSONDecodeError:
                return None

    def _merge_prediction_payload(
        self,
        base: dict[str, Any],
        payload: Any,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None

        title = str(payload.get("title") or "").strip()
        summary = str(payload.get("summary") or "").strip()
        action_type = str(payload.get("predicted_action_type") or "").strip()
        suggested_prompt = str(payload.get("suggested_prompt") or "").strip()
        reasons = [
            str(item).strip()
            for item in list(payload.get("reasons") or [])
            if str(item).strip()
        ]
        has_signal = any([title, summary, action_type, suggested_prompt, reasons])
        if not has_signal:
            return None

        merged_confidence = payload.get("confidence")
        try:
            confidence = float(merged_confidence)
        except (TypeError, ValueError):
            confidence = float(base["confidence"])

        return {
            **base,
            "title": title or str(base["title"]),
            "summary": summary or str(base["summary"]),
            "confidence": max(0.0, min(confidence, 0.95)),
            "predicted_action_type": action_type or str(base["predicted_action_type"]),
            "predicted_window": str(payload.get("predicted_window") or base["predicted_window"]),
            "reasons": reasons or list(base["reasons"]),
            "suggested_prompt": suggested_prompt or str(base["suggested_prompt"]),
        }

    def _build_realtime_llm_messages(
        self,
        *,
        partial_text: str,
        base: dict[str, Any],
    ) -> list[dict[str, str]]:
        signals = base.get("signals", {})
        compact_payload = {
            "input": partial_text[:180],
            "base_action": base.get("predicted_action_type"),
            "base_prompt": str(base.get("suggested_prompt") or "")[:120],
            "pending_task_count": signals.get("pending_task_count", 0),
            "focus_sessions_last_24h": signals.get("focus_sessions_last_24h", 0),
            "top_task_title": signals.get("top_task_title"),
            "surface": signals.get("surface") or "chat",
        }
        return [
            {
                "role": "system",
                "content": (
                    "你是 Sparkle 的实时下一步预测器。"
                    "目标是在 2 秒内判断用户此刻最可能点击或要求的下一步。"
                    "只输出 JSON。优先给出 predicted_action_type 和 suggested_prompt。"
                    "句子要短，不确定字段可以留空。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(compact_payload, ensure_ascii=False),
            },
        ]

    def _build_long_horizon_messages(self, base: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "你是 Sparkle 的长期行为预测器。"
                    "基于最近行为、待办和专注信号，判断用户未来 2 到 6 小时最可能推进的一件事。"
                    "只输出一行 JSON，字段尽量包含 title, summary, confidence, "
                    "predicted_action_type, predicted_window, reasons, suggested_prompt。"
                    "结论短、动作明确。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(base.get("signals", {}), ensure_ascii=False),
            },
        ]

    def _realtime_model_attempts(self) -> list[tuple[str, ModelTier, float]]:
        attempts: list[tuple[str, ModelTier, float]] = []

        def _append_candidates(
            tier: ModelTier,
            *,
            timeout_seconds: float,
            preferred_order: list[str],
            limit: int,
        ) -> None:
            candidates = llm_router.resolve_candidate_models(
                AgentRole.GENERATION,
                TaskType.STANDARD_RESPONSE,
                force_tier=tier,
            )
            ordered = [model for model in preferred_order if model in candidates]
            ordered.extend(model for model in candidates if model not in ordered)
            for model_key in ordered[:limit]:
                attempts.append((model_key, tier, timeout_seconds))

        _append_candidates(
            ModelTier.FREE,
            timeout_seconds=self.REALTIME_FREE_TIMEOUT_SECONDS,
            preferred_order=["siliconflow_free"],
            limit=1,
        )
        _append_candidates(
            ModelTier.FREE_FAST,
            timeout_seconds=self.REALTIME_FREE_FAST_TIMEOUT_SECONDS,
            preferred_order=["glm_4_5_air_free"],
            limit=1,
        )
        _append_candidates(
            ModelTier.FAST,
            timeout_seconds=self.REALTIME_FAST_TIMEOUT_SECONDS,
            preferred_order=["xiaomi_chat", "glm_4_7_flash_no_thinking"],
            limit=2,
        )
        return attempts

    def _select_long_horizon_model_chain(
        self,
        signals: dict[str, Any],
    ) -> tuple[list[str], str]:
        pending_task_count = int(signals.get("pending_task_count") or 0)
        overdue_count = int(signals.get("overdue_count") or 0)
        completed_last_24h = int(signals.get("completed_last_24h") or 0)
        focus_minutes_last_24h = int(signals.get("focus_minutes_last_24h") or 0)
        study_records_last_24h = int(signals.get("study_records_last_24h") or 0)
        study_records_last_7d = int(signals.get("study_records_last_7d") or 0)
        top_task_priority = int(signals.get("top_task_priority") or 0)
        has_top_task = bool(str(signals.get("top_task_title") or "").strip())

        complexity_score = 0
        ambiguity_score = 0

        if pending_task_count >= 2:
            complexity_score += 1
        if pending_task_count >= 5:
            complexity_score += 1
        if overdue_count > 0:
            complexity_score += 2
        if top_task_priority >= 2:
            complexity_score += 1
        if focus_minutes_last_24h >= 60:
            complexity_score += 1
        if study_records_last_7d >= 8:
            complexity_score += 1

        if has_top_task and completed_last_24h == 0 and focus_minutes_last_24h == 0:
            ambiguity_score += 1
        if overdue_count > 0 and completed_last_24h > 0:
            ambiguity_score += 1
        if pending_task_count == 0 and study_records_last_24h > 0:
            ambiguity_score += 1
        if pending_task_count >= 4 and focus_minutes_last_24h < 20:
            ambiguity_score += 1

        if ambiguity_score >= 2 or complexity_score >= 6:
            preferred = [
                "glm_4_7_thinking",
                "glm_4_7_no_thinking",
                "glm_4_6_batch",
                "glm_4_5_air_batch",
            ]
            reason = "高冲突/高复杂行为信号，优先用 glm_4_7_thinking 做抽象预测"
        elif complexity_score >= 4:
            preferred = [
                "glm_4_7_no_thinking",
                "glm_4_7_thinking",
                "glm_4_6_batch",
                "glm_4_5_air_batch",
            ]
            reason = "中高复杂行为信号，优先用 glm_4_7_no_thinking 做稳态综合"
        elif complexity_score >= 2:
            preferred = [
                "glm_4_6_batch",
                "glm_4_7_no_thinking",
                "glm_4_5_air_batch",
                "glm_4_7_thinking",
            ]
            reason = "中等复杂行为信号，优先用 glm_4_6_batch 控制成本"
        else:
            preferred = [
                "glm_4_5_air_batch",
                "glm_4_6_batch",
                "glm_4_7_no_thinking",
                "glm_4_7_thinking",
            ]
            reason = "低复杂行为信号，优先用 glm_4_5_air_batch 快速完成批处理"

        registered = llm_router.resolve_candidate_models(
            AgentRole.GENERATION,
            TaskType.STANDARD_RESPONSE,
            force_tier=ModelTier.GLM_BATCH,
        )
        ordered = [model_key for model_key in preferred if model_key in registered]
        ordered.extend(model_key for model_key in registered if model_key not in ordered)
        return ordered, reason

    def _finalize_prediction(
        self,
        *,
        user_id: UUID,
        forecast: dict[str, Any],
        horizon: str,
        source: str,
        tier: str,
        fallback_used: bool,
        surface: str | None = None,
    ) -> dict[str, Any]:
        generated_at = self._get_current_time().isoformat()
        prediction_id = str(uuid4())
        action_type = str(forecast.get("predicted_action_type") or "continue_chat")
        suggested_prompt = str(forecast.get("suggested_prompt") or "").strip()
        primary_route = str(forecast.get("primary_route") or self._route_for_action(action_type))
        explanations = self._normalize_explanations(forecast.get("explanations"))
        reasons = [str(item) for item in list(forecast.get("reasons") or []) if str(item).strip()]

        recommended_actions = self._build_prediction_actions(
            prediction_id=prediction_id,
            action_type=action_type,
            suggested_prompt=suggested_prompt,
            primary_route=primary_route,
            surface=surface,
        )

        return {
            "schema_version": "prediction.v1",
            "prediction_id": prediction_id,
            "horizon": horizon,
            "surface": surface,
            "title": str(forecast.get("title") or ""),
            "summary": str(forecast.get("summary") or ""),
            "confidence": round(float(forecast.get("confidence") or 0.0), 3),
            "predicted_action_type": action_type,
            "predicted_window": str(forecast.get("predicted_window") or "now"),
            "reasons": reasons,
            "suggested_prompt": suggested_prompt,
            "prediction_source": source,
            "prediction_tier": tier,
            "fallback_used": fallback_used,
            "generated_at": generated_at,
            "signals": forecast.get("signals") or {},
            "explanations": explanations,
            "recommended_actions": recommended_actions,
            "tracking": {
                "candidate_id": prediction_id,
                "action_type": action_type,
                "surface": surface,
            },
            "entity_card": build_prediction_entity_card(
                prediction_id=prediction_id,
                title=str(forecast.get("title") or ""),
                summary=str(forecast.get("summary") or ""),
                action_type=action_type,
                suggested_prompt=suggested_prompt,
                predicted_window=str(forecast.get("predicted_window") or "now"),
                confidence=round(float(forecast.get("confidence") or 0.0), 3),
                surface=surface,
                reasons=reasons,
                source=source,
                tier=tier,
                recommended_actions=recommended_actions,
            ),
            "user_id": str(user_id),
        }

    def _build_prediction_actions(
        self,
        *,
        prediction_id: str,
        action_type: str,
        suggested_prompt: str,
        primary_route: str,
        surface: str | None,
    ) -> list[dict[str, Any]]:
        primary_label = {
            "create_task": "落成任务",
            "study_plan": "生成计划",
            "error_diagnosis": "开始诊断",
            "resume_task": "继续任务",
            "light_review": "开始复盘",
            "start_focus": "开始专注",
            "translate": "立即获取结果",
        }.get(action_type, "继续让 AI 帮我推进")

        actions = [
            {
                "id": f"{prediction_id}:primary",
                "label": primary_label,
                "action_type": action_type,
                "target_route": primary_route,
                "suggested_prompt": suggested_prompt,
                "resource_type": "chat" if primary_route == "/chat" else "navigation",
                "resource_id": None,
                "surface": surface,
            },
        ]

        if suggested_prompt:
            actions.append(
                {
                    "id": f"{prediction_id}:chat",
                    "label": "交给 AI 承接",
                    "action_type": "continue_chat",
                    "target_route": "/chat",
                    "suggested_prompt": suggested_prompt,
                    "resource_type": "chat",
                    "resource_id": None,
                    "surface": surface,
                },
            )

        if action_type not in {"light_review", "start_focus"}:
            actions.append(
                {
                    "id": f"{prediction_id}:focus",
                    "label": "先专注 25 分钟",
                    "action_type": "start_focus",
                    "target_route": "/focus",
                    "suggested_prompt": "",
                    "resource_type": "focus_session",
                    "resource_id": None,
                    "surface": surface,
                },
            )

        return actions[:3]

    def _normalize_explanations(self, value: Any) -> dict[str, list[str]]:
        base = {
            "recent_24h": [],
            "recent_7d": [],
            "profile": [],
            "plan": [],
            "focus": [],
        }
        if not isinstance(value, dict):
            return base
        for key in base:
            raw = value.get(key)
            if isinstance(raw, list):
                base[key] = [str(item) for item in raw if str(item).strip()]
        return base

    def _route_for_action(self, action_type: str) -> str:
        return {
            "create_task": "/tasks/new",
            "resume_task": "/tasks",
            "resume_priority_task": "/tasks",
            "study_plan": "/chat",
            "error_diagnosis": "/chat",
            "light_review": "/chat",
            "start_focus": "/focus",
            "translate": "/chat",
        }.get(action_type, "/chat")

    async def get_prediction_analytics(
        self,
        user_id: UUID,
        *,
        days: int = 7,
    ) -> dict[str, Any]:
        since = self._get_current_time().replace(tzinfo=None) - timedelta(days=max(1, min(days, 30)))
        try:
            stmt = select(CandidateActionFeedback).where(
                CandidateActionFeedback.user_id == user_id,
                CandidateActionFeedback.created_at >= since,
                CandidateActionFeedback.deleted_at.is_(None),
            )
            rows = (await self.db.execute(stmt)).scalars().all()
        except Exception as exc:
            if "candidate_action_feedback" in str(exc).lower():
                await self.db.rollback()
                logger.warning(
                    "Prediction analytics feedback table unavailable; continuing in degraded mode for user {}",
                    user_id,
                )
                rows = []
            else:
                raise

        def _blank_bucket() -> dict[str, Any]:
            return {
                "impressions": 0,
                "accepts": 0,
                "dismisses": 0,
                "ignores": 0,
                "executed_accepts": 0,
                "linked_executions": 0,
            }

        overall = _blank_bucket()
        by_surface: dict[str, dict[str, Any]] = defaultdict(_blank_bucket)
        by_horizon: dict[str, dict[str, Any]] = defaultdict(_blank_bucket)
        by_source: dict[str, dict[str, Any]] = defaultdict(_blank_bucket)
        by_action_type: dict[str, dict[str, Any]] = defaultdict(_blank_bucket)

        for row in rows:
            ctx = row.context_snapshot or {}
            prediction_ctx = ctx.get("prediction") if isinstance(ctx.get("prediction"), dict) else {}
            surface = str(prediction_ctx.get("surface") or "unknown")
            horizon = str(prediction_ctx.get("horizon") or "unknown")
            source = str(prediction_ctx.get("source") or "unknown")
            action_type = str(row.action_type or "unknown")
            buckets = [overall, by_surface[surface], by_horizon[horizon], by_source[source], by_action_type[action_type]]
            for bucket in buckets:
                if row.feedback_type == "impression":
                    bucket["impressions"] += 1
                elif row.feedback_type == "accept":
                    bucket["accepts"] += 1
                elif row.feedback_type == "dismiss":
                    bucket["dismisses"] += 1
                elif row.feedback_type == "ignore":
                    bucket["ignores"] += 1
                if row.feedback_type == "accept" and row.executed:
                    bucket["executed_accepts"] += 1

        event_stmt = select(TrackingEvent).where(
            TrackingEvent.user_id == user_id,
            TrackingEvent.received_at >= since,
        )
        events = (await self.db.execute(event_stmt)).scalars().all()
        for event in events:
            if event.event_type != "entity_execution":
                continue
            payload = event.payload if isinstance(event.payload, dict) else {}
            prediction_id = str(payload.get("prediction_id") or "").strip()
            if not prediction_id:
                continue
            surface = str(payload.get("prediction_surface") or payload.get("surface") or "unknown")
            horizon = str(payload.get("prediction_horizon") or "unknown")
            source = str(payload.get("prediction_source") or "unknown")
            action_type = str(payload.get("prediction_action_type") or payload.get("action_type") or "unknown")
            buckets = [
                overall,
                by_surface[surface],
                by_horizon[horizon],
                by_source[source],
                by_action_type[action_type],
            ]
            for bucket in buckets:
                bucket["linked_executions"] += 1

        def _finalize(bucket: dict[str, Any]) -> dict[str, Any]:
            impressions = int(bucket["impressions"])
            accepts = int(bucket["accepts"])
            executed_accepts = int(bucket["executed_accepts"])
            linked_executions = int(bucket["linked_executions"])
            total_executions = linked_executions if linked_executions > 0 else executed_accepts
            return {
                **bucket,
                "ctr_percent": round((accepts / impressions) * 100, 2) if impressions > 0 else 0.0,
                "execution_rate_percent": round((total_executions / accepts) * 100, 2)
                if accepts > 0
                else 0.0,
                "impression_to_execution_percent": round((total_executions / impressions) * 100, 2)
                if impressions > 0
                else 0.0,
            }

        overall_final = _finalize(overall)
        by_surface_final = {key: _finalize(value) for key, value in by_surface.items()}
        by_horizon_final = {key: _finalize(value) for key, value in by_horizon.items()}
        by_source_final = {key: _finalize(value) for key, value in by_source.items()}
        by_action_type_final = {key: _finalize(value) for key, value in by_action_type.items()}

        top_actions = sorted(
            (
                {
                    "action_type": key,
                    **value,
                }
                for key, value in by_action_type_final.items()
            ),
            key=lambda item: (item.get("accepts", 0), item.get("linked_executions", 0)),
            reverse=True,
        )[:5]

        return {
            "generated_at": self._get_current_time().isoformat(),
            "window_days": max(1, min(days, 30)),
            "overall": overall_final,
            "funnel": {
                "impressions": overall_final["impressions"],
                "accepts": overall_final["accepts"],
                "executions": overall_final["linked_executions"],
                "ctr_percent": overall_final["ctr_percent"],
                "accept_to_execution_percent": overall_final["execution_rate_percent"],
                "impression_to_execution_percent": overall_final["impression_to_execution_percent"],
            },
            "by_surface": by_surface_final,
            "by_horizon": by_horizon_final,
            "by_source": by_source_final,
            "by_action_type": by_action_type_final,
            "top_actions": top_actions,
        }

    async def _get_cached_forecast(self, cache_key: str) -> dict[str, Any] | None:
        if not cache_service.redis:
            return None
        try:
            raw = await cache_service.redis.get(cache_key)
            if not raw:
                return None
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else None
        except Exception as exc:
            logger.warning(f"Failed to read predictive cache {cache_key}: {exc}")
            return None

    async def _cache_forecast(self, cache_key: str, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        if not cache_service.redis:
            return
        try:
            await cache_service.redis.setex(cache_key, ttl_seconds, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.warning(f"Failed to cache predictive forecast {cache_key}: {exc}")

    async def _schedule_long_horizon_refresh(self, user_id: UUID) -> None:
        if not cache_service.redis:
            return
        lock_key = f"predictive:next_intent:refreshing:{user_id}"
        try:
            acquired = await cache_service.redis.set(lock_key, "1", ex=300, nx=True)
            if not acquired:
                return

            from app.core.celery_app import celery_app

            celery_app.send_task(
                "generate_long_horizon_prediction",
                args=(str(user_id),),
                queue="glm_batch",
            )

            if settings.DEBUG:
                self._schedule_local_long_horizon_refresh(
                    user_id=user_id,
                    lock_key=lock_key,
                    reason="debug_local_fallback",
                )
        except Exception as exc:
            try:
                await cache_service.redis.delete(lock_key)
            except Exception:
                pass
            logger.warning(f"Failed to schedule long horizon prediction for user {user_id}: {exc}")

    def _schedule_local_long_horizon_refresh(self, *, user_id: UUID, lock_key: str, reason: str) -> None:
        async def _run() -> None:
            from app.db.session import AsyncSessionLocal

            try:
                logger.info(f"Scheduling local long horizon refresh for user {user_id} ({reason})")
                async with AsyncSessionLocal() as session:
                    service = PredictiveService(session)
                    await service.generate_long_horizon_forecast(user_id)
            except Exception as exc:
                logger.warning(f"Local long horizon refresh failed for user {user_id}: {exc}")
            finally:
                if cache_service.redis:
                    try:
                        await cache_service.redis.delete(lock_key)
                    except Exception as exc:
                        logger.warning(f"Failed to release long horizon refresh lock for user {user_id}: {exc}")

        asyncio.create_task(_run())
