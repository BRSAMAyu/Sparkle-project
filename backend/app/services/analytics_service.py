from uuid import UUID
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.galaxy import StudyRecord
from app.models.chat import ChatMessage, MessageRole
from app.models.cognitive import CognitiveFragment
from app.models.analytics import UserDailyMetric

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_daily_metrics(self, user_id: UUID, target_date: date) -> Optional[UserDailyMetric]:
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
                anxious_count = sum(1 for f in fragments if f.sentiment == "anxious")
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
        """
        try:
            # Get User Basics
            user_query = select(User).where(User.id == user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found when generating summary")
                return "User not found."

            # Get last 7 days metrics
            seven_days_ago = date.today() - timedelta(days=7)
            metrics_query = select(UserDailyMetric).where(
                and_(
                    UserDailyMetric.user_id == user_id,
                    UserDailyMetric.date >= seven_days_ago
                )
            ).order_by(desc(UserDailyMetric.date))
            
            metrics_result = await self.db.execute(metrics_query)
            recent_metrics = metrics_result.scalars().all()

            # Aggregate
            total_focus = sum(m.total_focus_minutes for m in recent_metrics)
            avg_focus = total_focus / len(recent_metrics) if recent_metrics else 0
            total_completed = sum(m.tasks_completed for m in recent_metrics)
            avg_anxiety = sum(m.anxiety_score for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0
            
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
