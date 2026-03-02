from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.core.cache import cache_service
from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.cognitive_pattern_mining_service import CognitivePatternMiningService
from app.services.cognitive_service import CognitiveService
from app.services.decay_service import DecayService
from app.services.event_retention_service import EventRetentionService
from app.services.expert_policy_report_service import ExpertPolicyReportService
from app.services.learning_feature_rollup_service import LearningFeatureRollupService
from app.services.memory_jobs import MemoryJobsService
from app.services.meta_learning_feature_service import MetaLearningFeatureService
from app.services.meta_policy_recommendation_service import MetaPolicyRecommendationService
from app.services.nightly_review_service import NightlyReviewService
from app.services.notification_service import NotificationService
from app.services.personalization.preference_service import PreferenceService
from app.services.policy_candidate_service import PolicyCandidateService
from app.services.policy_registry_service import PolicyRegistryService
from app.services.push_service import PushService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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

        if settings.ENABLE_LEARNING_CONTROL_PLANE:
            self.scheduler.add_job(
                self.run_learning_feature_rollup_job,
                "interval",
                minutes=max(5, int(getattr(settings, "LEARNING_ROLLUP_WINDOW_MINUTES", 30))),
            )
            if settings.ENABLE_POLICY_CANDIDATE_PIPELINE:
                self.scheduler.add_job(
                    self.run_policy_candidate_job,
                    "cron",
                    hour=int(getattr(settings, "LEARNING_POLICY_CANDIDATE_HOUR", 3)),
                    minute=int(getattr(settings, "LEARNING_POLICY_CANDIDATE_MINUTE", 40)),
                )
            self.scheduler.add_job(
                self.run_learning_weekly_report_job,
                "cron",
                day_of_week=str(getattr(settings, "LEARNING_WEEKLY_REPORT_WEEKDAY", "mon")),
                hour=int(getattr(settings, "LEARNING_WEEKLY_REPORT_HOUR", 4)),
                minute=int(getattr(settings, "LEARNING_WEEKLY_REPORT_MINUTE", 10)),
            )
            self.scheduler.add_job(
                self.run_research_benchmark_job,
                "cron",
                hour=int(getattr(settings, "LEARNING_RESEARCH_BENCHMARK_HOUR", 3)),
                minute=int(getattr(settings, "LEARNING_RESEARCH_BENCHMARK_MINUTE", 15)),
            )
            self.scheduler.add_job(
                self.run_research_promotion_package_job,
                "cron",
                day_of_week=str(getattr(settings, "LEARNING_RESEARCH_PROMOTION_WEEKDAY", "mon")),
                hour=int(getattr(settings, "LEARNING_RESEARCH_PROMOTION_HOUR", 4)),
                minute=int(getattr(settings, "LEARNING_RESEARCH_PROMOTION_MINUTE", 35)),
            )
            if bool(getattr(settings, "ENABLE_META_RULE_AUTO_MINING", False)):
                self.scheduler.add_job(
                    self.run_cognitive_pattern_mining_job,
                    "cron",
                    hour=int(getattr(settings, "LEARNING_META_RULE_MINING_HOUR", 2)),
                    minute=int(getattr(settings, "LEARNING_META_RULE_MINING_MINUTE", 50)),
                )

        # ========== 胶囊生成调度任务 ==========

        # 每日胶囊生成 (每天早上8点)
        self.scheduler.add_job(self.generate_daily_capsules, 'cron', hour=8, minute=0)

        # 每周深度胶囊 (每周日早上9点)
        self.scheduler.add_job(self.generate_weekly_deep_capsules, 'cron', day_of_week='sun', hour=9, minute=0)

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
                await service.run_decay_job(window_days=30)
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

    async def _run_learning_job_with_guard(self, job_name: str, runner):
        registry = PolicyRegistryService(redis_client=cache_service.redis)
        if not settings.ENABLE_LEARNING_CONTROL_PLANE:
            await registry.record_job_run(
                job=job_name,
                status="disabled",
                detail={"reason": "flag_off"},
            )
            return {"status": "disabled", "reason": "flag_off"}

        lock_key = f"learning-job:{job_name}"
        lock_acquired = False
        try:
            if cache_service.redis:
                async with cache_service.distributed_lock(lock_key, expire=1800):
                    lock_acquired = True
                    detail = await runner()
            else:
                detail = await runner()
            await registry.record_job_run(job=job_name, status="ok", detail=detail)
            return detail
        except Exception as exc:
            status = "skipped_lock" if not lock_acquired and cache_service.redis else "error"
            await registry.record_job_run(
                job=job_name,
                status=status,
                detail={"error": str(exc)},
            )
            logger.exception("Learning job {} failed: {}", job_name, exc)
            return {"status": status, "error": str(exc)}

    async def run_learning_feature_rollup_job(self):
        logger.info("Starting learning feature rollup job...")

        async def _runner():
            service = LearningFeatureRollupService(redis_client=cache_service.redis)
            summary = await service.run_rollup_job(
                window_minutes=max(5, int(getattr(settings, "LEARNING_ROLLUP_WINDOW_MINUTES", 30)))
            )
            guardrail = await self._evaluate_canary_guardrails()
            summary["canary_guardrail"] = guardrail
            return summary

        return await self._run_learning_job_with_guard("learning_feature_rollup", _runner)

    async def run_policy_candidate_job(self):
        logger.info("Starting policy candidate generation job...")

        async def _runner():
            service = PolicyCandidateService(redis_client=cache_service.redis)
            channels: list[str] = []
            if bool(getattr(settings, "ENABLE_META_LEARNING_CHANNEL_ROUTING", True)):
                channels.append("routing")
            if bool(getattr(settings, "ENABLE_META_LEARNING_CHANNEL_PROMPT", False)):
                channels.append("prompt")
            if bool(getattr(settings, "ENABLE_META_LEARNING_CHANNEL_TOOLCHAIN", False)):
                channels.append("toolchain")
            if not channels:
                channels = ["routing"]
            return await service.run_candidate_job(window_days=7, channels=channels)

        return await self._run_learning_job_with_guard("policy_candidate_generation", _runner)

    async def run_learning_weekly_report_job(self):
        logger.info("Starting learning weekly report job...")

        async def _runner():
            report_service = ExpertPolicyReportService(redis_client=cache_service.redis)
            rollup_service = LearningFeatureRollupService(redis_client=cache_service.redis)
            registry = PolicyRegistryService(redis_client=cache_service.redis)
            feature_service = MetaLearningFeatureService(redis_client=cache_service.redis)
            tuning_service = MetaPolicyRecommendationService(redis_client=cache_service.redis)
            report = await report_service.build_report(days=14)
            rollups = await rollup_service.list_rollups(days=14)
            stable_cohort_q_gap = float(report.get("stable_cohort_q_gap", 0.0) or 0.0)
            redline = float(getattr(settings, "FAIRNESS_STABLE_COHORT_Q_GAP_REDLINE", 0.08))
            feature_vectors = await feature_service.build_feature_vectors(days=14)
            payload = {
                "generated_at": _utcnow().isoformat(),
                "window_days": 14,
                "policy_report": report,
                "meta_feature_vector_count": len(feature_vectors),
                "meta_feature_vectors_top": feature_vectors[:100],
                "new_user_transfer_gain": self._estimate_transfer_gain_new_user(rollups),
                "channel_health": report.get("channel_health", {}),
                "rollback_recommendation": report.get("rollback_recommendation", {}),
                "long_tail_guardrail": {
                    "stable_cohort_q_gap": round(stable_cohort_q_gap, 4),
                    "redline": redline,
                    "is_healthy": stable_cohort_q_gap <= redline,
                },
                "failure_mode_topn": self._extract_failure_modes(rollups, limit=20),
                "tuning_package": await tuning_service.build_weekly_tuning_package(days=14),
                "summary": {
                    "fallback_rate": report.get("rates", {}).get("fallback_rate", 0.0),
                    "feedback_binding_rate": report.get("rates", {}).get("feedback_binding_rate", 0.0),
                },
            }
            payload["required_next_candidate_focus"] = [
                item.get("pattern", "")
                for item in payload.get("failure_mode_topn", [])[:3]
            ]
            await registry.save_weekly_report(payload)
            return payload

        return await self._run_learning_job_with_guard("learning_weekly_report", _runner)

    async def run_research_benchmark_job(self):
        logger.info("Starting research benchmark job...")

        async def _runner():
            report_service = ExpertPolicyReportService(redis_client=cache_service.redis)
            registry = PolicyRegistryService(redis_client=cache_service.redis)
            report = await report_service.build_report(days=14)
            pending = await registry.list_candidates(status="research_pending")
            passed = await registry.list_candidates(status="research_passed")
            payload = {
                "generated_at": _utcnow().isoformat(),
                "window_days": 14,
                "q_score_by_policy": report.get("q_score_by_policy", {}),
                "q_score_by_cohort": report.get("q_score_by_cohort", {}),
                "stable_cohort_q_gap": report.get("stable_cohort_q_gap", 0.0),
                "research_pending": len(pending),
                "research_passed": len(passed),
            }
            return payload

        return await self._run_learning_job_with_guard("learning_research_benchmark", _runner)

    async def run_research_promotion_package_job(self):
        logger.info("Starting research promotion package job...")

        async def _runner():
            registry = PolicyRegistryService(redis_client=cache_service.redis)
            pending = await registry.list_candidates(status="research_pending")
            passed = await registry.list_candidates(status="research_passed")
            recommendations: list[dict[str, Any]] = []

            for row in passed[:50]:
                recommendations.append(
                    {
                        "candidate_id": str(row.get("id", "")),
                        "policy_id": str(row.get("policy_id", "")),
                        "channel": str(row.get("channel", "routing")),
                        "scope_type": str(row.get("scope_type", "global")),
                        "risk_level": str(row.get("risk_level", "medium")),
                        "expected_delta": float(row.get("expected_delta", 0.0) or 0.0),
                        "action": "promote_to_canary",
                    }
                )

            return {
                "generated_at": _utcnow().isoformat(),
                "research_pending_count": len(pending),
                "research_passed_count": len(passed),
                "promotion_recommendations": recommendations,
            }

        return await self._run_learning_job_with_guard("learning_research_promotion_package", _runner)

    async def run_cognitive_pattern_mining_job(self):
        logger.info("Starting cognitive pattern mining job...")

        async def _runner():
            service = CognitivePatternMiningService(redis_client=cache_service.redis)
            return await service.run_mining_job(days=14)

        return await self._run_learning_job_with_guard("learning_cognitive_pattern_mining", _runner)

    async def _evaluate_canary_guardrails(self) -> dict[str, Any]:
        if not settings.ENABLE_POLICY_CANARY_ROLLOUT:
            return {"checked": 0, "rolled_back": 0, "reason": "canary_flag_off"}

        registry = PolicyRegistryService(redis_client=cache_service.redis)
        rollups = LearningFeatureRollupService(redis_client=cache_service.redis)
        canaries = await registry.list_policies(statuses={"canary"})
        if not canaries:
            return {"checked": 0, "rolled_back": 0}

        rows = await rollups.list_rollups(days=2)
        grouped: dict[str, dict[str, int]] = {}
        for row in rows:
            policy_id = str(row.get("policy_id", ""))
            counts = row.get("counts") if isinstance(row.get("counts"), dict) else {}
            target = grouped.setdefault(policy_id, {})
            for key, value in counts.items():
                target[key] = int(target.get(key, 0)) + int(value or 0)

        min_selected = int(getattr(settings, "LEARNING_CANARY_MIN_SELECTED", 30))
        fallback_limit = float(getattr(settings, "LEARNING_CANARY_MAX_FALLBACK_RATE", 0.12))
        negative_limit = float(getattr(settings, "LEARNING_CANARY_MAX_NEGATIVE_FEEDBACK_RATE", 0.55))

        checked = 0
        rolled_back = 0
        rolled_back_ids: list[str] = []
        fairness_q_gap = 0.0
        for policy in canaries:
            policy_id = str(policy.get("policy_id", ""))
            metrics = grouped.get(policy_id, {})
            selected = int(metrics.get("expert_selected", 0))
            if selected < min_selected:
                continue
            checked += 1
            fallback = int(metrics.get("expert_fallback", 0))
            feedback_up = int(metrics.get("feedback_up", 0))
            feedback_down = int(metrics.get("feedback_down", 0))
            feedback_total = feedback_up + feedback_down
            fallback_rate = (fallback / selected) if selected > 0 else 0.0
            negative_feedback_rate = (feedback_down / feedback_total) if feedback_total > 0 else 0.0

            if fallback_rate > fallback_limit or negative_feedback_rate > negative_limit:
                reason = (
                    f"guardrail_exceeded:fallback={fallback_rate:.3f},"
                    f"negative_feedback={negative_feedback_rate:.3f}"
                )
                rolled = await registry.rollback_policy(policy_id=policy_id, reason=reason)
                if rolled:
                    rolled_back += 1
                    rolled_back_ids.append(policy_id)
                    self._metric_policy_rollback(reason_type="guardrail_exceeded")

        if bool(getattr(settings, "ENABLE_META_FAIRNESS_GUARDRAIL", False)):
            by_cohort: dict[str, dict[str, float]] = {}
            for row in rows:
                cohort_id = str(row.get("cohort_id", "") or "")
                if not cohort_id:
                    continue
                counts = row.get("counts") if isinstance(row.get("counts"), dict) else {}
                selected = int(counts.get("expert_selected", 0))
                if selected <= 0:
                    continue
                q_score = float(row.get("q_score", 0.0) or 0.0)
                target = by_cohort.setdefault(cohort_id, {"selected": 0.0, "q_weighted": 0.0})
                target["selected"] += float(selected)
                target["q_weighted"] += q_score * float(selected)
            min_support_cohort = int(getattr(settings, "LONG_TAIL_COHORT_MIN_SUPPORT", 20))
            stable_values = []
            for stat in by_cohort.values():
                selected = int(stat["selected"])
                if selected < min_support_cohort:
                    continue
                stable_values.append(float(stat["q_weighted"]) / max(1.0, float(selected)))
            if stable_values:
                fairness_q_gap = max(stable_values) - min(stable_values)
            redline = float(getattr(settings, "FAIRNESS_STABLE_COHORT_Q_GAP_REDLINE", 0.08))
            if fairness_q_gap > redline:
                for policy in canaries:
                    policy_id = str(policy.get("policy_id", ""))
                    if policy_id in rolled_back_ids:
                        continue
                    rolled = await registry.rollback_policy(
                        policy_id=policy_id,
                        reason=f"fairness_redline_exceeded:q_gap={fairness_q_gap:.3f}",
                    )
                    if rolled:
                        rolled_back += 1
                        rolled_back_ids.append(policy_id)
                        self._metric_policy_rollback(reason_type="fairness_redline")

        try:
            from app.core.metrics import FAIRNESS_STABLE_Q_GAP
            FAIRNESS_STABLE_Q_GAP.set(float(fairness_q_gap))
        except Exception:
            pass

        return {
            "checked": checked,
            "rolled_back": rolled_back,
            "rolled_back_policy_ids": rolled_back_ids,
            "fairness_q_gap": round(fairness_q_gap, 4),
        }

    @staticmethod
    def _metric_policy_rollback(*, reason_type: str) -> None:
        try:
            from app.core.metrics import META_POLICY_ROLLBACK_TOTAL
            META_POLICY_ROLLBACK_TOTAL.labels(reason_type=str(reason_type)).inc()
        except Exception:
            return

    @staticmethod
    def _estimate_transfer_gain_new_user(rollups: list[dict[str, Any]]) -> float:
        baseline_scores: list[float] = []
        cold_start_scores: list[float] = []
        for row in rollups:
            try:
                q_score = float(row.get("q_score", 0.0) or 0.0)
            except (TypeError, ValueError):
                q_score = 0.0
            baseline_scores.append(q_score)
            counts = row.get("counts") if isinstance(row.get("counts"), dict) else {}
            if int(counts.get("cold_start_bootstrap_applied", 0)) > 0:
                cold_start_scores.append(q_score)

        baseline = (sum(baseline_scores) / len(baseline_scores)) if baseline_scores else 0.0
        cold_start = (sum(cold_start_scores) / len(cold_start_scores)) if cold_start_scores else baseline
        return round(cold_start - baseline, 4)

    @staticmethod
    def _extract_failure_modes(rollups: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
        merged: dict[str, int] = {}
        for row in rollups:
            patterns = row.get("failure_pattern_topn") if isinstance(row.get("failure_pattern_topn"), list) else []
            for item in patterns:
                if not isinstance(item, dict):
                    continue
                pattern = str(item.get("pattern", "")).strip()
                if not pattern:
                    continue
                try:
                    count = int(item.get("count", 0))
                except (TypeError, ValueError):
                    count = 0
                merged[pattern] = int(merged.get(pattern, 0)) + max(0, count)
        ordered = sorted(merged.items(), key=lambda pair: pair[1], reverse=True)
        return [{"pattern": pattern, "count": count} for pattern, count in ordered[: max(1, limit)]]


scheduler_service = SchedulerService()
