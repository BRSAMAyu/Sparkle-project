"""
责任伙伴成就服务
Accountability Achievement Service

处理责任伙伴系统的成就:
- 连胜里程碑成就
- 伙伴关系成就
- 协作成就
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.achievement import Achievement, AchievementRarity, AchievementType, UserAchievement
from app.models.user import PushPreference, User
from app.services.notification_service import notification_service


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_timezone(timezone_name: str | None) -> str:
    timezone_name = timezone_name or "Asia/Shanghai"
    try:
        ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "Asia/Shanghai"
    return timezone_name


def _user_timezone(user: User | None) -> str:
    return _normalize_timezone(getattr(getattr(user, "push_preference", None), "timezone", None))


def _to_local_date(timestamp: datetime, timezone_name: str):
    zone = ZoneInfo(timezone_name)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(zone).date()


class AccountabilityAchievementService:
    """责任伙伴成就服务"""

    # 责任伙伴成就定义
    ACCOUNTABILITY_ACHIEVEMENTS = {
        "accountability_first_partnership": {
            "id": "accountability_first_partnership",
            "name": "首次结伴",
            "description": "成功建立第一个责任伙伴关系",
            "icon": "🤝",
            "type": AchievementType.SOCIAL,
            "points": 10,
            "trigger_code": "FIRST_PARTNERSHIP",
        },
        "accountability_streak_7": {
            "id": "accountability_streak_7",
            "name": "一周连胜",
            "description": "在责任伙伴关系中连续7天打卡",
            "icon": "🔥",
            "type": AchievementType.STREAK,
            "points": 50,
            "trigger_code": "STREAK_7",
        },
        "accountability_streak_30": {
            "id": "accountability_streak_30",
            "name": "月度坚持",
            "description": "在责任伙伴关系中连续30天打卡",
            "icon": "🏆",
            "type": AchievementType.STREAK,
            "points": 200,
            "trigger_code": "STREAK_30",
        },
        "accountability_streak_100": {
            "id": "accountability_streak_100",
            "name": "百日长跑",
            "description": "在责任伙伴关系中连续100天打卡",
            "icon": "💯",
            "type": AchievementType.STREAK,
            "points": 500,
            "trigger_code": "STREAK_100",
        },
        "accountability_perfect_month": {
            "id": "accountability_perfect_month",
            "name": "完美月份",
            "description": "在一个自然月内每天打卡（与伙伴双方）",
            "icon": "⭐",
            "type": AchievementType.MILESTONE,
            "points": 300,
            "trigger_code": "PERFECT_MONTH",
        },
        "accountability_partner_streak_7": {
            "id": "accountability_partner_streak_7",
            "name": "共同进步",
            "description": "与伙伴同时保持7天连胜",
            "icon": "👥",
            "type": AchievementType.SOCIAL,
            "points": 100,
            "trigger_code": "PARTNER_STREAK_7",
        },
        "accountability_50_checkins": {
            "id": "accountability_50_checkins",
            "name": "打卡达人",
            "description": "在责任伙伴关系中累计打卡50次",
            "icon": "📝",
            "type": AchievementType.MILESTONE,
            "points": 150,
            "trigger_code": "CHECKINS_50",
        },
        "accountability_mutual_support": {
            "id": "accountability_mutual_support",
            "name": "互相支持",
            "description": "连续7天双方都在同一时间打卡（2小时内）",
            "icon": "🤲",
            "type": AchievementType.SOCIAL,
            "points": 120,
            "trigger_code": "MUTUAL_SUPPORT",
        },
    }

    _RARITY_BY_ACHIEVEMENT = {
        "accountability_first_partnership": AchievementRarity.COMMON,
        "accountability_streak_7": AchievementRarity.RARE,
        "accountability_streak_30": AchievementRarity.EPIC,
        "accountability_streak_100": AchievementRarity.LEGENDARY,
        "accountability_perfect_month": AchievementRarity.EPIC,
        "accountability_partner_streak_7": AchievementRarity.RARE,
        "accountability_50_checkins": AchievementRarity.RARE,
        "accountability_mutual_support": AchievementRarity.EPIC,
    }

    async def ensure_achievement_definitions(self, db: AsyncSession) -> None:
        for achievement_id, achievement_def in self.ACCOUNTABILITY_ACHIEVEMENTS.items():
            existing = await db.get(Achievement, achievement_id)
            if existing:
                continue

            db.add(
                Achievement(
                    id=achievement_id,
                    name=achievement_def["name"],
                    description=achievement_def["description"],
                    icon_url=achievement_def.get("icon"),
                    type=achievement_def["type"],
                    rarity=self._RARITY_BY_ACHIEVEMENT.get(achievement_id, AchievementRarity.COMMON),
                    trigger_code=achievement_def["trigger_code"],
                    trigger_config={
                        "points": achievement_def.get("points", 0),
                        "source": "accountability",
                    },
                    category="accountability",
                )
            )
        await db.flush()

    async def check_streak_achievements(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
    ) -> list[str]:
        """
        检查连胜成就

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID

        Returns:
            新解锁的成就ID列表
        """
        unlocked = []

        # 计算连胜天数
        streak_days = await self._calculate_streak(db, partnership_id, user_id)

        # 检查各连胜里程碑
        for achievement_id, required_days in [
            ("accountability_streak_7", 7),
            ("accountability_streak_30", 30),
            ("accountability_streak_100", 100),
        ]:
            if streak_days >= required_days:
                if await self._unlock_achievement(db, user_id, achievement_id):
                    unlocked.append(achievement_id)
                    logger.info(
                        f"Unlocked achievement {achievement_id} for user {user_id} with {streak_days} day streak"
                    )

        return unlocked

    async def check_partnership_achievements(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
    ) -> list[str]:
        """
        检查伙伴关系成就

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID

        Returns:
            新解锁的成就ID列表
        """
        unlocked = []

        partnership = await db.get(AccountabilityPartnership, partnership_id)
        if not partnership:
            return unlocked

        partner_id = partnership.partner_id if user_id == partnership.initiator_id else partnership.initiator_id

        # 检查首次伙伴关系
        if await self._is_first_partnership(db, user_id):
            if await self._unlock_achievement(db, user_id, "accountability_first_partnership"):
                unlocked.append("accountability_first_partnership")

        # 检查共同进步（双方都有7天以上连胜）
        user_streak = await self._calculate_streak(db, partnership_id, user_id)
        partner_streak = await self._calculate_streak(db, partnership_id, partner_id)

        if user_streak >= 7 and partner_streak >= 7:
            if await self._unlock_achievement(db, user_id, "accountability_partner_streak_7"):
                unlocked.append("accountability_partner_streak_7")

        # 检查打卡次数里程碑
        total_checkins = await self._count_checkins(db, partnership_id, user_id)
        if total_checkins >= 50:
            if await self._unlock_achievement(db, user_id, "accountability_50_checkins"):
                unlocked.append("accountability_50_checkins")

        return unlocked

    async def check_mutual_support_achievement(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
    ) -> list[str]:
        """
        检查互相支持成就（连续7天双方都在2小时内打卡）

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID

        Returns:
            新解锁的成就ID列表
        """
        unlocked = []

        partnership = await db.get(AccountabilityPartnership, partnership_id)
        if not partnership:
            return unlocked

        partner_id = partnership.partner_id if user_id == partnership.initiator_id else partnership.initiator_id

        # 检查连续7天互相支持
        mutual_days = await self._count_mutual_checkin_days(db, partnership_id, user_id, partner_id, days=7)

        if mutual_days >= 7:
            if await self._unlock_achievement(db, user_id, "accountability_mutual_support"):
                unlocked.append("accountability_mutual_support")

        return unlocked

    async def check_perfect_month(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
    ) -> list[str]:
        """
        检查完美月份成就

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID

        Returns:
            新解锁的成就ID列表
        """
        unlocked = []

        partnership = await db.get(AccountabilityPartnership, partnership_id)
        if not partnership or not partnership.started_at:
            return unlocked

        # 检查上个月是否双方都每天打卡
        now = _utcnow()
        if now.month == 1:
            last_month = 12
            last_month_year = now.year - 1
        else:
            last_month = now.month - 1
            last_month_year = now.year

        # 获取上个月的天数
        import calendar

        days_in_month = calendar.monthrange(last_month_year, last_month)[1]

        # 检查双方是否每天都打卡
        partner_id = partnership.partner_id if user_id == partnership.initiator_id else partnership.initiator_id

        for target_user_id in [user_id, partner_id]:
            perfect_month = await self._check_perfect_month_for_user(
                db, partnership_id, target_user_id, last_month_year, last_month, days_in_month
            )

            if perfect_month:
                if await self._unlock_achievement(db, target_user_id, "accountability_perfect_month"):
                    unlocked.append(f"{target_user_id}:accountability_perfect_month")

        return unlocked

    async def award_achievement(
        self,
        db: AsyncSession,
        user_id: UUID,
        achievement_id: str,
    ) -> dict[str, Any]:
        """
        发放成就奖励

        Args:
            db: 数据库会话
            user_id: 用户ID
            achievement_id: 成就ID

        Returns:
            发放结果
        """
        achievement_def = self.ACCOUNTABILITY_ACHIEVEMENTS.get(achievement_id)
        if not achievement_def:
            return {"status": "error", "message": "Achievement not found"}

        # 检查是否已解锁
        existing = await db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "already_unlocked", "achievement_id": achievement_id}

        await self.ensure_achievement_definitions(db)

        # 创建成就记录
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            unlocked_at=_utcnow(),
        )
        db.add(user_achievement)
        await db.commit()

        # 发送通知
        await notification_service.create(
            db,
            user_id,
            {
                "title": f"🏆 成就解锁：{achievement_def['name']}",
                "content": achievement_def["description"],
                "type": "achievement",
                "data": {
                    "achievement_id": achievement_id,
                    "points": achievement_def["points"],
                },
            },
            push_via_websocket=True,
        )

        logger.info(f"Awarded achievement {achievement_id} to user {user_id}")
        return {
            "status": "success",
            "achievement_id": achievement_id,
            "points": achievement_def["points"],
        }

    # ==================== 辅助方法 ====================

    async def _calculate_streak(
        self,
        db: AsyncSession,
        partnership_id: UUID,
        user_id: UUID,
    ) -> int:
        """计算用户的连续打卡天数"""
        from datetime import date

        timezone_result = await db.execute(
            select(PushPreference.timezone).where(PushPreference.user_id == user_id)
        )
        timezone_name = _normalize_timezone(timezone_result.scalar_one_or_none())

        result = await db.execute(
            select(AccountabilityCheckin.created_at)
            .where(
                and_(
                    AccountabilityCheckin.partnership_id == partnership_id,
                    AccountabilityCheckin.user_id == user_id,
                )
            )
            .order_by(AccountabilityCheckin.created_at.desc())
        )

        checkin_dates: set[date] = set()
        for (ts,) in result.all():
            checkin_dates.add(_to_local_date(ts, timezone_name))

        today_local = _to_local_date(_utcnow(), timezone_name)
        streak = 0
        current = today_local

        while current in checkin_dates:
            streak += 1
            current -= timedelta(days=1)

        return streak

    async def _count_checkins(
        self,
        db: AsyncSession,
        partnership_id: UUID,
        user_id: UUID,
    ) -> int:
        """统计用户的总打卡次数"""
        result = await db.execute(
            select(func.count(AccountabilityCheckin.id)).where(
                and_(
                    AccountabilityCheckin.partnership_id == partnership_id,
                    AccountabilityCheckin.user_id == user_id,
                )
            )
        )
        return result.scalar() or 0

    async def _is_first_partnership(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> bool:
        """检查是否是第一个伙伴关系"""
        result = await db.execute(
            select(func.count(AccountabilityPartnership.id)).where(
                and_(
                    AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
                    or_(
                        AccountabilityPartnership.initiator_id == user_id,
                        AccountabilityPartnership.partner_id == user_id,
                    ),
                )
            )
        )
        count = result.scalar() or 0
        return count == 1

    async def _count_mutual_checkin_days(
        self,
        db: AsyncSession,
        partnership_id: UUID,
        user_id: UUID,
        partner_id: UUID,
        days: int = 7,
    ) -> int:
        """统计双方在2小时内互相打卡的天数"""
        mutual_days = 0

        for i in range(days):
            target_date = (_utcnow() - timedelta(days=i)).date()
            day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=UTC)
            day_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=UTC)

            # 获取双方当天的打卡时间
            user_checkins = await db.execute(
                select(AccountabilityCheckin.created_at).where(
                    and_(
                        AccountabilityCheckin.partnership_id == partnership_id,
                        AccountabilityCheckin.user_id == user_id,
                        AccountabilityCheckin.created_at >= day_start,
                        AccountabilityCheckin.created_at <= day_end,
                    )
                )
            )
            user_times = [t[0] for t in user_checkins.all()]

            partner_checkins = await db.execute(
                select(AccountabilityCheckin.created_at).where(
                    and_(
                        AccountabilityCheckin.partnership_id == partnership_id,
                        AccountabilityCheckin.user_id == partner_id,
                        AccountabilityCheckin.created_at >= day_start,
                        AccountabilityCheckin.created_at <= day_end,
                    )
                )
            )
            partner_times = [t[0] for t in partner_checkins.all()]

            # 检查是否有在2小时内的打卡
            found_mutual = False
            for user_time in user_times:
                for partner_time in partner_times:
                    if abs((user_time - partner_time).total_seconds()) <= 7200:  # 2小时
                        mutual_days += 1
                        found_mutual = True
                        break
                if found_mutual:
                    break

        return mutual_days

    async def _check_perfect_month_for_user(
        self,
        db: AsyncSession,
        partnership_id: UUID,
        user_id: UUID,
        year: int,
        month: int,
        days_in_month: int,
    ) -> bool:
        """检查用户在指定月份是否每天打卡"""
        month_start = datetime(year, month, 1).replace(tzinfo=UTC)
        month_end = datetime(year, month, days_in_month, 23, 59, 59).replace(tzinfo=UTC)

        # 统计该月份的打卡天数
        result = await db.execute(
            select(func.distinct(func.date(AccountabilityCheckin.created_at))).where(
                and_(
                    AccountabilityCheckin.partnership_id == partnership_id,
                    AccountabilityCheckin.user_id == user_id,
                    AccountabilityCheckin.created_at >= month_start,
                    AccountabilityCheckin.created_at <= month_end,
                )
            )
        )
        checkin_days = len(result.all())

        return checkin_days >= days_in_month

    async def _unlock_achievement(
        self,
        db: AsyncSession,
        user_id: UUID,
        achievement_id: str,
    ) -> bool:
        """
        解锁成就

        Returns:
            True if newly unlocked, False if already unlocked or failed
        """
        # 检查是否已解锁
        existing = await db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            return False

        await self.ensure_achievement_definitions(db)

        # 创建成就记录
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            unlocked_at=_utcnow(),
        )
        db.add(user_achievement)
        await db.commit()

        # 发送通知
        achievement_def = self.ACCOUNTABILITY_ACHIEVEMENTS.get(achievement_id)
        if achievement_def:
            await notification_service.create(
                db,
                user_id,
                {
                    "title": f"🏆 成就解锁：{achievement_def['name']}",
                    "content": achievement_def["description"],
                    "type": "achievement",
                    "data": {
                        "achievement_id": achievement_id,
                        "icon": achievement_def.get("icon", "🏆"),
                        "points": achievement_def.get("points", 0),
                    },
                },
                push_via_websocket=True,
            )

        logger.info(f"Unlocked achievement {achievement_id} for user {user_id}")
        return True


# 单例实例
accountability_achievement_service = AccountabilityAchievementService()
