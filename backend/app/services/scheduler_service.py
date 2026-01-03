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
from app.services.push_service import PushService
from app.services.cognitive_service import CognitiveService

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        # 智能推送循环 (每15分钟运行一次，PushService 内部会做更细致的频控)
        self.scheduler.add_job(self.run_smart_push_cycle, 'interval', minutes=15)
        
        # 每日衰减任务 (每天凌晨3点执行)
        self.scheduler.add_job(self.apply_daily_decay, 'cron', hour=3, minute=0)

        # 每日行为挖掘 (每天凌晨4点执行)
        self.scheduler.add_job(self.mining_implicit_behaviors_job, 'cron', hour=4, minute=0)

        self.scheduler.start()
        logger.info("Scheduler started with smart push cycle and daily decay jobs")

    async def run_smart_push_cycle(self):
        """
        执行智能推送周期
        触发 PushService.process_all_users()
        """
        logger.info("Starting smart push cycle...")
        async with AsyncSessionLocal() as db:
            push_service = PushService(db)
            await push_service.process_all_users()

    # async def check_fragmented_time(self):
    #     """
    #     Check for fragmented time opportunities for all users.
    #     (Deprecated by Smart Push Cycle v2.0)
    #     """
    #     logger.info("Checking for fragmented time opportunities...")
    #     async with AsyncSessionLocal() as db:
    #         # 1. Get active users with schedule preferences
    #         result = await db.execute(select(User).where(User.is_active == True, User.schedule_preferences.isnot(None)))
    #         users = result.scalars().all()
    #         ...
    # (保留旧代码作为参考或彻底删除，此处注释掉以避免冲突)

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

    async def mining_implicit_behaviors_job(self):
        """
        每日隐式行为挖掘任务
        """
        logger.info("Starting implicit behavior mining job...")
        try:
            async with AsyncSessionLocal() as db:
                # 1. Get all active users
                result = await db.execute(select(User).where(User.is_active == True))
                users = result.scalars().all()
                
                cognitive_service = CognitiveService(db)
                total_fragments = 0
                
                for user in users:
                    fragments = await cognitive_service.mining_implicit_behaviors(user.id)
                    total_fragments += len(fragments)
                    
                logger.info(f"Implicit mining completed: {total_fragments} fragments generated across {len(users)} users.")

        except Exception as e:
            logger.error(f"Error in implicit mining job: {e}", exc_info=True)

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
