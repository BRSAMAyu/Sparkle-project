"""
Achievement Engine Service
成就引擎核心服务 - 处理成就解锁逻辑、连胜统计、契约管理
"""
from __future__ import annotations
import asyncio
import contextlib
from datetime import timezone, date, datetime, timedelta
from typing import Any, Awaitable, Callable

from loguru import logger
from sqlalchemy import event
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.event_bus import event_bus
from app.models.achievement import (
    Achievement,
    AchievementRarity,
    ContractStatus,
    SparkContract,
    StreakDayStatus,
    UserAchievement,
    UserGalaxySkin,
    UserStreakDay,
    UserStreakStats,
    UserTitle,
)
from app.models.community import GroupTaskClaim
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.session_completion import SessionCompletion
from app.models.subject import Subject
from app.services.achievement_reward_observability import AchievementRewardObservability
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


_EXTERNAL_TRANSACTION_MANAGED_KEY = "external_transaction_managed"
_AFTER_COMMIT_TASKS_KEY = "achievement_after_commit_tasks"


@event.listens_for(AsyncSession.sync_session_class, "after_commit")
def _run_achievement_after_commit_tasks(session) -> None:
    callbacks: list[Callable[[], Awaitable[None]]] = session.info.pop(_AFTER_COMMIT_TASKS_KEY, [])
    if not callbacks:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("Skipping achievement after-commit callbacks because no event loop is running")
        return

    for callback in callbacks:
        loop.create_task(callback())


@event.listens_for(AsyncSession.sync_session_class, "after_rollback")
@event.listens_for(AsyncSession.sync_session_class, "after_soft_rollback")
def _clear_achievement_after_commit_tasks(session, *_args) -> None:
    session.info.pop(_AFTER_COMMIT_TASKS_KEY, None)


class AchievementEvent:
    """成就事件类型"""
    TASK_COMPLETED = "task_completed"
    DAILY_CHECKIN = "daily_checkin"
    NODE_UNLOCKED = "node_unlocked"
    NODE_MASTERED = "node_mastered"
    STUDY_MINUTES_ACCUMULATED = "study_minutes_accumulated"
    NIGHT_STUDY = "night_study"  # 23:00-05:00
    EARLY_BIRD = "early_bird"    # 05:00-08:00
    WEEKEND_WARRIOR = "weekend_warrior"
    STREAK_MILESTONE = "streak_milestone"
    CONTRACT_COMPLETED = "contract_completed"
    CONTRACT_FAILED = "contract_failed"
    MUTUAL_STUDY = "mutual_study"  # 与搭子同时学习
    HIDDEN_TRIGGER = "hidden_trigger"  # 隐藏成就特殊触发
    # Sprint events
    SPRINT_STARTED = "sprint_started"
    SPRINT_COMPLETED = "sprint_completed"
    SPRINT_ABANDONED = "sprint_abandoned"
    SPRINT_PERFECT = "sprint_perfect"  # 100%完成
    SPRINT_STREAK = "sprint_streak"    # 连续冲刺
    SPRINT_AHEAD = "sprint_ahead"      # 超前完成
    # Enhancement events
    ACHIEVEMENT_COMBO = "achievement_combo"  # 连续解锁成就
    PROGRESS_MILESTONE = "progress_milestone"  # 进度里程碑
    PLAN_CREATED = "plan_created"


