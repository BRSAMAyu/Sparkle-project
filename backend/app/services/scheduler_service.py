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

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        self.scheduler.add_job(self.check_fragmented_time, 'interval', minutes=15)
        self.scheduler.start()
        logger.info("Scheduler started")

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

scheduler_service = SchedulerService()
