"""
Predictive Learning Intelligence Service - 预测学习智能服务

功能：
- 参与度预测：预测用户下次活跃时间
- 难度预测：预测某话题对用户的难度
- 最佳学习时间推荐
- 辍学风险检测
"""
from __future__ import annotations

import json
import statistics
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.cache import cache_service
from app.core.llm_router import llm_router
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus
from app.services.llm_service import get_llm_service_for_specific_model


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
            now = self._get_current_time()

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
            now = self._get_current_time()

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
            now = self._get_current_time()

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

        rule_based = await self._build_rule_based_next_intent(user_id)
        await self._cache_forecast(
            cache_key,
            rule_based,
            ttl_seconds=self.LONG_HORIZON_SOFT_STALE_SECONDS,
        )
        await self._schedule_long_horizon_refresh(user_id)
        return rule_based

    async def generate_long_horizon_forecast(self, user_id: UUID) -> dict[str, Any]:
        base = await self._build_rule_based_next_intent(user_id)
        try:
            selection = llm_router.select_model(
                AgentRole.GENERATION,
                TaskType.STANDARD_RESPONSE,
                force_tier=ModelTier.GLM_BATCH,
            )
            llm = await get_llm_service_for_specific_model(
                selection.model_key,
                agent_role=AgentRole.GENERATION,
            )
            payload = await llm.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是 Sparkle 的长期行为预测器。"
                            "请基于输入的用户画像、最近24小时行为、待办和专注信号，"
                            "预测用户接下来最可能想做的一件事。"
                            "输出 JSON，字段必须包含 title, summary, confidence, "
                            "predicted_action_type, predicted_window, reasons(list), suggested_prompt。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(base["signals"], ensure_ascii=False),
                    },
                ],
                schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "confidence": {"type": "number"},
                        "predicted_action_type": {"type": "string"},
                        "predicted_window": {"type": "string"},
                        "reasons": {"type": "array", "items": {"type": "string"}},
                        "suggested_prompt": {"type": "string"},
                    },
                    "required": [
                        "title",
                        "summary",
                        "confidence",
                        "predicted_action_type",
                        "predicted_window",
                        "reasons",
                        "suggested_prompt",
                    ],
                },
                temperature=0.3,
            )
            if isinstance(payload, dict) and payload.get("title") and payload.get("summary"):
                enriched = {
                    **base,
                    "title": str(payload.get("title") or base["title"]),
                    "summary": str(payload.get("summary") or base["summary"]),
                    "confidence": float(payload.get("confidence") or base["confidence"]),
                    "predicted_action_type": str(
                        payload.get("predicted_action_type") or base["predicted_action_type"]
                    ),
                    "predicted_window": str(payload.get("predicted_window") or base["predicted_window"]),
                    "reasons": list(payload.get("reasons") or base["reasons"]),
                    "suggested_prompt": str(payload.get("suggested_prompt") or base["suggested_prompt"]),
                    "prediction_source": "glm_batch",
                    "prediction_tier": selection.model_key,
                    "fallback_used": False,
                    "generated_at": self._get_current_time().isoformat(),
                }
                await self._cache_forecast(
                    f"predictive:next_intent:{user_id}",
                    enriched,
                    ttl_seconds=self.LONG_HORIZON_CACHE_TTL_SECONDS,
                )
                return enriched
        except Exception as exc:
            logger.warning(f"Long horizon prediction failed for user {user_id}: {exc}")

        fallback = {
            **base,
            "prediction_source": "rules",
            "prediction_tier": "rules",
            "fallback_used": True,
            "generated_at": self._get_current_time().isoformat(),
        }
        await self._cache_forecast(
            f"predictive:next_intent:{user_id}",
            fallback,
            ttl_seconds=self.LONG_HORIZON_CACHE_TTL_SECONDS,
        )
        return fallback

    async def _build_rule_based_next_intent(self, user_id: UUID) -> dict[str, Any]:
        now = self._get_current_time().replace(tzinfo=None)
        last_24h = now - timedelta(hours=24)

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
                },
            }

        return {
            **forecast,
            "prediction_source": "rules",
            "prediction_tier": "rules",
            "fallback_used": True,
            "generated_at": self._get_current_time().isoformat(),
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
        except Exception as exc:
            logger.warning(f"Failed to schedule long horizon prediction for user {user_id}: {exc}")
