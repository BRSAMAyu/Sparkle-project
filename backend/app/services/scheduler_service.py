from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from loguru import logger
from datetime import datetime
import json
import asyncio

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationCreate
from app.services.decay_service import DecayService

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        # 碎片时间提醒 (每15分钟检查一次)
        self.scheduler.add_job(self.check_fragmented_time, 'interval', minutes=15)

        # 每日衰减任务 (每天凌晨3点执行)
        self.scheduler.add_job(self.apply_daily_decay, 'cron', hour=3, minute=0)

        self.scheduler.start()
        logger.info("Scheduler started with fragmented time check and daily decay jobs")

    async def check_fragmented_time(self):
        """
        Check for fragmented time opportunities for all users.
        """
        logger.info("Checking for fragmented time opportunities...")
        async with AsyncSessionLocal() as db:
            # 1. Get active users with schedule preferences
            result = await db.execute(select(User).where(User.is_active == True, User.schedule_preferences.isnot(None)))
            users = result.scalars().all()
            
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            for user in users:
                try:
                    prefs = user.schedule_preferences
                    if not prefs:
                        continue
                        
                    # Example prefs: {"commute": ["08:00", "09:00"], "lunch": ["12:00", "13:00"]}
                    # Simplified logic: Check if current time falls within any range
                    
                    is_fragmented_time = False
                    matched_period = ""
                    
                    for period_name, time_range in prefs.items():
                        if isinstance(time_range, list) and len(time_range) == 2:
                            start_time = datetime.strptime(time_range[0], "%H:%M").time()
                            end_time = datetime.strptime(time_range[1], "%H:%M").time()
                            current_time = now.time()
                            
                            if start_time <= current_time <= end_time:
                                is_fragmented_time = True
                                matched_period = period_name
                                break
                    
                    if is_fragmented_time:
                        await self._suggest_task(db, user, matched_period)
                        
                except Exception as e:
                    logger.error(f"Error checking fragmented time for user {user.id}: {e}")

    async def _suggest_task(self, db, user, period_name):
        """
        Suggest a short task for the user.
        """
        # Find a short task (< 15 mins)
        result = await db.execute(
            select(Task)
            .where(Task.user_id == user.id, Task.status == TaskStatus.TODO, Task.estimated_minutes <= 15)
            .limit(1)
        )
        task = result.scalar_one_or_none()
        
        if task:
            # Check if we already notified recently? (Simplification: Just notify)
            # Ideally we should check if we already sent a notification for this slot today.
            
            logger.info(f"Suggesting task {task.title} for user {user.username} during {period_name}")
            
            await NotificationService.create(db, user.id, NotificationCreate(
                title=f"利用碎片时间 ({period_name})",
                content=f"现在是 {period_name} 时间，要不要花 {task.estimated_minutes} 分钟完成任务：{task.title}？",
                type="fragmented_time",
                data={"task_id": str(task.id)}
            ))

    async def apply_daily_decay(self):
        """
        每日遗忘衰减任务
        对所有用户的知识点应用遗忘曲线衰减
        """
        logger.info("Starting daily decay job...")
        try:
            async with AsyncSessionLocal() as db:
                decay_service = DecayService(db)
                stats = await decay_service.apply_daily_decay()

                logger.info(
                    f"Daily decay completed: "
                    f"processed={stats['processed']}, "
                    f"dimmed={stats['dimmed']}, "
                    f"collapsed={stats['collapsed']}"
                )

                # 可选：对暗淡严重的节点发送复习提醒
                if stats['dimmed'] > 0:
                    await self._send_review_reminders(db)

        except Exception as e:
            logger.error(f"Error in daily decay job: {e}", exc_info=True)

    async def _send_review_reminders(self, db):
        """
        向用户发送复习提醒通知
        """
        try:
            # 获取所有有需要复习节点的用户
            result = await db.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()

            for user in users:
                decay_service = DecayService(db)
                suggestions = await decay_service.get_review_suggestions(
                    user_id=user.id,
                    limit=5
                )

                if suggestions:
                    urgent_count = sum(1 for s in suggestions if s['urgency'] == 'high')

                    # 发送通知
                    await NotificationService.create(db, user.id, NotificationCreate(
                        title="知识复习提醒",
                        content=f"您有 {len(suggestions)} 个知识点需要复习" +
                               (f"，其中 {urgent_count} 个紧急" if urgent_count > 0 else ""),
                        type="review_reminder",
                        data={"suggestion_count": len(suggestions), "urgent_count": urgent_count}
                    ))

                    logger.info(f"Sent review reminder to user {user.username}")

        except Exception as e:
            logger.error(f"Error sending review reminders: {e}", exc_info=True)

scheduler_service = SchedulerService()
