from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import time_utils
from app.models.analytics import UserDailyMetric
from app.models.chat import ChatMessage, MessageRole
from app.models.cognitive import CognitiveFragment
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.compliance.crypto_erase import CryptoEraseManager


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_daily_metrics(self, user_id: UUID, target_date: date) -> UserDailyMetric | None:
        """
        Calculate and store/update daily metrics for a specific user and date.
        """
        logger.info(f"Calculating daily metrics for user {user_id} on {target_date}")
        try:
            # Define time range for the day
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())

            # 1. Engagement Metrics
            # Focus Minutes & Completed Tasks
            task_query = select(
                func.coalesce(func.sum(Task.actual_minutes), 0),
                func.count(Task.id)
            ).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= start_of_day,
                    Task.completed_at <= end_of_day
                )
            )
            task_result = await self.db.execute(task_query)
            focus_minutes, completed_count = task_result.one()

            # Created Tasks
            created_query = select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.created_at >= start_of_day,
                    Task.created_at <= end_of_day
                )
            )
            created_result = await self.db.execute(created_query)
            created_count = created_result.scalar() or 0

            # 2. Learning Metrics
            # Study Records Aggregation
            study_query = select(
                func.count(func.distinct(StudyRecord.node_id)),
                func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0),
                func.count(StudyRecord.id)
            ).where(
                and_(
                    StudyRecord.user_id == user_id,
                    StudyRecord.created_at >= start_of_day,
                    StudyRecord.created_at <= end_of_day
                )
            )
            study_result = await self.db.execute(study_query)
            nodes_studied, mastery_gained, total_records = study_result.one()

            # Review Count
            review_query = select(func.count(StudyRecord.id)).where(
                and_(
                    StudyRecord.user_id == user_id,
                    StudyRecord.record_type == 'review',
                    StudyRecord.created_at >= start_of_day,
                    StudyRecord.created_at <= end_of_day
                )
            )
            review_result = await self.db.execute(review_query)
            review_count = review_result.scalar() or 0

            # 3. Cognitive Metrics
            # Anxiety Score
            cog_query = select(CognitiveFragment).where(
                and_(
                    CognitiveFragment.user_id == user_id,
                    CognitiveFragment.created_at >= start_of_day,
                    CognitiveFragment.created_at <= end_of_day
                )
            )
            cog_result = await self.db.execute(cog_query)
            fragments = cog_result.scalars().all()

            anxiety_score = 0.0
            if fragments:
                crypto = CryptoEraseManager(self.db)
                anxious_count = 0
                for f in fragments:
                    if f.sentiment == "anxious":
                        anxious_count += 1
                        continue
                    if f.sensitive_tags_encrypted:
                        decrypted = await crypto.decrypt_payload(user_id, f.sensitive_tags_encrypted)
                        if decrypted and "anxiety_high" in decrypted:
                            anxious_count += 1
                anxiety_score = anxious_count / len(fragments)

            # 4. System Metrics
            # Chat Messages
            chat_query = select(func.count(ChatMessage.id)).where(
                and_(
                    ChatMessage.user_id == user_id,
                    ChatMessage.role == MessageRole.USER,
                    ChatMessage.created_at >= start_of_day,
                    ChatMessage.created_at <= end_of_day
                )
            )
            chat_result = await self.db.execute(chat_query)
            chat_count = chat_result.scalar() or 0

            # Update or Insert
            stmt = select(UserDailyMetric).where(
                and_(UserDailyMetric.user_id == user_id, UserDailyMetric.date == target_date)
            )
            result = await self.db.execute(stmt)
            metric = result.scalar_one_or_none()

            if not metric:
                metric = UserDailyMetric(user_id=user_id, date=target_date)
                self.db.add(metric)

            metric.total_focus_minutes = focus_minutes
            metric.tasks_completed = completed_count
            metric.tasks_created = created_count
            metric.nodes_studied = nodes_studied
            metric.mastery_gained = mastery_gained
            metric.review_count = review_count
            metric.anxiety_score = anxiety_score
            metric.chat_messages_count = chat_count

            await self.db.commit()
            await self.db.refresh(metric)
            logger.info(f"Daily metrics calculated successfully for user {user_id}")
            return metric
        except Exception as e:
            logger.error(f"Error calculating daily metrics for user {user_id}: {str(e)}")
            await self.db.rollback()
            return None # Or raise custom exception

    async def get_user_profile_summary(self, user_id: UUID) -> str:
        """
        Generate a text summary of the user's recent activity and stats for LLM context.

        V3-FIX-353：本摘要曾读 ``UserDailyMetric`` 预聚合表，而该表生产零写入方
        （``calculate_daily_metrics`` 全仓零调用方），读恒空表后把
        「Total Focus Time: 0 minutes / Recent Anxiety Index: 0.00」等结构性零
        当真实测量值注入 LLM 上下文（FIX-330 同形态）。现改为读侧实时聚合
        真实数据源（已完成任务的 actual_minutes 与 CognitiveFragment 情绪，
        均由生产链路真实写入），口径与 ``calculate_daily_metrics`` 一致；
        此处的零值仅来自真实表扫描（真测量零），窗口按 V3-FIX-37 用户本地日切。
        """
        try:
            # Get User Basics
            user_query = select(User).where(User.id == user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found when generating summary")
                return "User not found."

            # V3-FIX-353: 实时聚合真实数据源（不再读零写入的 UserDailyMetric 预聚合表）
            window_start, window_end = self._recent_activity_window(user)
            total_focus, total_completed = await self._task_activity_totals(user_id, window_start, window_end)
            avg_focus = total_focus / 7
            avg_anxiety = await self._anxiety_index(user_id, window_start, window_end)

            # Format Text
            summary = f"""
            [User Profile Analysis]
            - Flame Level: {user.flame_level} (Brightness: {user.flame_brightness:.2f})
            - Learning Style: Depth Preference {user.depth_preference:.2f}, Curiosity {user.curiosity_preference:.2f}

            [Recent Activity (Last 7 Days)]
            - Total Focus Time: {total_focus} minutes (Avg {avg_focus:.1f} min/day)
            - Tasks Completed: {total_completed}
            - Recent Anxiety Index: {avg_anxiety:.2f} (0-1 scale)
            """
            return summary
        except Exception as e:
            logger.error(f"Error generating profile summary for user {user_id}: {str(e)}")
            return "Error generating user profile summary."

    @staticmethod
    def _recent_activity_window(user: User) -> tuple[datetime, datetime]:
        """最近 7 天（含今日）活动窗口，V3-FIX-37 用户本地日切口径，返回 UTC naive 边界。"""
        tz_name = time_utils.user_timezone_name(user)
        today = time_utils.local_date(time_utils.utcnow(), tz_name)
        start_day = today - timedelta(days=6)
        return (
            time_utils.local_midnight_as_utc_naive(start_day, tz_name),
            time_utils.local_midnight_as_utc_naive(today + timedelta(days=1), tz_name),
        )

    async def _task_activity_totals(
        self, user_id: UUID, window_start: datetime, window_end: datetime
    ) -> tuple[int, int]:
        """窗口内已完成任务的专注分钟（actual_minutes）与完成数——任务完成真轨。"""
        task_query = select(
            func.coalesce(func.sum(Task.actual_minutes), 0),
            func.count(Task.id),
        ).where(
            and_(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= window_start,
                Task.completed_at < window_end,
            )
        )
        task_result = await self.db.execute(task_query)
        focus_minutes, completed_count = task_result.one()
        return int(focus_minutes or 0), int(completed_count or 0)

    async def _anxiety_index(self, user_id: UUID, window_start: datetime, window_end: datetime) -> float:
        """窗口内焦虑碎片占比，口径与 ``calculate_daily_metrics`` 一致；无碎片为真零。"""
        cog_query = select(CognitiveFragment).where(
            and_(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.created_at >= window_start,
                CognitiveFragment.created_at < window_end,
            )
        )
        cog_result = await self.db.execute(cog_query)
        fragments = cog_result.scalars().all()
        if not fragments:
            return 0.0

        crypto = CryptoEraseManager(self.db)
        anxious_count = 0
        for f in fragments:
            if f.sentiment == "anxious":
                anxious_count += 1
                continue
            if f.sensitive_tags_encrypted:
                decrypted = await crypto.decrypt_payload(user_id, f.sensitive_tags_encrypted)
                if decrypted and "anxiety_high" in decrypted:
                    anxious_count += 1
        return anxious_count / len(fragments)