class AchievementEngine:
    """成就引擎 - 核心服务"""
    GROUP_TASK_WEIGHT_FACTOR = 0.7
    SUPPORTED_TRIGGER_CODES = {
        "ALL_SECTORS_UNLOCKED",
        "EARLY_BIRD",
        "NIGHT_OWL_STUDY",
        "NODES_MASTERED",
        "NODES_UNLOCKED",
        "PERFECTIONIST",
        "PLANS_TOTAL",
        "SECTOR_MASTERY",
        "SPEED_UNLOCK",
        "SPRINTS_STREAK",
        "SPRINTS_TOTAL",
        "SPRINT_AHEAD",
        "SPRINT_PERFECT",
        "STREAK_DAYS",
        "STUDY_MINUTES_SINGLE",
        "STUDY_MINUTES_TOTAL",
        "TASKS_TOTAL",
        "WEEKEND_WARRIOR",
    }
    SUPPORTED_REWARD_TYPES = {"freeze_charge", "galaxy_skin", "photon", "title", "visual_element"}
    PRESTIGE_LANES = {
        "streak": {"id": "streak_lane", "label": "连胜王者线", "color": "#FF8A3D", "x": 120},
        "sprint": {"id": "sprint_lane", "label": "冲刺战绩线", "color": "#2FB6FF", "x": 390},
        "conquest": {"id": "conquest_lane", "label": "探索征服线", "color": "#63E6BE", "x": 660},
        "hidden": {"id": "hidden_lane", "label": "隐藏猎人线", "color": "#B197FC", "x": 930},
        "prestige": {"id": "prestige_lane", "label": "声望进阶线", "color": "#FFD43B", "x": 1200},
    }
    CATEGORY_TO_LANE = {
        "streak": "streak",
        "sprint": "sprint",
        "exploration": "conquest",
        "mastery": "conquest",
        "study_time": "conquest",
        "hidden": "hidden",
        "tasks": "prestige",
    }

    # 成就定义缓存（内存缓存）
    _achievement_cache: dict[str, Achievement] = {}
    _cache_last_update: datetime = None
    _cache_ttl = timedelta(minutes=5)

    def __init__(self, db: AsyncSession):
        self.db = db

    def _enqueue_after_commit(self, callback: Callable[[], Awaitable[None]]) -> None:
        callbacks = self.db.sync_session.info.setdefault(_AFTER_COMMIT_TASKS_KEY, [])
        callbacks.append(callback)

    def _is_transaction_managed_externally(self) -> bool:
        return bool(self.db.sync_session.info.get(_EXTERNAL_TRANSACTION_MANAGED_KEY))

    @staticmethod
    def _coerce_activity_date(value: date | datetime | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value

    @staticmethod
    def _build_session_completion_key(
        user_id: str,
        event_type: str,
        **kwargs,
    ) -> tuple[str, str] | None:
        session_id = kwargs.get("session_id")
        if session_id and event_type in {
            AchievementEvent.STUDY_MINUTES_ACCUMULATED,
            AchievementEvent.NIGHT_STUDY,
            AchievementEvent.EARLY_BIRD,
        }:
            return (f"{user_id}:{event_type}:focus:{session_id}", "focus_session")

        if event_type == AchievementEvent.TASK_COMPLETED:
            task_id = kwargs.get("task_id")
            if task_id:
                return (f"{user_id}:{event_type}:task:{task_id}", "task_completion")

            group_task_id = kwargs.get("group_task_id")
            if group_task_id:
                return (f"{user_id}:{event_type}:group_task:{group_task_id}", "group_task_completion")

        return None

    async def _reserve_session_completion(
        self,
        user_id: str,
        event_type: str,
        **kwargs,
    ) -> bool:
        completion_key = self._build_session_completion_key(user_id, event_type, **kwargs)
        if completion_key is None:
            return True

        scoped_session_id, completion_type = completion_key
        values = {
            "session_id": scoped_session_id,
            "user_id": user_id,
            "completion_type": completion_type,
            "source_event": event_type,
        }

        bind = self.db.sync_session.get_bind()
        dialect_name = bind.dialect.name if bind is not None else ""

        if dialect_name == "postgresql":
            stmt = pg_insert(SessionCompletion).values(**values).on_conflict_do_nothing(
                index_elements=[SessionCompletion.session_id]
            )
            result = await self.db.execute(stmt)
            return bool(result.rowcount)

        if dialect_name == "sqlite":
            stmt = sqlite_insert(SessionCompletion).values(**values).on_conflict_do_nothing(
                index_elements=[SessionCompletion.session_id]
            )
            result = await self.db.execute(stmt)
            return bool(result.rowcount)

        try:
            async with self.db.begin_nested():
                self.db.add(SessionCompletion(**values))
                await self.db.flush()
            return True
        except IntegrityError:
            return False

    async def _refresh_achievement_cache(self):
        """刷新成就定义缓存"""
        now = _utcnow()
        if self._cache_last_update and (now - self._cache_last_update < self._cache_ttl):
            return

        query = select(Achievement)
        result = await self.db.execute(query)
        achievements = result.scalars().all()

        self._achievement_cache = {a.id: a for a in achievements}
        self._cache_last_update = now

    async def _get_achievement(self, achievement_id: str) -> Achievement | None:
        """获取成就定义（带缓存）"""
        await self._refresh_achievement_cache()
        return self._achievement_cache.get(achievement_id)

    async def _get_all_achievements(self) -> list[Achievement]:
        """获取所有成就定义（带缓存）"""
        await self._refresh_achievement_cache()
        return list(self._achievement_cache.values())

    def _is_achievement_active(self, achievement: Achievement, now: datetime) -> bool:
        if achievement.active_from and now < achievement.active_from:
            return False
        if achievement.active_to and now > achievement.active_to:
            return False
        return True

    async def process_event(
        self,
        user_id: str,
        event_type: str,
        **kwargs
    ) -> list[dict[str, Any]]:
        """
        处理用户事件，检查并解锁成就

        Args:
            user_id: 用户ID
            event_type: 事件类型
            **kwargs: 事件相关数据

        Returns:
            新解锁的成就列表，包含连击和里程碑信息
        """
        transaction_context = (
            self.db.begin_nested()
            if self._is_transaction_managed_externally()
            else contextlib.nullcontext()
        )

        async with transaction_context:
            if not await self._reserve_session_completion(user_id, event_type, **kwargs):
                return []

            # 1. 更新连胜统计
            await self._update_streak_stats(user_id, event_type, **kwargs)

            # 2. 获取相关成就定义
            relevant_achievements = await self._get_relevant_achievements(event_type)

            # 3. 检查每个成就的条件
            unlocked = []
            milestones = []  # 进度里程碑通知
            for achievement in relevant_achievements:
                # 检查是否已解锁
                if await self._is_unlocked(user_id, achievement.id):
                    continue

                # 检查前置条件
                if not await self._check_prerequisites(user_id, achievement):
                    continue

                # 评估进度
                progress, current_value, target_value = await self._evaluate_progress(
                    user_id, achievement, **kwargs
                )

                # 记录解锁前的进度，用于里程碑检测
                old_progress = await self._get_old_progress(user_id, achievement.id)

                # 更新或创建进度记录
                await self._update_progress(
                    user_id, achievement.id, progress, current_value, target_value
                )

                # 检查进度里程碑（每25%进度）
                milestone = await self._check_progress_milestone(
                    user_id, achievement, old_progress, progress
                )
                if milestone:
                    milestones.append(milestone)

                # 检查是否解锁
                if progress >= 1.0:
                    unlock_data = await self._unlock_achievement(user_id, achievement)
                    if unlock_data:
                        unlocked.append(unlock_data)

            # 4. 处理连击检测
            combo_info = None
            if unlocked:
                combo_info = await self._handle_achievement_combo(user_id, len(unlocked))
                # 将连击信息添加到每个解锁的成就中
                if combo_info:
                    for unlock_data in unlocked:
                        unlock_data["combo_info"] = combo_info

            # 5. 发送通知和触发视觉效果
            if unlocked:
                self._enqueue_after_commit(
                    lambda: self._notify_unlocks(user_id, unlocked)
                )

            # 6. 发送里程碑通知
            if milestones:
                self._enqueue_after_commit(
                    lambda: self._notify_milestones(user_id, milestones)
                )

            if self._is_transaction_managed_externally():
                await self.db.flush()
            else:
                await self.db.commit()

            return unlocked

    async def _get_relevant_achievements(self, event_type: str) -> list[Achievement]:
        """获取与事件类型相关的成就"""
        all_achievements = await self._get_all_achievements()

        relevant = []
        for achievement in all_achievements:
            # 检查触发代码是否匹配事件
            trigger_code = achievement.trigger_code

            # 直接匹配
            if trigger_code == event_type:
                relevant.append(achievement)
                continue

            # 特殊匹配逻辑
            match event_type:
                case AchievementEvent.TASK_COMPLETED:
                    if trigger_code in ["TASKS_TOTAL", "TASKS_COMPLETED", "WEEKEND_WARRIOR"]:
                        relevant.append(achievement)
                case AchievementEvent.DAILY_CHECKIN:
                    if trigger_code == "STREAK_DAYS":
                        relevant.append(achievement)
                case AchievementEvent.NODE_UNLOCKED:
                    if trigger_code in [
                        "ALL_SECTORS_UNLOCKED",
                        "NODES_UNLOCKED",
                        "SECTOR_MASTERY",
                        "SPEED_UNLOCK",
                    ]:
                        relevant.append(achievement)
                case AchievementEvent.NODE_MASTERED:
                    if trigger_code in ["NODES_MASTERED", "PERFECTIONIST", "SECTOR_MASTERY", "WEEKEND_WARRIOR"]:
                        relevant.append(achievement)
                case AchievementEvent.STUDY_MINUTES_ACCUMULATED:
                    if trigger_code in ["STUDY_MINUTES_TOTAL", "STUDY_MINUTES_SINGLE", "WEEKEND_WARRIOR"]:
                        relevant.append(achievement)
                case AchievementEvent.NIGHT_STUDY:
                    if trigger_code == "NIGHT_OWL_STUDY":
                        relevant.append(achievement)
                case AchievementEvent.EARLY_BIRD:
                    if trigger_code == "EARLY_BIRD":
                        relevant.append(achievement)
                case AchievementEvent.STREAK_MILESTONE:
                    if trigger_code == "STREAK_DAYS":
                        relevant.append(achievement)
                # Sprint event matching
                case AchievementEvent.SPRINT_COMPLETED:
                    if trigger_code in ["SPRINTS_TOTAL", "SPRINTS_COMPLETED"]:
                        relevant.append(achievement)
                case AchievementEvent.SPRINT_PERFECT:
                    if trigger_code in ["SPRINTS_TOTAL", "SPRINTS_COMPLETED", "SPRINT_PERFECT"]:
                        relevant.append(achievement)
                case AchievementEvent.SPRINT_STREAK:
                    if trigger_code in ["SPRINTS_TOTAL", "SPRINTS_STREAK"]:
                        relevant.append(achievement)
                case AchievementEvent.SPRINT_AHEAD:
                    if trigger_code in ["SPRINTS_TOTAL", "SPRINT_AHEAD"]:
                        relevant.append(achievement)
                case AchievementEvent.PLAN_CREATED:
                    if trigger_code == "PLANS_TOTAL":
                        relevant.append(achievement)
        return relevant

    async def _get_user_achievement_progress(
        self, user_id: str, achievement_id: str
    ) -> UserAchievement | None:
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _extract_session_hour(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return None
        if isinstance(value, datetime):
            return value.hour
        return None

    @staticmethod
    def _weekend_bucket_for(ts: datetime) -> date | None:
        day = ts.date()
        weekday = day.weekday()
        if weekday == 5:
            return day
        if weekday == 6:
            return day - timedelta(days=1)
        return None

    @classmethod
    def _calculate_weekend_streak(cls, timestamps: list[datetime]) -> int:
        buckets = sorted({cls._weekend_bucket_for(ts) for ts in timestamps if cls._weekend_bucket_for(ts)})
        if not buckets:
            return 0

        max_streak = 1
        current_streak = 1
        for previous, current in zip(buckets, buckets[1:], strict=False):
            if (current - previous).days == 7:
                current_streak += 1
            else:
                current_streak = 1
            max_streak = max(max_streak, current_streak)

        return max_streak

    async def _is_unlocked(self, user_id: str, achievement_id: str) -> bool:
        """检查成就是否已解锁"""
        cache_key = f"{settings.APP_NAME}:achievement:{user_id}:{achievement_id}:unlocked"
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return cached

        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
                UserAchievement.unlocked_at.isnot(None)
            )
        )
        result = await self.db.execute(query)
        unlocked = result.scalar_one_or_none() is not None

        await cache_service.set(cache_key, unlocked, ttl=300)
        return unlocked

    async def _check_prerequisites(self, user_id: str, achievement: Achievement) -> bool:
        """检查前置成就是否已解锁"""
        if not achievement.prerequisites:
            return True

        for prereq_id in achievement.prerequisites:
            if not await self._is_unlocked(user_id, prereq_id):
                return False
        return True

    async def _evaluate_progress(
        self,
        user_id: str,
        achievement: Achievement,
        **kwargs
    ) -> tuple[float, int, int]:
        """
        评估成就进度

        Returns:
            (progress, current_value, target_value)
        """
        config = achievement.trigger_config or {}
        trigger_code = achievement.trigger_code

        match trigger_code:
            # 连续学习天数
            case "STREAK_DAYS":
                stats = await self._get_or_create_streak_stats(user_id)
                target = config.get("days", 30)
                current = stats.current_streak
                return (min(current / target, 1.0), current, target)

            # 任务完成数量
            case "TASKS_TOTAL":
                from app.models.task import Task, TaskStatus
                target = config.get("count", 10)
                claim_ids_query = select(GroupTaskClaim.personal_task_id).where(
                    GroupTaskClaim.user_id == user_id,
                    GroupTaskClaim.personal_task_id.is_not(None),
                )
                solo_query = select(func.count()).select_from(Task).where(
                    and_(
                        Task.user_id == user_id,
                        Task.status == TaskStatus.COMPLETED,
                        Task.id.not_in(claim_ids_query),
                    )
                )
                group_query = select(func.count()).select_from(GroupTaskClaim).where(
                    and_(
                        GroupTaskClaim.user_id == user_id,
                        GroupTaskClaim.is_completed.is_(True),
                    )
                )
                solo_result = await self.db.execute(solo_query)
                group_result = await self.db.execute(group_query)
                solo_completed = int(solo_result.scalar_one() or 0)
                group_completed = int(group_result.scalar_one() or 0)
                effective_total = solo_completed + (group_completed * self.GROUP_TASK_WEIGHT_FACTOR)
                progress = min(effective_total / target, 1.0)
                return (progress, int(round(effective_total)), target)

            case "PLANS_TOTAL":
                from app.models.plan import Plan

                target = config.get("count", 1)
                query = select(func.count()).select_from(Plan).where(Plan.user_id == user_id)
                result = await self.db.execute(query)
                current = int(result.scalar_one() or 0)
                return (min(current / target, 1.0), current, target)

            # 知识点数量
            case "NODES_UNLOCKED":
                target = config.get("count", 100)
                query = select(func.count()).select_from(UserNodeStatus).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.is_unlocked
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
                return (min(current / target, 1.0), current, target)

            # 知识点掌握数量
            case "NODES_MASTERED":
                target = config.get("count", 50)
                mastery_threshold = config.get("mastery_threshold", 80)
                query = select(func.count()).select_from(UserNodeStatus).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.mastery_score >= mastery_threshold
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
                return (min(current / target, 1.0), current, target)

            # 领域精通
            case "SECTOR_MASTERY":
                sector = config.get("sector")
                mastery_threshold = config.get("percent", 80)
                target = config.get("count", 20)
                query = select(func.count()).select_from(UserNodeStatus).join(
                    KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id
                ).join(
                    Subject, KnowledgeNode.subject_id == Subject.id
                ).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        Subject.sector_code == sector,
                        UserNodeStatus.is_unlocked,
                        UserNodeStatus.mastery_score >= mastery_threshold,
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
                return (min(current / target, 1.0), current, target)

            # 学习时长累计
            case "STUDY_MINUTES_TOTAL":
                target = config.get("minutes", 1000)
                query = select(func.coalesce(func.sum(UserNodeStatus.total_study_minutes), 0)).where(
                    UserNodeStatus.user_id == user_id
                )
                result = await self.db.execute(query)
                total = result.scalar_one() or 0
                return (min(total / target, 1.0), total, target)

            # 单次学习时长
            case "STUDY_MINUTES_SINGLE":
                target = config.get("minutes", 60)
                current = kwargs.get("study_minutes", 0)
                return (min(current / target, 1.0), current, target)

            # 深夜学习（隐藏成就）
            case "NIGHT_OWL_STUDY":
                hour = self._extract_session_hour(kwargs.get("session_start_time"))
                target = config.get("sessions", 10)
                progress_record = await self._get_user_achievement_progress(user_id, achievement.id)
                current = progress_record.progress_value if progress_record else 0
                if hour is not None and (hour >= 23 or hour < 5):
                    # 检查累计次数
                    cache_key = f"night_owl:{user_id}"
                    count = max(await cache_service.get(cache_key) or 0, current) + 1
                    await cache_service.set(cache_key, count, ttl=86400 * 30)
                    return (min(count / target, 1.0), count, target)
                return (min(current / target, 1.0), current, target)

            case "EARLY_BIRD":
                hour = self._extract_session_hour(kwargs.get("session_start_time"))
                target = config.get("sessions", 10)
                progress_record = await self._get_user_achievement_progress(user_id, achievement.id)
                current = progress_record.progress_value if progress_record else 0
                if hour is not None and 5 <= hour < 8:
                    cache_key = f"early_bird:{user_id}"
                    count = max(await cache_service.get(cache_key) or 0, current) + 1
                    await cache_service.set(cache_key, count, ttl=86400 * 30)
                    return (min(count / target, 1.0), count, target)
                return (min(current / target, 1.0), current, target)

            case "SPEED_UNLOCK":
                target = config.get("count", 20)
                hours = config.get("hours", 24)
                window_start = _utcnow() - timedelta(hours=hours)
                query = select(func.count()).select_from(UserNodeStatus).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.is_unlocked,
                        UserNodeStatus.first_unlock_at.isnot(None),
                        UserNodeStatus.first_unlock_at >= window_start,
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
                return (min(current / target, 1.0), current, target)

            case "ALL_SECTORS_UNLOCKED":
                sectors = config.get("sectors", [])
                target = len(sectors)
                if target == 0:
                    return (0.0, 0, 1)

                query = select(func.distinct(Subject.sector_code)).select_from(UserNodeStatus).join(
                    KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id
                ).join(
                    Subject, KnowledgeNode.subject_id == Subject.id
                ).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.is_unlocked,
                        Subject.sector_code.in_(sectors),
                    )
                )
                result = await self.db.execute(query)
                current = len(result.scalars().all())
                return (min(current / target, 1.0), current, target)

            case "WEEKEND_WARRIOR":
                from app.models.focus import FocusSession, FocusStatus
                from app.models.task import Task, TaskStatus

                target = config.get("consecutive_weekends", 4)
                timestamps: list[datetime] = []

                focus_result = await self.db.execute(
                    select(FocusSession.start_time).where(
                        and_(
                            FocusSession.user_id == user_id,
                            FocusSession.status == FocusStatus.COMPLETED,
                        )
                    )
                )
                timestamps.extend(ts for ts in focus_result.scalars().all() if ts is not None)

                task_result = await self.db.execute(
                    select(Task.completed_at).where(
                        and_(
                            Task.user_id == user_id,
                            Task.status == TaskStatus.COMPLETED,
                            Task.completed_at.isnot(None),
                        )
                    )
                )
                timestamps.extend(ts for ts in task_result.scalars().all() if ts is not None)

                study_result = await self.db.execute(
                    select(StudyRecord.created_at).where(StudyRecord.user_id == user_id)
                )
                timestamps.extend(ts for ts in study_result.scalars().all() if ts is not None)

                current = self._calculate_weekend_streak(timestamps)
                return (min(current / target, 1.0), current, target)

            # 完美主义者（单节点100%掌握度）
            case "PERFECTIONIST":
                node_id = kwargs.get("node_id")
                if node_id:
                    status = await self.db.get(UserNodeStatus, {
                        "user_id": user_id,
                        "node_id": node_id
                    })
                    if status and status.mastery_score >= 100:
                        return (1.0, 100, 100)
                return (0.0, 0, 100)

            # ========== Sprint Achievement Triggers ==========
            # 冲刺完成总数
            case "SPRINTS_TOTAL":
                from app.models.plan import Plan, PlanType
                target = config.get("count", 1)
                query = select(func.count()).select_from(Plan).where(
                    and_(
                        Plan.user_id == user_id,
                        Plan.type == PlanType.SPRINT,
                        Plan.is_active.is_(False),
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
                return (min(current / target, 1.0), current, target)

            # 完美冲刺（100%完成率）
            case "SPRINT_PERFECT":
                from app.models.plan import Plan, PlanType
                target = config.get("count", 1)
                # 查询完成率为100%的冲刺
                query = select(func.count()).select_from(Plan).where(
                    and_(
                        Plan.user_id == user_id,
                        Plan.type == PlanType.SPRINT,
                        Plan.is_active.is_(False),
                        Plan.progress >= 1.0
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
                return (min(current / target, 1.0), current, target)

            # 连续冲刺（连续完成多个冲刺）
            case "SPRINTS_STREAK":
                from app.models.plan import Plan, PlanType
                target = config.get("streak", 3)

                # 获取最近归档的冲刺（按archived_at降序）
                query = select(Plan).where(
                    and_(
                        Plan.user_id == user_id,
                        Plan.type == PlanType.SPRINT,
                        Plan.is_active.is_(False)
                    )
                ).order_by(Plan.updated_at.desc())

                result = await self.db.execute(query)
                sprints = result.scalars().all()

                # 计算连续完成的冲刺（progress >= 0.8视为完成）
                streak = 0
                for sprint in sprints:
                    if sprint.progress >= 0.8:
                        streak += 1
                    else:
                        break  # 断开连续

                current = streak
                return (min(current / target, 1.0), current, target)

            # 超前完成（提前完成冲刺）
            case "SPRINT_AHEAD":
                # 这个在事件触发时检查，这里返回当前值
                completion_rate = kwargs.get("completion_rate", 0.0)
                days_ahead = kwargs.get("days_ahead", 0)

                # 检查是否100%完成且提前至少1天
                if completion_rate >= 1.0 and days_ahead > 0:
                    return (1.0, days_ahead, 1)

                # 统计历史超前完成次数
                from app.models.plan import Plan, PlanType
                query = select(func.count()).select_from(Plan).where(
                    and_(
                        Plan.user_id == user_id,
                        Plan.type == PlanType.SPRINT,
                        Plan.is_active.is_(False),
                        Plan.progress >= 1.0,
                        Plan.target_date.isnot(None)
                    )
                )
                result = await self.db.execute(query)
                total = result.scalar_one() or 0

                # 估算超前完成数（这里简化处理，实际应用中需要更精确的记录）
                target = config.get("count", 1)
                progress = min(total / target, 1.0) if total > 0 else 0.0
                return (progress, total, target)

            case _:
                logger.warning(f"Unknown trigger code: {trigger_code}")
                return (0.0, 0, 1)

    async def _update_progress(
        self,
        user_id: str,
        achievement_id: str,
        progress: float,
        current_value: int,
        target_value: int
    ):
        """更新或创建进度记录"""
        # 检查是否已有记录
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id
            )
        )
        result = await self.db.execute(query)
        user_achievement = result.scalar_one_or_none()

        if user_achievement:
            # 更新现有记录
            user_achievement.progress = min(progress, 1.0)
            user_achievement.progress_value = current_value
            user_achievement.progress_target = target_value
            user_achievement.last_progress_update = _utcnow()
        else:
            # 创建新记录
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement_id,
                progress=min(progress, 1.0),
                progress_value=current_value,
                progress_target=target_value,
                last_progress_update=_utcnow()
            )
            self.db.add(user_achievement)

        await self.db.flush()

    async def _unlock_achievement(
        self,
        user_id: str,
        achievement: Achievement
    ) -> dict[str, Any] | None:
        """解锁成就"""
        now = _utcnow()

        locked_achievement_result = await self.db.execute(
            select(Achievement)
            .where(Achievement.id == achievement.id)
            .with_for_update()
        )
        locked_achievement = locked_achievement_result.scalar_one()

        # 更新用户成就记录
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            )
        ).with_for_update()
        result = await self.db.execute(query)
        user_achievement = result.scalar_one_or_none()

        if user_achievement and user_achievement.unlocked_at is not None:
            return None

        if not user_achievement:
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=locked_achievement.id,
                progress=1.0,
                unlocked_at=now,
                last_progress_update=now,
            )
            self.db.add(user_achievement)
        else:
            user_achievement.unlocked_at = now
            user_achievement.progress = 1.0
            user_achievement.last_progress_update = now

        # 检查是否首位解锁者
        is_first = False
        if not locked_achievement.first_unlocker_id:
            locked_achievement.first_unlocker_id = user_id
            user_achievement.is_first_unlocker = True
            is_first = True

        # 更新全局统计
        locked_achievement.total_unlocked += 1
        await self.db.flush()

        # 处理奖励
        await self._grant_rewards(user_id, locked_achievement)
        reward_preview = self._build_reward_preview(locked_achievement.reward_config)
        surface_preview = self._surface_preview_for_rewards(locked_achievement.reward_config)
        unlock_payload = {
            "achievement_id": locked_achievement.id,
            "name": locked_achievement.name,
            "rarity": locked_achievement.rarity,
            "visual_effect": locked_achievement.visual_config,
            "visual_effect_type": locked_achievement.visual_effect_type,
            "rewards": locked_achievement.reward_config,
            "reward_preview": reward_preview,
            "surface_preview": surface_preview,
            "is_first": is_first,
            "unlocked_at": now,
        }

        self._enqueue_after_commit(
            lambda: self._finalize_unlock_side_effects(user_id, unlock_payload)
        )

        return unlock_payload

    async def _finalize_unlock_side_effects(self, user_id: str, unlock_payload: dict[str, Any]) -> None:
        cache_key = f"{settings.APP_NAME}:achievement:{user_id}:{unlock_payload['achievement_id']}:unlocked"
        await cache_service.delete(cache_key)
        await cache_service.delete_pattern(
            f"{settings.APP_NAME}:achievement:{user_id}:*"
        )
        await self._broadcast_unlock_signals(user_id, unlock_payload)

    async def _broadcast_unlock_signals(self, user_id: str, unlock_payload: dict[str, Any]) -> None:
        try:
            rarity = unlock_payload.get("rarity")
            rarity_value = rarity.value if hasattr(rarity, "value") else str(rarity)
            await event_bus.publish(
                "achievement.unlocked",
                {
                    "event_type": "achievement.unlocked",
                    "user_id": str(user_id),
                    "achievement_id": unlock_payload["achievement_id"],
                    "achievement_name": unlock_payload["name"],
                    "achievement_type": "achievement_unlock",
                    "rarity": rarity_value,
                    "visual_effect_type": unlock_payload.get("visual_effect_type"),
                    "trigger_reason": "achievement_condition_met",
                    "timestamp": _utcnow().isoformat(),
                },
            )
            await SystemUpdateService().enqueue(
                user_id,
                build_system_update(
                    update_type="achievement_unlocked",
                    category="evolution",
                    title=f"解锁成就：{unlock_payload['name']}",
                    description=f"你刚刚解锁了「{unlock_payload['name']}」，这意味着你在相关领域已经取得了实质性进步。",
                    priority="low",
                    metadata={
                        "evolution_kind": "highlight",
                        "highlight": f"你刚刚解锁了「{unlock_payload['name']}」。",
                        "source": "achievement_engine",
                        "rarity": rarity_value,
                    },
                ),
            )
        except Exception as exc:
            logger.warning(f"Failed to broadcast achievement unlock signals: {exc}")

    async def _schedule_photon_reward_retry(
        self,
        *,
        user_id: str,
        achievement_id: str,
        achievement_name: str,
        quantity: int,
        error_message: str | None = None,
    ) -> None:
        await AchievementRewardObservability.record_event(
            status="scheduled",
            channel="post_commit",
            user_id=user_id,
            achievement_id=achievement_id,
            achievement_name=achievement_name,
            quantity=quantity,
            error_message=error_message,
        )

        payload = {
            "user_id": str(user_id),
            "achievement_id": achievement_id,
            "achievement_name": achievement_name,
            "quantity": quantity,
        }

        try:
            from app.core.celery_tasks import retry_achievement_photon_reward

            retry_achievement_photon_reward.delay(**payload)
            await AchievementRewardObservability.record_event(
                status="enqueued",
                channel="celery",
                user_id=user_id,
                achievement_id=achievement_id,
                achievement_name=achievement_name,
                quantity=quantity,
            )
            logger.info(
                "Queued photon reward compensation for achievement %s and user %s",
                achievement_id,
                user_id,
            )
            return
        except Exception as exc:
            logger.warning(
                "Failed to enqueue photon reward compensation for achievement %s: %s. Falling back to local retry.",
                achievement_id,
                exc,
            )
            await AchievementRewardObservability.record_event(
                status="enqueue_failed",
                channel="celery",
                user_id=user_id,
                achievement_id=achievement_id,
                achievement_name=achievement_name,
                quantity=quantity,
                error_message=str(exc),
            )

        await self._retry_photon_reward_locally(**payload)

    async def _retry_photon_reward_locally(
        self,
        *,
        user_id: str,
        achievement_id: str,
        achievement_name: str,
        quantity: int,
    ) -> None:
        from app.db.session import AsyncSessionLocal
        from app.services.photon_service import PhotonService, PhotonTransactionType

        delay_seconds = 1
        for attempt in range(1, 4):
            try:
                async with AsyncSessionLocal() as session:
                    photon_service = PhotonService(session)
                    await photon_service.grant_photons(
                        user_id=user_id,
                        amount=quantity,
                        source=f"achievement:{achievement_id}",
                        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
                        metadata={"achievement_name": achievement_name},
                        related_item_id=achievement_id,
                        record_history=True,
                    )
                logger.info(
                    "Photon reward compensation succeeded for achievement %s on local retry attempt %s",
                    achievement_id,
                    attempt,
                )
                await AchievementRewardObservability.record_event(
                    status="retry_succeeded",
                    channel="local",
                    user_id=user_id,
                    achievement_id=achievement_id,
                    achievement_name=achievement_name,
                    quantity=quantity,
                    attempt=attempt,
                )
                return
            except Exception as exc:
                logger.warning(
                    "Photon reward local retry %s failed for achievement %s: %s",
                    attempt,
                    achievement_id,
                    exc,
                )
                await AchievementRewardObservability.record_event(
                    status="retry_failed",
                    channel="local",
                    user_id=user_id,
                    achievement_id=achievement_id,
                    achievement_name=achievement_name,
                    quantity=quantity,
                    attempt=attempt,
                    error_message=str(exc),
                )
                if attempt == 3:
                    break
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2

        logger.error(
            "Photon reward compensation exhausted retries for achievement %s and user %s",
            achievement_id,
            user_id,
        )
        await AchievementRewardObservability.record_event(
            status="exhausted",
            channel="local",
            user_id=user_id,
            achievement_id=achievement_id,
            achievement_name=achievement_name,
            quantity=quantity,
            attempt=3,
        )

    async def _grant_rewards(self, user_id: str, achievement: Achievement):
        """发放奖励"""
        if not achievement.reward_config:
            return

        rewards = achievement.reward_config if isinstance(achievement.reward_config, list) else achievement.reward_config.get("rewards", [])

        for reward in rewards:
            reward_type = reward.get("type")

            match reward_type:
                case "title":
                    # 解锁称号
                    title_id = reward.get("value") or f"title_{achievement.id}"
                    await self._unlock_title(
                        user_id, title_id,
                        reward.get("display", achievement.name),
                        achievement.id
                    )

                case "galaxy_skin":
                    # 解锁星系皮肤
                    skin_id = reward.get("skin_id")
                    if skin_id:
                        await self._unlock_galaxy_skin(user_id, skin_id)

                case "freeze_charge":
                    # 增加连胜保护卡
                    quantity = reward.get("quantity", 1)
                    stats = await self._get_or_create_streak_stats(user_id)
                    stats.freeze_charges = min(
                        stats.freeze_charges + quantity,
                        stats.max_freeze_charges
                    )
                    await self.db.flush()

                case "photon":
                    from app.services.photon_service import PhotonService, PhotonTransactionType

                    photon_service = PhotonService(self.db)
                    quantity = int(reward.get("quantity", 0) or 0)
                    if quantity <= 0:
                        continue

                    await photon_service.grant_photons(
                        user_id=user_id,
                        amount=quantity,
                        source=f"achievement:{achievement.id}",
                        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
                        metadata={"achievement_name": achievement.name},
                        related_item_id=achievement.id,
                        record_history=True,
                        manage_transaction=False,
                    )

                    logger.info(f"Granted {quantity} photons to user {user_id} for achievement {achievement.id}")

                case "visual_element":
                    # 解锁视觉元素
                    element_id = reward.get("element_id")
                    if element_id:
                        await self._unlock_visual_element(user_id, element_id, achievement.id)

    async def _unlock_title(self, user_id: str, title_id: str, display: str, achievement_id: str):
        """解锁称号"""
        query = select(UserTitle).where(
            and_(
                UserTitle.user_id == user_id,
                UserTitle.title_id == title_id
            )
        )
        result = await self.db.execute(query)
        user_title = result.scalar_one_or_none()

        if not user_title:
            user_title = UserTitle(
                user_id=user_id,
                title_id=title_id,
                title_name=display,
                title_display=display,
                source_achievement_id=achievement_id,
                unlocked_at=_utcnow()
            )
            self.db.add(user_title)
            await self.db.flush()

    async def _unlock_galaxy_skin(self, user_id: str, skin_id: str):
        """解锁星系皮肤"""
        query = select(UserGalaxySkin).where(
            and_(
                UserGalaxySkin.user_id == user_id,
                UserGalaxySkin.skin_id == skin_id
            )
        )
        result = await self.db.execute(query)
        user_skin = result.scalar_one_or_none()

        if not user_skin:
            user_skin = UserGalaxySkin(
                user_id=user_id,
                skin_id=skin_id,
                unlocked_at=_utcnow(),
                unlock_source="achievement"
            )
            self.db.add(user_skin)
            await self.db.flush()

    async def _unlock_visual_element(self, user_id: str, element_id: str, achievement_id: str):
        """解锁视觉元素"""
        from app.schemas.visual_element import UnlockElementRequest
        from app.services.visual_element_service import VisualElementService

        visual_service = VisualElementService(self.db)
        response = await visual_service.unlock_element(
            user_id=user_id,
            request=UnlockElementRequest(
                element_id=element_id,
                source="achievement",
                source_id=achievement_id,
            ),
        )
        if response.success:
            logger.info(f"Unlocked visual element {element_id} for user {user_id} via achievement {achievement_id}")

    async def _notify_unlocks(self, user_id: str, unlocked: list[dict]):
        """发送成就解锁通知"""
        from app.core.websocket import get_ws_manager

        ws_manager = get_ws_manager()

        for unlock in unlocked:
            logger.info(f"Achievement unlocked for user {user_id}: {unlock['name']}")

            # 提取光子奖励信息（显式）
            photon_granted = 0
            rewards = unlock.get("rewards", [])
            if rewards:
                for reward in rewards:
                    if reward.get("type") == "photon":
                        photon_granted = reward.get("quantity", 0)
                        break
            glory_lines = self._build_glory_lines(unlock)

            # 通过 WebSocket 发送成就解锁事件
            message = {
                "type": "achievement_unlock",
                "achievement_data": {
                    "achievement_id": unlock["achievement_id"],
                    "name": unlock["name"],
                    "rarity": unlock["rarity"].value if hasattr(unlock["rarity"], "value") else unlock["rarity"],
                    "visual_effect": unlock.get("visual_effect"),
                    "visual_effect_type": unlock.get("visual_effect_type"),
                    "rewards": unlock.get("rewards"),
                    "reward_preview": unlock.get("reward_preview"),
                    "surface_preview": unlock.get("surface_preview"),
                    "is_first": unlock.get("is_first", False),
                    "unlocked_at": unlock["unlocked_at"].isoformat() if isinstance(unlock["unlocked_at"], datetime) else unlock["unlocked_at"],
                    # 添加连击信息
                    "combo_info": unlock.get("combo_info"),
                    "glory_lines": glory_lines,
                    # 显式添加光子奖励信息
                    "photon_granted": photon_granted,
                    "has_photon_reward": photon_granted > 0
                }
            }

            # 使用 WebSocket 发送
            try:
                await ws_manager.send_personal_message(message, user_id)
                logger.debug(f"Sent achievement unlock notification to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send achievement unlock notification: {e}")

    async def _upsert_streak_day(
        self,
        user_id: str,
        day: date,
        status: StreakDayStatus,
        used_freeze: bool = False,
        source_event: str | None = None,
    ) -> None:
        query = select(UserStreakDay).where(
            and_(
                UserStreakDay.user_id == user_id,
                UserStreakDay.day == day,
                UserStreakDay.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(query)
        record = result.scalar_one_or_none()
        persisted_status = status.value if hasattr(status, "value") else status

        if record:
            record.status = persisted_status
            record.used_freeze = used_freeze
            record.source_event = source_event
        else:
            record = UserStreakDay(
                user_id=user_id,
                day=day,
                status=persisted_status,
                used_freeze=used_freeze,
                source_event=source_event,
            )
            self.db.add(record)

        await self.db.flush()

    async def _update_streak_stats(self, user_id: str, event_type: str, **kwargs):
        """更新连胜统计"""
        stats = await self._get_or_create_streak_stats(user_id)
        today = _utcnow().date()
        last_activity_date = self._coerce_activity_date(stats.last_activity_date)
        if last_activity_date != stats.last_activity_date:
            stats.last_activity_date = last_activity_date

        # 只有核心活动才更新连胜
        if event_type not in [AchievementEvent.DAILY_CHECKIN,
                              AchievementEvent.TASK_COMPLETED,
                              AchievementEvent.NODE_MASTERED]:
            return

        if not last_activity_date:
            stats.current_streak = 1
            stats.max_streak = max(int(stats.max_streak or 0), 1)
            stats.longest_streak = max(int(stats.longest_streak or 0), 1)
            stats.total_checkin_days = max(int(stats.total_checkin_days or 0), 1)
            stats.last_activity_date = today
            stats.longest_streak_start = today
            stats.longest_streak_end = today
            await self._upsert_streak_day(
                user_id,
                today,
                StreakDayStatus.ACTIVE,
                source_event=event_type,
            )
            await self.db.flush()
            return

        delta = (today - last_activity_date).days

        if delta == 0:
            # 今天已活动，无需更新
            await self._upsert_streak_day(
                user_id,
                today,
                StreakDayStatus.ACTIVE,
                source_event=event_type,
            )
            return
        elif delta == 1:
            # 连续活动
            stats.current_streak += 1
            stats.max_streak = max(stats.current_streak, stats.max_streak)
            stats.total_checkin_days += 1

            # 更新最长连胜记录
            if stats.current_streak > stats.longest_streak:
                stats.longest_streak = stats.current_streak
                stats.longest_streak_start = stats.longest_streak_start or today
                stats.longest_streak_end = today

            await self._upsert_streak_day(
                user_id,
                today,
                StreakDayStatus.ACTIVE,
                source_event=event_type,
            )
        else:
            # 演了活动，检查保护卡
            days_missed = delta - 1

            if stats.freeze_charges >= days_missed:
                # 使用保护卡
                stats.freeze_charges -= days_missed
                stats.last_freeze_used_at = _utcnow()
                stats.current_streak += 1  # 今天也算
                logger.info(f"User {user_id} used {days_missed} freeze charges")

                for offset in range(1, days_missed + 1):
                    day = last_activity_date + timedelta(days=offset)
                    await self._upsert_streak_day(
                        user_id,
                        day,
                        StreakDayStatus.FROZEN,
                        used_freeze=True,
                        source_event="freeze",
                    )
            else:
                # 保护不足，连胜断裂
                stats.current_streak = 1
                logger.info(f"User {user_id} streak broken at {stats.max_streak} days")

                for offset in range(1, days_missed + 1):
                    day = last_activity_date + timedelta(days=offset)
                    await self._upsert_streak_day(
                        user_id,
                        day,
                        StreakDayStatus.MISSED,
                        used_freeze=False,
                        source_event="missed",
                    )

            await self._upsert_streak_day(
                user_id,
                today,
                StreakDayStatus.ACTIVE,
                source_event=event_type,
            )

        stats.last_activity_date = today
        await self.db.flush()

        # 触发连胜里程碑检查
        if stats.current_streak in [7, 14, 30, 60, 100, 365]:
            await self.process_event(
                user_id,
                AchievementEvent.STREAK_MILESTONE,
                streak_days=stats.current_streak
            )

    async def _get_or_create_streak_stats(self, user_id: str) -> UserStreakStats:
        """获取或创建连胜统计"""
        query = select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        result = await self.db.execute(query)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = UserStreakStats(user_id=user_id)
            self.db.add(stats)
            await self.db.flush()

        return stats

    def _lane_config_for_achievement(self, achievement: Achievement) -> dict[str, Any]:
        lane_key = self.CATEGORY_TO_LANE.get(achievement.category or "", "prestige")
        return self.PRESTIGE_LANES[lane_key]

    def _build_reward_preview(self, reward_config: Any) -> list[str]:
        rewards = reward_config if isinstance(reward_config, list) else (reward_config or {}).get("rewards", [])
        preview: list[str] = []
        for reward in rewards:
            reward_type = reward.get("type")
            if reward_type == "title":
                preview.append(f"称号 · {reward.get('display') or reward.get('value') or '荣耀称号'}")
            elif reward_type == "galaxy_skin":
                preview.append(f"星图皮肤 · {reward.get('skin_id')}")
            elif reward_type == "visual_element":
                preview.append(f"荣耀装扮 · {reward.get('element_id')}")
            elif reward_type == "freeze_charge":
                preview.append(f"连胜保护 · x{reward.get('quantity', 1)}")
            elif reward_type == "photon":
                preview.append(f"光子积分 · x{reward.get('quantity', 0)}")
        return preview[:4]

    def _surface_preview_for_rewards(self, reward_config: Any) -> list[str]:
        rewards = reward_config if isinstance(reward_config, list) else (reward_config or {}).get("rewards", [])
        surfaces: list[str] = []
        for reward in rewards:
            reward_type = reward.get("type")
            if reward_type == "title" and "个人主页身份条" not in surfaces:
                surfaces.append("个人主页身份条")
            elif reward_type == "galaxy_skin" and "星图主题" not in surfaces:
                surfaces.append("星图主题")
            elif reward_type == "visual_element":
                if "首页氛围" not in surfaces:
                    surfaces.append("首页氛围")
                if "个人主页荣耀位" not in surfaces:
                    surfaces.append("个人主页荣耀位")
        return surfaces

    def _build_unlock_hint(
        self,
        achievement: Achievement,
        progress_value: int,
        progress_target: int,
        display_state: str,
    ) -> str | None:
        if display_state == "hidden_unrevealed":
            return achievement.hint or "继续探索，也许下一次会被看见。"
        if display_state == "blocked" and achievement.prerequisites:
            return f"先完成前置成就：{len(achievement.prerequisites)} 项"
        if progress_target > 0 and progress_value < progress_target:
            return f"还差 {max(progress_target - progress_value, 0)} 即可解锁"
        return achievement.description

    def _build_glory_lines(self, unlock_payload: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        combo_info = unlock_payload.get("combo_info") or {}
        combo = combo_info.get("combo")
        if combo and combo > 1:
            lines.append(f"{combo} 连成就")
        rarity = unlock_payload.get("rarity")
        rarity_value = rarity.value if hasattr(rarity, "value") else str(rarity)
        percentile_map = {
            "common": "击败了 50% 的普通解锁节奏",
            "rare": "击败了 82% 的普通解锁节奏",
            "epic": "击败了 95% 的普通解锁节奏",
            "legendary": "击败了 99% 的普通解锁节奏",
        }
        if rarity_value in percentile_map:
            lines.append(percentile_map[rarity_value])
        if unlock_payload.get("is_first"):
            lines.append("你是首批解锁者之一")
        for surface in unlock_payload.get("surface_preview", [])[:2]:
            lines.append(f"将显眼展示在{surface}")
        return lines[:4]

    def _build_achievement_detail(
        self,
        achievement: Achievement,
        locale: str | None = None,
    ):
        from app.schemas.achievement import AchievementDetail

        detail = AchievementDetail.model_validate(
            achievement,
            from_attributes=True,
        )
        if locale:
            detail = detail.model_copy(
                update={
                    "name": achievement.get_localized_name(locale),
                    "description": achievement.get_localized_description(locale),
                }
            )
        return detail

    # ========== 公共API方法 ==========

    async def get_user_achievements(
        self,
        user_id: str,
        category: str | None = None,
        rarity: AchievementRarity | None = None,
        include_hidden: bool = False,
        include_inactive: bool = False,
        locale: str | None = None,
    ) -> dict[str, Any]:
        """获取用户成就列表"""
        all_achievements = await self._get_all_achievements()
        now = _utcnow()

        # 过滤
        filtered = []
        for achievement in all_achievements:
            if not include_inactive and not self._is_achievement_active(achievement, now):
                continue
            if category and achievement.category != category:
                continue
            if rarity and achievement.rarity != rarity:
                continue
            if not include_hidden and achievement.is_hidden:
                # 对于隐藏成就，只显示已解锁的
                if not await self._is_unlocked(user_id, achievement.id):
                    continue

            filtered.append(achievement)

        # 获取用户进度
        achievement_ids = [a.id for a in filtered]
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id.in_(achievement_ids)
            )
        )
        result = await self.db.execute(query)
        user_progress = {ua.achievement_id: ua for ua in result.scalars().all()}

        # 组装结果
        from app.schemas.achievement import (
            AchievementWithProgress,
            UserAchievementProgressPayload,
        )

        result_list = []
        for achievement in filtered:
            user_ach = user_progress.get(achievement.id)
            is_unlocked = bool(user_ach and user_ach.unlocked_at is not None)
            progress_percentage = int((user_ach.progress if user_ach else 0) * 100)

            # 转换为schema
            achievement_detail = self._build_achievement_detail(
                achievement,
                locale,
            )
            user_progress_detail = (
                UserAchievementProgressPayload.model_validate(
                    user_ach,
                    from_attributes=True,
                )
                if user_ach
                else None
            )

            result_list.append(AchievementWithProgress(
                achievement=achievement_detail,
                user_progress=user_progress_detail,
                is_unlocked=is_unlocked,
                progress_percentage=progress_percentage
            ))

        # 统计
        total_unlocked = sum(1 for ua in user_progress.values() if ua.unlocked_at is not None)

        # 分类统计
        categories = {}
        for achievement in all_achievements:
            cat = achievement.category or "other"
            if cat not in categories:
                categories[cat] = {"total": 0, "unlocked": 0}
            categories[cat]["total"] += 1
            if achievement.id in user_progress and user_progress[achievement.id].unlocked_at:
                categories[cat]["unlocked"] += 1

        return {
            "data": [r.model_dump() for r in result_list],
            "meta": {
                "total_achievements": len(all_achievements),
                "total_unlocked": total_unlocked,
                "categories": categories
            }
        }

    async def get_achievement_map(
        self,
        user_id: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        """获取成就地图数据"""
        all_achievements = await self._get_all_achievements()
        progress_result = await self.db.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        progress_map = {
            item.achievement_id: item
            for item in progress_result.scalars().all()
        }

        lane_groups: dict[str, list[Achievement]] = {}
        positions: dict[str, dict[str, float]] = {}
        sorted_achievements = sorted(
            all_achievements,
            key=lambda item: (
                self._lane_config_for_achievement(item)["x"],
                item.sort_order,
                item.id,
            ),
        )
        for achievement in sorted_achievements:
            lane = self._lane_config_for_achievement(achievement)
            lane_groups.setdefault(lane["id"], []).append(achievement)

        for lane_id, achievements in lane_groups.items():
            lane = next(value for value in self.PRESTIGE_LANES.values() if value["id"] == lane_id)
            ordered = sorted(achievements, key=lambda item: (item.sort_order, item.id))
            for index, achievement in enumerate(ordered):
                y = 130 + index * 156
                x = lane["x"] + (18 if index % 2 == 0 else -18)
                positions[achievement.id] = {"x": float(x), "y": float(y)}

        # 生成节点
        from app.schemas.achievement import AchievementMapNode

        nodes = []
        connections = []
        recommended_candidates: list[tuple[int, int, int, int, str]] = []

        for achievement in all_achievements:
            progress = progress_map.get(achievement.id)
            is_unlocked = bool(progress and progress.unlocked_at is not None)
            progress_percentage = int((progress.progress if progress else 0) * 100)
            progress_value = progress.progress_value if progress else 0
            progress_target = progress.progress_target if progress else 1
            prerequisites = achievement.prerequisites or []
            prerequisites_ready = all(
                bool(progress_map.get(prereq) and progress_map[prereq].unlocked_at is not None)
                for prereq in prerequisites
            )
            if achievement.is_hidden and not is_unlocked:
                display_state = "hidden_unrevealed"
            elif is_unlocked:
                display_state = "unlocked"
            elif progress_percentage >= 75:
                display_state = "close_to_unlock"
            elif prerequisites_ready:
                display_state = "ready_to_pursue"
            else:
                display_state = "blocked"

            if not is_unlocked and display_state in {"close_to_unlock", "ready_to_pursue"}:
                rarity_score = {
                    AchievementRarity.COMMON: 1,
                    AchievementRarity.RARE: 2,
                    AchievementRarity.EPIC: 3,
                    AchievementRarity.LEGENDARY: 4,
                }.get(achievement.rarity, 0)
                recommended_candidates.append(
                    (
                        0 if display_state == "close_to_unlock" else 1,
                        -progress_percentage,
                        -rarity_score,
                        achievement.sort_order,
                        achievement.id,
                    )
                )

            lane = self._lane_config_for_achievement(achievement)
            reward_preview = self._build_reward_preview(achievement.reward_config)
            unlock_hint = self._build_unlock_hint(
                achievement,
                progress_value=progress_value,
                progress_target=progress_target,
                display_state=display_state,
            )

            nodes.append(AchievementMapNode(
                id=achievement.id,
                name=achievement.get_localized_name(locale),
                rarity=achievement.rarity,
                category=achievement.category or "other",
                lane=lane["id"],
                lane_label=lane["label"],
                position=positions.get(achievement.id, {"x": 0, "y": 0}),
                is_unlocked=is_unlocked,
                is_hidden=achievement.is_hidden,
                prerequisites=prerequisites,
                parent_id=achievement.parent_id,
                display_state=display_state,
                reward_preview=reward_preview,
                progress_percentage=progress_percentage,
                progress_value=progress_value,
                progress_target=progress_target,
                unlock_hint=unlock_hint,
            ))

            # 生成连接线
            if prerequisites:
                for prereq in prerequisites:
                    connections.append({
                        "from": prereq,
                        "to": achievement.id,
                        "type": "prerequisite"
                    })

            if achievement.parent_id:
                connections.append({
                    "from": achievement.parent_id,
                    "to": achievement.id,
                    "type": "parent"
                })

        recommended_candidates.sort()
        recommended_target_id = recommended_candidates[0][4] if recommended_candidates else None

        node_payloads = []
        for node in nodes:
            payload = node.model_dump()
            payload["is_recommended_target"] = node.id == recommended_target_id
            node_payloads.append(payload)

        category_info = [
            {
                "id": lane["id"],
                "name": lane["label"],
                "count": len(lane_groups.get(lane["id"], [])),
                "color": lane["color"],
            }
            for lane in self.PRESTIGE_LANES.values()
        ]

        return {
            "nodes": node_payloads,
            "connections": connections,
            "categories": category_info
        }

    async def get_streak_stats(self, user_id: str) -> dict[str, Any]:
        """获取用户连胜统计"""
        stats = await self._get_or_create_streak_stats(user_id)

        from app.schemas.achievement import StreakStatsResponse
        return StreakStatsResponse.model_validate(stats, from_attributes=True).model_dump()

    async def get_streak_history(self, user_id: str, days: int = 90) -> dict[str, Any]:
        """获取连胜日历历史（默认最近90天）"""
        from app.schemas.achievement import StreakDayRecord, StreakHistoryResponse

        today = _utcnow().date()
        start_day = today - timedelta(days=days - 1)

        query = select(UserStreakDay).where(
            and_(
                UserStreakDay.user_id == user_id,
                UserStreakDay.day >= start_day,
                UserStreakDay.day <= today,
            )
        )
        result = await self.db.execute(query)
        records = result.scalars().all()
        record_map = {record.day: record for record in records}

        days_data: list[StreakDayRecord] = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            record = record_map.get(day)
            if record:
                status = record.status.value if hasattr(record.status, "value") else str(record.status)
                days_data.append(
                    StreakDayRecord(
                        day=day,
                        status=status,
                        used_freeze=record.used_freeze,
                        source_event=record.source_event,
                    )
                )
            else:
                days_data.append(
                    StreakDayRecord(
                        day=day,
                        status=StreakDayStatus.MISSED.value,
                        used_freeze=False,
                        source_event=None,
                    )
                )

        return StreakHistoryResponse(days=days_data).model_dump()

    async def get_achievement_stats(self, user_id: str) -> dict[str, Any]:
        """获取用户成就统计"""
        all_achievements = await self._get_all_achievements()

        # 获取用户成就
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.unlocked_at.isnot(None)
            )
        )
        result = await self.db.execute(query)
        unlocked = result.scalars().all()

        {ua.achievement_id for ua in unlocked}

        # 按稀有度统计
        rarity_count = dict.fromkeys(AchievementRarity, 0)
        hidden_count = 0

        for ua in unlocked:
            achievement = await self._get_achievement(ua.achievement_id)
            if achievement:
                rarity_count[achievement.rarity] += 1
                if achievement.is_hidden:
                    hidden_count += 1

        # 连胜统计
        stats = await self._get_or_create_streak_stats(user_id)

        # 获取用户光子余额
        from app.services.photon_service import PhotonService
        photon_service = PhotonService(self.db)
        total_photons = await photon_service.get_balance(user_id)

        from app.schemas.achievement import AchievementStatsResponse
        return AchievementStatsResponse(
            total_achievements=len(all_achievements),
            unlocked_count=len(unlocked),
            unlocked_percentage=round(len(unlocked) / len(all_achievements) * 100, 1) if all_achievements else 0,
            common_count=rarity_count[AchievementRarity.COMMON],
            rare_count=rarity_count[AchievementRarity.RARE],
            epic_count=rarity_count[AchievementRarity.EPIC],
            legendary_count=rarity_count[AchievementRarity.LEGENDARY],
            hidden_found=hidden_count,
            current_streak=stats.current_streak,
            total_photons=total_photons
        ).model_dump()

    # ========== Enhancement Methods: Combo, Milestone, Daily First ==========

    async def _get_old_progress(self, user_id: str, achievement_id: str) -> float:
        """获取成就的旧进度（用于里程碑检测）"""
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id
            )
        )
        result = await self.db.execute(query)
        user_achievement = result.scalar_one_or_none()
        return user_achievement.progress if user_achievement else 0.0

    async def _check_progress_milestone(
        self,
        user_id: str,
        achievement: Achievement,
        old_progress: float,
        new_progress: float
    ) -> dict[str, Any] | None:
        """
        检查进度里程碑（每25%进度）

        Returns:
            里程碑信息，如果触发了里程碑则返回数据，否则返回None
        """
        milestones = [25, 50, 75]
        old_percent = int(old_progress * 100)
        new_percent = int(new_progress * 100)

        for milestone in milestones:
            # 检查是否刚跨越这个里程碑
            if old_percent < milestone <= new_percent:
                return {
                    "achievement_id": achievement.id,
                    "achievement_name": achievement.name,
                    "milestone_percent": milestone,
                    "message": f"「{achievement.name}」进度达到{milestone}%！加油！",
                    "type": "progress_milestone"
                }
        return None

    async def _handle_achievement_combo(
        self,
        user_id: str,
        unlock_count: int
    ) -> dict[str, Any] | None:
        """
        处理成就连击检测

        Returns:
            连击信息，如果触发连击则返回数据，否则返回None
        """
        session_key = f"{settings.APP_NAME}:achievement_combo:{user_id}"
        combo = await cache_service.get(session_key) or 0

        # 更新连击计数
        combo += unlock_count
        await cache_service.set(session_key, combo, ttl=300)  # 5分钟内有效

        # 只在连击>=2时返回信息
        if combo >= 2:
            bonus_photons = combo * 10 if combo >= 3 else 0
            return {
                "combo": combo,
                "message": f"🔥 {combo}连击解锁！",
                "bonus_photons": bonus_photons,
                "type": "achievement_combo"
            }
        return None

    async def _notify_milestones(self, user_id: str, milestones: list[dict[str, Any]]):
        """发送里程碑通知"""
        from app.core.websocket import get_ws_manager

        ws_manager = get_ws_manager()

        for milestone in milestones:
            logger.info(f"Milestone for user {user_id}: {milestone['message']}")

            # 通过 WebSocket 发送里程碑事件
            message = {
                "type": "achievement_milestone",
                "data": milestone
            }

            try:
                await ws_manager.send_personal_message(message, user_id)
                logger.debug(f"Sent achievement milestone notification to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send milestone notification: {e}")

    async def check_daily_first(
        self,
        user_id: str,
        db: AsyncSession
    ) -> dict[str, Any] | None:
        """
        检查今日首胜奖励

        Returns:
            首胜奖励数据，如果今天已领取则返回None
        """
        today = date.today()
        cache_key = f"{settings.APP_NAME}:daily_first:{user_id}:{today.isoformat()}"

        # 检查今天是否已领取
        if await cache_service.get(cache_key):
            return None

        # 标记为已领取
        await cache_service.set(cache_key, True, ttl=86400)  # 24小时

        # 获取连胜统计
        stats = await self._get_or_create_streak_stats(user_id)

        return {
            "type": "daily_first",
            "reward": {
                "photon": 30,
                "freeze_charges": 1 if stats.current_streak >= 3 else 0,
            },
            "message": "🔥 今日首胜！获得30光子" +
                      (" + 1张连胜保护卡" if stats.current_streak >= 3 else ""),
            "streak": stats.current_streak,
            "date": today.isoformat(),
        }

    async def get_close_to_unlock_achievements(
        self,
        user_id: str,
        threshold: float = 0.8,
        category: str | None = None,
        locale: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取接近解锁的成就（用于临界提示）

        Args:
            user_id: 用户ID
            threshold: 进度阈值，默认80%
            category: 筛选特定类别，如 "sprint"

        Returns:
            接近解锁的成就列表，包含进度信息
        """
        all_achievements = await self._get_all_achievements()

        # 过滤类别
        if category:
            all_achievements = [a for a in all_achievements if a.category == category]

        from app.schemas.achievement import (
            AchievementWithProgress,
            UserAchievementProgressPayload,
        )

        unlocked_result = await self.db.execute(
            select(UserAchievement.achievement_id).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.unlocked_at.is_not(None),
                )
            )
        )
        unlocked_ids = set(unlocked_result.scalars().all())

        close_achievements = []

        for achievement in all_achievements:
            # 先以数据库记录为准，再用缓存短路未命中的场景，
            # 避免事务提交后的短暂缓存窗口把已解锁成就继续当作“即将解锁”返回。
            if achievement.id in unlocked_ids or await self._is_unlocked(user_id, achievement.id):
                continue

            # 检查前置条件
            if not await self._check_prerequisites(user_id, achievement):
                continue

            # 评估进度
            progress, current_value, target_value = await self._evaluate_progress(
                user_id, achievement
            )

            # 只返回达到阈值的
            if progress >= threshold:
                user_progress = UserAchievementProgressPayload(
                    achievement_id=achievement.id,
                    progress=progress,
                    progress_value=current_value,
                    progress_target=target_value,
                    is_pinned=False,
                    share_count=0,
                    is_first_unlocker=False,
                    unlocked_at=None,
                    last_progress_update=None,
                )
                close_achievements.append(
                    AchievementWithProgress(
                        achievement=self._build_achievement_detail(
                            achievement,
                            locale,
                        ),
                        user_progress=user_progress,
                        is_unlocked=False,
                        progress_percentage=int(progress * 100),
                    ).model_dump()
                )

        # 按进度降序排序
        close_achievements.sort(key=lambda x: x["progress_percentage"], reverse=True)

        return close_achievements


class ContractService:
    """星火契约服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_contract(
        self,
        user_id: str,
        study_minutes: int,
        days: int,
        photon_stake: int
    ) -> SparkContract:
        """创建学习契约"""
        # 检查是否已有活跃契约
        existing = await self._get_active_contract(user_id)
        if existing:
            raise ValueError("User already has an active contract")

        contract = SparkContract(
            user_id=user_id,
            target_study_minutes=study_minutes,
            target_days=days,
            photon_stake=photon_stake,
            start_date=_utcnow(),
            end_date=_utcnow() + timedelta(days=days),
            status=ContractStatus.ACTIVE
        )
        self.db.add(contract)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def _get_active_contract(self, user_id: str) -> SparkContract | None:
        """获取活跃契约"""
        query = select(SparkContract).where(
            and_(
                SparkContract.user_id == user_id,
                SparkContract.status == ContractStatus.ACTIVE
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_contract_status(self, user_id: str) -> dict | None:
        """检查契约状态"""
        contract = await self._get_active_contract(user_id)
        if not contract:
            return None

        today = _utcnow()

        # 检查是否过期
        if today > contract.end_date:
            if contract.current_days >= contract.target_days:
                # 完成
                contract.status = ContractStatus.COMPLETED
                contract.completed_at = today
                await self._grant_rewards(contract)
                await self.db.commit()
                return {"status": "completed", "reward": contract.photon_stake * contract.reward_multiplier}
            else:
                # 失败
                contract.status = ContractStatus.FAILED
                contract.failed_at = today
                contract.failure_reason = "Time expired"
                await self._deduct_photons(contract)
                await self.db.commit()
                return {"status": "failed", "lost": contract.photon_stake}

        return {
            "status": "active",
            "progress": f"{contract.current_days}/{contract.target_days}",
            "minutes": f"{contract.current_minutes}/{contract.target_study_minutes}"
        }

    async def _grant_rewards(self, contract: SparkContract):
        """发放契约奖励"""
        try:
            from app.services.photon_service import PhotonService, PhotonTransactionType

            photon_service = PhotonService(self.db)
            reward_amount = contract.photon_stake * contract.reward_multiplier

            await photon_service.grant_photons(
                user_id=contract.user_id,
                amount=reward_amount,
                source=f"contract:{contract.id}",
                transaction_type=PhotonTransactionType.GRANT_CONTRACT,
                metadata={
                    "contract_id": str(contract.id),
                    "stake": contract.photon_stake,
                    "multiplier": contract.reward_multiplier
                },
                related_item_id=str(contract.id),
                record_history=True,
                manage_transaction=False,
            )

            logger.info(f"Contract rewards granted: {reward_amount} photons to user {contract.user_id}")
        except Exception as e:
            logger.error(f"Failed to grant contract rewards for {contract.id}: {e}")

    async def _deduct_photons(self, contract: SparkContract):
        """扣除光子积分"""
        try:
            from app.services.photon_service import PhotonService, PhotonTransactionType

            photon_service = PhotonService(self.db)

            await photon_service.deduct_photons(
                user_id=contract.user_id,
                amount=contract.photon_stake,
                reason=f"Contract failed: {contract.id}",
                transaction_type=PhotonTransactionType.DEDUCT_CONTRACT,
                metadata={
                    "contract_id": str(contract.id),
                    "failure_reason": contract.failure_reason
                },
                related_item_id=str(contract.id),
                record_history=True,
                manage_transaction=False,
            )

            logger.info(f"Contract photons deducted: {contract.photon_stake} from user {contract.user_id}")
        except Exception as e:
            logger.error(f"Failed to deduct photons for failed contract {contract.id}: {e}")

    async def update_daily_progress(self, user_id: str, study_minutes: int):
        """更新每日契约进度"""
        contract = await self._get_active_contract(user_id)
        if not contract:
            return

        contract.current_minutes += study_minutes
        if contract.current_minutes >= contract.target_study_minutes:
            contract.current_days += 1
            contract.current_minutes = 0  # 重置当日分钟数

        await self.db.commit()

        # 检查契约状态
        await self.check_contract_status(user_id)

    # ------------------------------------------------------------------
    # Public aliases for internal methods used by the API layer
    # ------------------------------------------------------------------
    async def get_achievement(self, achievement_id: str):
        """Public alias for _get_achievement."""
        return await self._get_achievement(achievement_id)

    async def is_unlocked(self, user_id, achievement_id: str) -> bool:
        """Public alias for _is_unlocked."""
        return await self._is_unlocked(user_id, achievement_id)

    def build_achievement_detail(self, achievement, locale: str | None = None):
        """Public alias for _build_achievement_detail."""
        return self._build_achievement_detail(achievement, locale)
