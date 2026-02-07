"""
Achievement Engine Service
成就引擎核心服务 - 处理成就解锁逻辑、连胜统计、契约管理
"""
from datetime import UTC, date, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.models.achievement import (
    Achievement,
    AchievementRarity,
    ContractStatus,
    SparkContract,
    UserAchievement,
    UserGalaxySkin,
    UserStreakStats,
    UserTitle,
)
from app.models.galaxy import KnowledgeNode, UserNodeStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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


class AchievementEngine:
    """成就引擎 - 核心服务"""

    # 成就定义缓存（内存缓存）
    _achievement_cache: dict[str, Achievement] = {}
    _cache_last_update: datetime = None
    _cache_ttl = timedelta(minutes=5)

    def __init__(self, db: AsyncSession):
        self.db = db

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
            await self._notify_unlocks(user_id, unlocked)

        # 6. 发送里程碑通知
        if milestones:
            await self._notify_milestones(user_id, milestones)

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
                    if trigger_code in ["TASKS_TOTAL", "TASKS_COMPLETED"]:
                        relevant.append(achievement)
                case AchievementEvent.DAILY_CHECKIN:
                    if trigger_code == "STREAK_DAYS":
                        relevant.append(achievement)
                case AchievementEvent.NODE_UNLOCKED:
                    if trigger_code in ["NODES_UNLOCKED", "SECTOR_MASTERY"]:
                        relevant.append(achievement)
                case AchievementEvent.NODE_MASTERED:
                    if trigger_code in ["NODES_MASTERED", "PERFECTIONIST"]:
                        relevant.append(achievement)
                case AchievementEvent.STUDY_MINUTES_ACCUMULATED:
                    if trigger_code in ["STUDY_MINUTES_TOTAL", "STUDY_MINUTES_SINGLE"]:
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

        return relevant

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
                query = select(func.count()).select_from(Task).where(
                    and_(
                        Task.user_id == user_id,
                        Task.status == TaskStatus.COMPLETED
                    )
                )
                result = await self.db.execute(query)
                current = result.scalar_one() or 0
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
                target_percent = config.get("percent", 80)

                # 查询该领域所有节点
                query = select(UserNodeStatus).join(KnowledgeNode).where(
                    and_(
                        UserNodeStatus.user_id == user_id,
                        KnowledgeNode.sector_code == sector,
                        UserNodeStatus.is_unlocked
                    )
                )
                result = await self.db.execute(query)
                statuses = result.scalars().all()

                if not statuses:
                    return (0.0, 0, 100)

                mastered = sum(1 for s in statuses if s.mastery_score >= target_percent)
                return (mastered / len(statuses), mastered, len(statuses))

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
                hour = _utcnow().hour
                if hour >= 23 or hour <= 5:
                    # 检查累计次数
                    cache_key = f"night_owl:{user_id}"
                    count = await cache_service.get(cache_key) or 0
                    count += 1
                    await cache_service.set(cache_key, count, ex=86400*30)
                    target = config.get("sessions", 10)
                    return (min(count / target, 1.0), count, target)
                return (0.0, 0, 10)

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
                        not Plan.is_active  # 已归档（完成/放弃）
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
                        not Plan.is_active,
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
                        not Plan.is_active
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
                        not Plan.is_active,
                        Plan.progress >= 1.0,
                        Plan.target_date.isnot(None)
                    )
                )
                result = await self.db.execute(query)
                total = result.scalar_one() or 0

                # 估算超前完成数（这里简化处理，实际应用中需要更精确的记录）
                target = config.get("count", 1)
                return (min(1.0, total / target) if total > 0 else (0.0, 0, target), total, target)

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
    ) -> dict[str, Any]:
        """解锁成就"""
        now = _utcnow()

        # 更新用户成就记录
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            )
        )
        result = await self.db.execute(query)
        user_achievement = result.scalar_one_or_none()

        if not user_achievement:
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                progress=1.0,
                unlocked_at=now
            )
            self.db.add(user_achievement)
        else:
            user_achievement.unlocked_at = now
            user_achievement.progress = 1.0

        # 检查是否首位解锁者
        is_first = False
        if not achievement.first_unlocker_id:
            achievement.first_unlocker_id = user_id
            user_achievement.is_first_unlocker = True
            is_first = True

        # 更新全局统计
        achievement.total_unlocked += 1

        await self.db.commit()

        # 清除缓存
        cache_key = f"{settings.APP_NAME}:achievement:{user_id}:{achievement.id}:unlocked"
        await cache_service.delete(cache_key)
        await cache_service.delete_pattern(
            f"{settings.APP_NAME}:achievement:{user_id}:*"
        )

        # 处理奖励
        await self._grant_rewards(user_id, achievement)

        return {
            "achievement_id": achievement.id,
            "name": achievement.name,
            "rarity": achievement.rarity,
            "visual_effect": achievement.visual_config,
            "visual_effect_type": achievement.visual_effect_type,
            "rewards": achievement.reward_config,
            "is_first": is_first,
            "unlocked_at": now
        }

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
                    # 光子积分 - 实际发放
                    try:
                        from app.services.photon_service import PhotonService, PhotonTransactionType

                        photon_service = PhotonService(self.db)
                        quantity = reward.get("quantity", 0)

                        await photon_service.grant_photons(
                            user_id=user_id,
                            amount=quantity,
                            source=f"achievement:{achievement.id}",
                            transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
                            metadata={"achievement_name": achievement.name}
                        )

                        logger.info(f"Granted {quantity} photons to user {user_id} for achievement {achievement.id}")
                    except Exception as e:
                        logger.error(f"Failed to grant photons for achievement {achievement.id}: {e}")

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
                    "is_first": unlock.get("is_first", False),
                    "unlocked_at": unlock["unlocked_at"].isoformat() if isinstance(unlock["unlocked_at"], datetime) else unlock["unlocked_at"],
                    # 添加连击信息
                    "combo_info": unlock.get("combo_info"),
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

    async def _update_streak_stats(self, user_id: str, event_type: str, **kwargs):
        """更新连胜统计"""
        stats = await self._get_or_create_streak_stats(user_id)
        today = _utcnow().date()

        # 只有核心活动才更新连胜
        if event_type not in [AchievementEvent.DAILY_CHECKIN,
                              AchievementEvent.TASK_COMPLETED,
                              AchievementEvent.NODE_MASTERED]:
            return

        if not stats.last_activity_date:
            stats.current_streak = 1
            stats.last_activity_date = today
            stats.longest_streak_start = today
            await self.db.flush()
            return

        delta = (today - stats.last_activity_date).days

        if delta == 0:
            # 今天已活动，无需更新
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
        else:
            # 演了活动，检查保护卡
            days_missed = delta - 1

            if stats.freeze_charges >= days_missed:
                # 使用保护卡
                stats.freeze_charges -= days_missed
                stats.last_freeze_used_at = _utcnow()
                stats.current_streak += 1  # 今天也算
                logger.info(f"User {user_id} used {days_missed} freeze charges")
            else:
                # 保护不足，连胜断裂
                stats.current_streak = 1
                logger.info(f"User {user_id} streak broken at {stats.max_streak} days")

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

    # ========== 公共API方法 ==========

    async def get_user_achievements(
        self,
        user_id: str,
        category: str | None = None,
        rarity: AchievementRarity | None = None,
        include_hidden: bool = False
    ) -> dict[str, Any]:
        """获取用户成就列表"""
        all_achievements = await self._get_all_achievements()

        # 过滤
        filtered = []
        for achievement in all_achievements:
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
        from app.schemas.achievement import AchievementDetail, AchievementWithProgress, UserAchievementDetail

        result_list = []
        for achievement in filtered:
            user_ach = user_progress.get(achievement.id)
            is_unlocked = user_ach and user_ach.unlocked_at is not None
            progress_percentage = int((user_ach.progress if user_ach else 0) * 100)

            # 转换为schema
            achievement_detail = AchievementDetail.model_validate(achievement)
            user_progress_detail = UserAchievementDetail.model_validate(user_ach) if user_ach else None

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

    async def get_achievement_map(self, user_id: str) -> dict[str, Any]:
        """获取成就地图数据"""
        all_achievements = await self._get_all_achievements()

        # 按类别分组获取位置
        categories = {}
        positions = {}
        _x, _y = 0, 0
        row_width = 5

        for achievement in all_achievements:
            cat = achievement.category or "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(achievement)

        # 计算位置（简单的网格布局）
        for cat, achievements in categories.items():
            for i, achievement in enumerate(achievements):
                positions[achievement.id] = {
                    "x": (i % row_width) * 100 + (len(cat) * 50),
                    "y": (i // row_width) * 100
                }

        # 生成节点
        from app.schemas.achievement import AchievementMapNode

        nodes = []
        connections = []

        for achievement in all_achievements:
            is_unlocked = await self._is_unlocked(user_id, achievement.id)

            nodes.append(AchievementMapNode(
                id=achievement.id,
                name=achievement.name,
                rarity=achievement.rarity,
                category=achievement.category or "other",
                position=positions.get(achievement.id, {"x": 0, "y": 0}),
                is_unlocked=is_unlocked,
                is_hidden=achievement.is_hidden,
                prerequisites=achievement.prerequisites or [],
                parent_id=achievement.parent_id
            ))

            # 生成连接线
            if achievement.prerequisites:
                for prereq in achievement.prerequisites:
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

        # 分类信息
        category_info = [
            {"id": cat, "name": cat, "count": len(achievements)}
            for cat, achievements in categories.items()
        ]

        return {
            "nodes": [n.model_dump() for n in nodes],
            "connections": connections,
            "categories": category_info
        }

    async def get_streak_stats(self, user_id: str) -> dict[str, Any]:
        """获取用户连胜统计"""
        stats = await self._get_or_create_streak_stats(user_id)

        from app.schemas.achievement import StreakStatsResponse
        return StreakStatsResponse.model_validate(stats).model_dump()

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
        await cache_service.set(session_key, combo, ex=300)  # 5分钟内有效

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
        await cache_service.set(cache_key, True, ex=86400)  # 24小时

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
        category: str | None = None
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

        close_achievements = []

        for achievement in all_achievements:
            # 跳过已解锁的
            if await self._is_unlocked(user_id, achievement.id):
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
                close_achievements.append({
                    "achievement_id": achievement.id,
                    "name": achievement.name,
                    "description": achievement.description,
                    "rarity": achievement.rarity.value,
                    "progress": progress,
                    "progress_value": current_value,
                    "progress_target": target_value,
                    "remaining": target_value - current_value,
                })

        # 按进度降序排序
        close_achievements.sort(key=lambda x: x["progress"], reverse=True)

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
                    "contract_id": contract.id,
                    "stake": contract.photon_stake,
                    "multiplier": contract.reward_multiplier
                }
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
                    "contract_id": contract.id,
                    "failure_reason": contract.failure_reason
                }
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
