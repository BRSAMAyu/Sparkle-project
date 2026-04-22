"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from datetime import timezone, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.cognitive_service import CognitiveService
from app.services.decay_service import DecayService
from app.services.event_retention_service import EventRetentionService
from app.services.memory_jobs import MemoryJobsService
from app.services.nightly_review_service import NightlyReviewService
from app.services.notification_service import NotificationService
from app.services.personalization.preference_service import PreferenceService
from app.services.push_service import PushService
from app.services.community_advanced_service import OfflineQueueService
from app.services.execution_schedule_service import ExecutionScheduleService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

        # 事件保留清理 (每天凌晨2点半执行)
        self.scheduler.add_job(self.run_event_retention_cleanup, 'cron', hour=2, minute=30)

        # 离线消息队列过期清理（每小时一次）
        self.scheduler.add_job(self.run_offline_queue_cleanup, 'interval', hours=1)

        # 夜间复盘 (每天凌晨1点执行)
        self.scheduler.add_job(self.run_nightly_review, 'cron', hour=1, minute=0)

        if settings.ENABLE_MEMORY_JOBS:
            # Memory evidence health + decay + repair (daily, off by default)
            self.scheduler.add_job(self.run_memory_evidence_health_job, 'cron', hour=2, minute=10)
            self.scheduler.add_job(self.run_memory_decay_job, 'cron', hour=2, minute=40)
            self.scheduler.add_job(self.run_memory_repair_job, 'cron', hour=3, minute=10)
        if settings.ENABLE_MEMORY_DAILY_SUMMARY:
            self.scheduler.add_job(self.run_memory_daily_summary_job, 'cron', hour=3, minute=30)

        # 推断偏好衰减 (每周日凌晨2点执行)
        self.scheduler.add_job(self.apply_inferred_preference_decay, 'cron', day_of_week='sun', hour=2, minute=0)

        # ========== 胶囊生成调度任务 ==========

        # 每日胶囊生成 (每天早上8点)
        self.scheduler.add_job(self.generate_daily_capsules, 'cron', hour=8, minute=0)

        # 每周深度胶囊 (每周日早上9点)
        self.scheduler.add_job(self.generate_weekly_deep_capsules, 'cron', day_of_week='sun', hour=9, minute=0)

        # OpenClaw 定时/条件执行轮询（每分钟）
        self.scheduler.add_job(self.run_execution_schedule_tick, 'interval', minutes=1)

        self.scheduler.start()
        logger.info("Scheduler started with smart push cycle, daily decay, capsule generation, and weekly preference inference decay jobs")

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
                result = await db.execute(select(User).where(User.is_active))
                users = result.scalars().all()

                cognitive_service = CognitiveService(db)
                total_fragments = 0

                for user in users:
                    fragments = await cognitive_service.mining_implicit_behaviors(user.id)
                    total_fragments += len(fragments)

                logger.info(f"Implicit mining completed: {total_fragments} fragments generated across {len(users)} users.")

        except Exception as e:
            logger.error(f"Error in implicit mining job: {e}", exc_info=True)

    async def run_event_retention_cleanup(self):
        """
        清理过期事件与状态快照
        """
        logger.info("Starting event retention cleanup...")
        try:
            async with AsyncSessionLocal() as db:
                retention = EventRetentionService(db)
                events_pruned = await retention.prune_events(settings.EVENT_RETENTION_DAYS)
                states_pruned = await retention.prune_state_snapshots(settings.STATE_RETENTION_DAYS)
                logger.info(
                    f"Event retention cleanup completed: events={events_pruned}, states={states_pruned}"
                )
        except Exception as e:
            logger.error(f"Error in event retention cleanup: {e}", exc_info=True)

    async def run_offline_queue_cleanup(self):
        """清理过期离线消息，避免队列无限增长。"""
        logger.info("Starting offline queue cleanup...")
        try:
            async with AsyncSessionLocal() as db:
                expired_count = await OfflineQueueService.cleanup_expired(db)
                await db.commit()
                logger.info(f"Offline queue cleanup completed: expired={expired_count}")
        except Exception as e:
            logger.error(f"Error in offline queue cleanup: {e}", exc_info=True)

    async def run_nightly_review(self):
        """
        生成夜间复盘（Nightly Reviewer v1）
        """
        logger.info("Starting nightly review job...")
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.is_active))
                users = result.scalars().all()
                service = NightlyReviewService(db)
                for user in users:
                    await service.generate_for_user(user.id, user.timezone)
        except Exception as e:
            logger.error(f"Error in nightly review job: {e}", exc_info=True)

    async def run_execution_schedule_tick(self):
        logger.info("Starting execution schedule tick...")
        try:
            async with AsyncSessionLocal() as db:
                result = await ExecutionScheduleService(db).tick_due_schedules()
                logger.info(
                    "Execution schedule tick completed: due=%s dispatched=%s",
                    result["due_count"],
                    result["dispatched_count"],
                )
        except Exception as e:
            logger.error(f"Error in execution schedule tick: {e}", exc_info=True)

    async def run_memory_evidence_health_job(self):
        if not settings.ENABLE_MEMORY_JOBS:
            return
        logger.info("Starting memory evidence health job...")
        try:
            async with AsyncSessionLocal() as db:
                service = MemoryJobsService(db)
                await service.run_evidence_health_job(limit_per_type=200)
        except Exception as e:
            logger.error(f"Error in memory evidence health job: {e}", exc_info=True)

    async def run_memory_decay_job(self):
        if not settings.ENABLE_MEMORY_JOBS:
            return
        logger.info("Starting memory decay job...")
        try:
            async with AsyncSessionLocal() as db:
                service = MemoryJobsService(db)
                await service.run_decay_job(window_days=14)
        except Exception as e:
            logger.error(f"Error in memory decay job: {e}", exc_info=True)

    async def run_memory_repair_job(self):
        if not settings.ENABLE_MEMORY_JOBS:
            return
        logger.info("Starting memory repair job...")
        try:
            async with AsyncSessionLocal() as db:
                service = MemoryJobsService(db)
                await service.run_repair_job(limit=200)
        except Exception as e:
            logger.error(f"Error in memory repair job: {e}", exc_info=True)

    async def run_memory_daily_summary_job(self):
        if not settings.ENABLE_MEMORY_DAILY_SUMMARY:
            return
        logger.info("Starting memory daily summary job...")
        try:
            async with AsyncSessionLocal() as db:
                service = MemoryJobsService(db)
                await service.run_daily_summary_job()
        except Exception as e:
            logger.error(f"Error in memory daily summary job: {e}", exc_info=True)

    async def _send_review_reminders(self, db):
        """
        向用户发送复习提醒通知
        """
        try:
            # 获取所有有需要复习节点的用户
            result = await db.execute(select(User).where(User.is_active))
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

    async def apply_inferred_preference_decay(self):
        """
        每周推断偏好衰减任务
        对所有用户的推断偏好应用衰减，避免历史反馈永久影响
        使用游标分页确保处理所有用户
        """
        logger.info("Starting weekly inferred preference decay job...")
        try:
            async with AsyncSessionLocal() as db:
                from app.services.personalization.inferred_preference_decay_service import (
                    InferredPreferenceDecayService,
                )

                decay_service = InferredPreferenceDecayService(db)

                # 游标分页：循环处理直到没有更多用户
                batch_size = 200
                total_stats = {"processed": 0, "changes": 0, "resets": 0, "errors": []}

                while True:
                    stats = await decay_service.apply_decay_batch(
                        limit=batch_size,
                        offset=total_stats["processed"]
                    )

                    total_stats["processed"] += stats["processed"]
                    total_stats["changes"] += stats["changes"]
                    total_stats["resets"] += stats["resets"]
                    total_stats["errors"].extend(stats["errors"])

                    # 如果本批处理的用户数少于 batch_size，说明已处理完
                    if stats["processed"] < batch_size:
                        break

                    # 防止无限循环的安全保护
                    if total_stats["processed"] > 100000:
                        logger.warning("Decay job processed over 100k users, stopping for safety")
                        break

                logger.info(
                    f"Weekly preference decay completed: "
                    f"processed={total_stats['processed']}, "
                    f"changes={total_stats['changes']}, "
                    f"resets={total_stats['resets']}, "
                    f"errors={len(total_stats['errors'])}"
                )

        except Exception as e:
            logger.error(f"Error in preference decay job: {e}", exc_info=True)

    # ========== 胶囊生成任务 ==========

    async def generate_daily_capsules(self):
        """
        每日胶囊生成任务
        为好奇心偏好 > 0.3 的活跃用户生成胶囊
        """
        logger.info("Starting daily capsule generation...")
        try:
            async with AsyncSessionLocal() as db:
                # 获取活跃用户（最近7天有活动）
                from datetime import timedelta
                cutoff_date = _utcnow() - timedelta(days=7)

                result = await db.execute(
                    select(User).where(
                        User.is_active,
                        User.last_active_at >= cutoff_date
                    )
                )
                users = result.scalars().all()

                pref_service = PreferenceService(db)
                stats = {
                    "total_users": len(users),
                    "eligible_users": 0,
                    "scheduled_jobs": 0,
                    "skipped_users": 0,
                }

                for user in users:
                    try:
                        # 获取用户好奇心偏好
                        prefs = await pref_service.get_preferences(user.id)
                        curiosity_pref = (prefs.explicit or {}).get("curiosity_preference", 0.5)

                        # 只为好奇心偏好 > 0.3 的用户生成
                        if curiosity_pref < 0.3:
                            stats["skipped_users"] += 1
                            continue

                        # 通过 Celery 异步生成
                        celery_app.send_task(
                            "generate_capsules_batch",
                            args=(
                                str(user.id),
                                0.5,  # depth_preference - 默认中等
                                curiosity_pref,
                                "daily",
                                1,  # 每日1个
                            ),
                            queue="default",
                        )
                        stats["eligible_users"] += 1
                        stats["scheduled_jobs"] += 1

                    except Exception as e:
                        logger.warning(f"Failed to schedule capsule for user {user.id}: {e}")
                        stats["skipped_users"] += 1

                logger.info(
                    f"Daily capsule generation completed: "
                    f"total={stats['total_users']}, "
                    f"eligible={stats['eligible_users']}, "
                    f"scheduled={stats['scheduled_jobs']}, "
                    f"skipped={stats['skipped_users']}"
                )

        except Exception as e:
            logger.error(f"Error in daily capsule generation: {e}", exc_info=True)

    async def generate_weekly_deep_capsules(self):
        """
        每周深度胶囊生成任务
        为深度偏好 > 0.7 的活跃用户生成深度胶囊
        """
        logger.info("Starting weekly deep capsule generation...")
        try:
            async with AsyncSessionLocal() as db:
                # 获取活跃用户（最近7天有活动）
                from datetime import timedelta
                cutoff_date = _utcnow() - timedelta(days=7)

                result = await db.execute(
                    select(User).where(
                        User.is_active,
                        User.last_active_at >= cutoff_date
                    )
                )
                users = result.scalars().all()

                pref_service = PreferenceService(db)
                stats = {
                    "total_users": len(users),
                    "eligible_users": 0,
                    "scheduled_jobs": 0,
                    "skipped_users": 0,
                }

                for user in users:
                    try:
                        # 获取用户偏好
                        prefs = await pref_service.get_preferences(user.id)
                        depth_pref = (prefs.explicit or {}).get("depth_preference", 0.5)
                        curiosity_pref = (prefs.explicit or {}).get("curiosity_preference", 0.5)

                        # 只为深度偏好 > 0.7 且好奇心偏好 > 0.3 的用户生成
                        if depth_pref <= 0.7 or curiosity_pref < 0.3:
                            stats["skipped_users"] += 1
                            continue

                        # 通过 Celery 异步生成深度胶囊
                        celery_app.send_task(
                            "generate_capsules_batch",
                            args=(
                                str(user.id),
                                depth_pref,
                                curiosity_pref,
                                "weekly",
                                2,  # 每周2个深度胶囊
                            ),
                            queue="default",
                        )
                        stats["eligible_users"] += 1
                        stats["scheduled_jobs"] += 1

                    except Exception as e:
                        logger.warning(f"Failed to schedule deep capsule for user {user.id}: {e}")
                        stats["skipped_users"] += 1

                logger.info(
                    f"Weekly deep capsule generation completed: "
                    f"total={stats['total_users']}, "
                    f"eligible={stats['eligible_users']}, "
                    f"scheduled={stats['scheduled_jobs']}, "
                    f"skipped={stats['skipped_users']}"
                )

        except Exception as e:
            logger.error(f"Error in weekly deep capsule generation: {e}", exc_info=True)


scheduler_service = SchedulerService()
