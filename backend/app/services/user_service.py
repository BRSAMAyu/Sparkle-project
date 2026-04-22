"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

User Service - 生产级实现
用户服务封装，提供用户上下文和偏好数据

特性:
- Cache-Aside 模式: Redis 缓存 + 数据库回源
- JSON 序列化: 兼容性好，支持多语言
- 缓存失效: 用户更新时自动失效
- 容错降级: 缓存/DB 故障时优雅降级
"""

from __future__ import annotations
import json
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import CACHE_HIT_COUNT
from app.core.security import get_password_hash
from app.models.user import PushPreference, User
from app.schemas.user import UserContext, UserPreferences, UserRegister
from app.services.profile_write_service import ProfileWriteService
from app.services.personalization.preference_service import PreferenceService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_active_users(db: AsyncSession, days: int | None = None) -> list[User]:
    """
    Return active users, optionally preferring recently active accounts.

    When ``days`` is provided we use ``last_login_at`` as a soft activity signal,
    but still fall back to all active users if no recent records exist. This keeps
    scheduled jobs operational in local/dev environments with sparse data.
    """
    stmt = select(User).where(User.is_active.is_(True))
    if days is None:
        result = await db.execute(stmt)
        return list(result.scalars().all())

    cutoff = _utcnow() - timedelta(days=days)
    recent_stmt = stmt.where(User.last_login_at.is_not(None), User.last_login_at >= cutoff)
    recent_result = await db.execute(recent_stmt)
    recent_users = list(recent_result.scalars().all())
    if recent_users:
        return recent_users

    result = await db.execute(stmt)
    return list(result.scalars().all())


class UserService:
    """
    用户服务 - 生产级实现

    特性:
    - Cache-Aside 模式: Redis 缓存 + 数据库回源
    - JSON 序列化: 兼容性好，支持多语言
    - 缓存失效: 用户更新时自动失效
    - 容错降级: 缓存/DB 故障时优雅降级
    """

    def __init__(self, db_session: AsyncSession, redis_client=None):
        self.db = db_session
        self.redis = redis_client
        self.cache_ttl = 1800  # 30分钟
        logger.info("UserService initialized with cache support")

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """
        根据邮箱获取用户实体

        Args:
            email: 用户邮箱

        Returns:
            Optional[User]: 用户实体，如果不存在则返回 None
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user_in: UserRegister) -> User:
        """
        创建用户

        Args:
            user_in: 用户注册信息

        Returns:
            User: 创建后的用户实体
        """
        user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            nickname=user_in.nickname or user_in.username,
            registration_source="email",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """
        根据用户 ID 获取用户实体

        Args:
            user_id: 用户 ID

        Returns:
            Optional[User]: 用户实体，如果不存在则返回 None
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id, User.is_active)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_context(self, user_id: UUID) -> UserContext | None:
        """
        获取用户上下文（带缓存）

        Args:
            user_id: 用户 ID

        Returns:
            Optional[UserContext]: 用户上下文，如果获取失败则返回 None

        策略:
            1. Cache Lookup: 检查 Redis 缓存
            2. DB Query: 缓存未命中时查询数据库
            3. Cache Write: 写入缓存
            4. Fallback: 缓存/DB 失败时返回 None
        """
        cache_key = f"user:context:{user_id}"

        # 1. Cache Lookup
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    CACHE_HIT_COUNT.labels(cache_name="user_context", result="hit").inc()
                    data = json.loads(cached)
                    context = UserContext(**data)
                    pref_service = PreferenceService(self.db, self.redis)
                    current_version = await pref_service.get_preference_version(user_id)
                    if context.preference_version == current_version:
                        logger.debug(f"Cache HIT for user {user_id}")
                        return context
                    logger.info(
                        "User context cache stale for %s: cached_version=%s current_version=%s",
                        user_id,
                        context.preference_version,
                        current_version,
                    )
                CACHE_HIT_COUNT.labels(cache_name="user_context", result="miss").inc()
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}, falling back to DB")

        # 2. Database Query
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None

            push_pref = await self._get_push_preference(user_id)
            pref_service = PreferenceService(self.db, self.redis)
            prefs_center = await pref_service.get_preferences(user_id)
            explicit = prefs_center.explicit if prefs_center else {}
            preference_version = int(getattr(prefs_center, "version", 0) or 0)

            if explicit:
                timezone = explicit.get("timezone", "Asia/Shanghai")
                slot_source = explicit.get("active_slots")
            else:
                timezone = push_pref.timezone if push_pref else "Asia/Shanghai"
                slot_source = push_pref.active_slots if push_pref else None

            active_slots = self._normalize_active_slots(
                slot_source,
                timezone,
            )

            context = UserContext(
                user_id=str(user_id),
                nickname=user.nickname or user.username,
                timezone=timezone,
                language="zh-CN",
                is_pro=user.flame_level >= 3,
                preferences={
                    "depth_preference": explicit.get("depth_preference", user.depth_preference),
                    "curiosity_preference": explicit.get("curiosity_preference", user.curiosity_preference),
                    "flame_level": user.flame_level,
                    "flame_brightness": user.flame_brightness,
                },
                active_slots=active_slots,
                daily_cap=explicit.get("daily_cap", push_pref.daily_cap if push_pref else 5),
                persona_type=explicit.get("persona_type", push_pref.persona_type if push_pref else "coach"),
                preference_version=preference_version,
            )

            # 3. Cache Write
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(context.dict(), ensure_ascii=False)
                    )
                    logger.debug(f"Cache WRITE for user {user_id}")
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")

            logger.debug(f"Retrieved context for user {user_id}: {context.nickname}")
            return context

        except Exception as e:
            logger.error(f"Failed to get context for user {user_id}: {e}")
            return None

    async def get_preferences(self, user_id: UUID) -> UserPreferences | None:
        """
        获取用户偏好设置（带缓存，用于个性化推荐）

        Args:
            user_id: 用户 ID

        Returns:
            Optional[UserPreferences]: 用户偏好

        策略:
            1. Cache Lookup: 检查 Redis 缓存
            2. DB Query: 缓存未命中时查询数据库
            3. Cache Write: 写入缓存
        """
        cache_key = f"user:preferences:{user_id}"

        # 1. Cache Lookup
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    prefs = UserPreferences(**data)
                    logger.debug(f"Preferences cache HIT for user {user_id}")
                    return prefs
            except Exception as e:
                logger.warning(f"Preferences cache lookup failed: {e}")

        # 2. Database Query
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            push_pref = await self._get_push_preference(user_id)
            pref_service = PreferenceService(self.db, self.redis)
            prefs_center = await pref_service.get_preferences(user_id)
            explicit = prefs_center.explicit if prefs_center else {}

            if explicit:
                timezone = explicit.get("timezone", "Asia/Shanghai")
                slot_source = explicit.get("active_slots")
            else:
                timezone = push_pref.timezone if push_pref else "Asia/Shanghai"
                slot_source = push_pref.active_slots if push_pref else None

            schedule_preferences = self._normalize_active_slots(
                slot_source,
                timezone,
            )

            prefs = UserPreferences(
                learning_depth=explicit.get("depth_preference", user.depth_preference),
                curiosity_level=explicit.get("curiosity_preference", user.curiosity_preference),
                schedule_preferences=schedule_preferences,
                weather_preferences=user.weather_preferences or {},
                notification_enabled=explicit.get("enable_push", True),
                persona_type=explicit.get("persona_type", push_pref.persona_type if push_pref else "coach"),
                daily_cap=explicit.get("daily_cap", push_pref.daily_cap if push_pref else 5),
            )

            # 3. Cache Write
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(prefs.dict(), ensure_ascii=False)
                    )
                    logger.debug(f"Preferences cache WRITE for user {user_id}")
                except Exception as e:
                    logger.warning(f"Preferences cache write failed: {e}")

            return prefs

        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}")
            return None

    async def get_analytics_summary(self, user_id: UUID) -> dict[str, Any] | None:
        """
        获取用户分析摘要（带缓存）

        Args:
            user_id: 用户 ID

        Returns:
            Optional[Dict]: 分析摘要
        """
        cache_key = f"user:analytics:{user_id}"

        # 1. Cache Lookup
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    CACHE_HIT_COUNT.labels(cache_name="user_analytics", result="hit").inc()
                    logger.debug(f"Analytics cache HIT for user {user_id}")
                    return json.loads(cached)
                CACHE_HIT_COUNT.labels(cache_name="user_analytics", result="miss").inc()
            except Exception as e:
                logger.warning(f"Analytics cache lookup failed: {e}")

        # 2. Database Query
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            is_active = user.last_login_at is not None
            active_level = "active" if is_active else "inactive"

            flame_level = user.flame_level
            if flame_level >= 5:
                engagement = "very_high"
            elif flame_level >= 3:
                engagement = "high"
            elif flame_level >= 2:
                engagement = "medium"
            else:
                engagement = "low"

            summary = {
                "is_active": is_active,
                "active_level": active_level,
                "engagement_level": engagement,
                "flame_level": flame_level,
                "flame_brightness": user.flame_brightness,
                "depth_preference": user.depth_preference,
                "curiosity_preference": user.curiosity_preference,
                "registration_source": user.registration_source,
            }

            # 3. Cache Write
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(summary, ensure_ascii=False)
                    )
                    logger.debug(f"Analytics cache WRITE for user {user_id}")
                except Exception as e:
                    logger.warning(f"Analytics cache write failed: {e}")

            logger.debug(f"Analytics summary for user {user_id}: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Failed to get analytics summary for user {user_id}: {e}")
            return None

    async def _get_push_preference(self, user_id: UUID) -> PushPreference | None:
        """
        获取推送偏好（内部方法）

        Args:
            user_id: 用户 ID

        Returns:
            Optional[PushPreference]: 推送偏好
        """
        try:
            result = await self.db.execute(
                select(PushPreference).where(PushPreference.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get push preference for user {user_id}: {e}")
            return None

    def _normalize_active_slots(
        self,
        slots: list[dict[str, Any]] | None,
        timezone: str,
    ) -> dict[str, Any] | None:
        """
        将字符串格式的时间段转换为分钟数格式

        输入: [{"start": "08:00", "end": "09:00"}]
        输出: {
            "timezone": "Asia/Shanghai",
            "slots": [{"dow": [0,1,2,3,4], "start_min": 480, "end_min": 540}]
        }
        """
        if not slots:
            return None

        if isinstance(slots, dict):
            slots = slots.get("slots", [])
        if not isinstance(slots, list):
            return None

        normalized = []
        for slot in slots:
            start_min = slot.get("start_min")
            end_min = slot.get("end_min")
            if start_min is None:
                start_str = slot.get("start", "08:00")
                start_min = self._time_str_to_minutes(start_str)
            if end_min is None:
                end_str = slot.get("end", "09:00")
                end_min = self._time_str_to_minutes(end_str)
            dow = slot.get("dow", [0, 1, 2, 3, 4])

            normalized.append({
                "dow": dow,
                "start_min": start_min,
                "end_min": end_min,
            })

        return {
            "timezone": timezone,
            "slots": normalized,
        }

    def _time_str_to_minutes(self, time_str: str) -> int:
        """将 "HH:MM" 转换为分钟数"""
        try:
            parts = time_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return 480

    async def update_last_login(self, user_id: UUID) -> bool:
        """
        更新最后登录时间

        Args:
            user_id: 用户 ID

        Returns:
            bool: 是否成功
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False

            from datetime import timezone, datetime
            user.last_login_at = _utcnow()
            await self.db.commit()
            logger.debug(f"Updated last login for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            return False

    async def get_user_stats(self, user_id: UUID) -> dict[str, Any] | None:
        """
        获取用户统计信息（带缓存，用于展示和分析）

        Args:
            user_id: 用户 ID

        Returns:
            Optional[Dict]: 统计信息

        策略:
            1. Cache Lookup: 检查 Redis 缓存
            2. DB Query: 缓存未命中时查询数据库
            3. Cache Write: 写入缓存
        """
        cache_key = f"user:stats:{user_id}"

        # 1. Cache Lookup
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    logger.debug(f"Stats cache HIT for user {user_id}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Stats cache lookup failed: {e}")

        # 2. Database Query
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            push_pref = await self._get_push_preference(user_id)

            stats = {
                "user_id": str(user_id),
                "username": user.username,
                "nickname": user.nickname,
                "flame_level": user.flame_level,
                "flame_brightness": user.flame_brightness,
                "depth_preference": user.depth_preference,
                "curiosity_preference": user.curiosity_preference,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "status": user.status.value if user.status else "offline",
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                "registration_source": user.registration_source,
                "push_preferences": {
                    "timezone": push_pref.timezone if push_pref else "Asia/Shanghai",
                    "enable_curiosity": push_pref.enable_curiosity if push_pref else True,
                    "persona_type": push_pref.persona_type if push_pref else "coach",
                    "daily_cap": push_pref.daily_cap if push_pref else 5,
                    "active_slots": push_pref.active_slots if push_pref else None,
                } if push_pref else None,
            }

            # 3. Cache Write
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(stats, ensure_ascii=False)
                    )
                    logger.debug(f"Stats cache WRITE for user {user_id}")
                except Exception as e:
                    logger.warning(f"Stats cache write failed: {e}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get user stats for user {user_id}: {e}")
            return None

    async def invalidate_user_cache(self, user_id: UUID) -> bool:
        """
        使用户缓存失效（在用户更新资料时调用）

        Args:
            user_id: 用户 ID

        Returns:
            bool: 是否成功

        说明:
            当用户资料更新时，需要立即清除相关缓存，
            避免返回过期数据
        """
        if not self.redis:
            logger.warning("Redis not available, skipping cache invalidation")
            return False

        keys = [
            f"user:context:{user_id}",
            f"user:context:snapshot:{user_id}",
            f"user:prefs:center:{user_id}",
            f"user:analytics:{user_id}",
            f"user:preferences:{user_id}",
            f"user:stats:{user_id}",
        ]

        try:
            await self.redis.delete(*keys)
            logger.info(f"Invalidated cache for user {user_id}, keys: {keys}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache for user {user_id}: {e}")
            return False

    async def update_user_profile(self, user_id: UUID, updates: dict[str, Any]) -> bool:
        """
        更新用户资料并使缓存失效

        Args:
            user_id: 用户 ID
            updates: 要更新的字段和值

        Returns:
            bool: 是否成功

        示例:
            await user_service.update_user_profile(
                user_id,
                {"nickname": "新昵称", "depth_preference": 0.8}
            )
        """
        try:
            # 1. 更新数据库
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            pref_updates = {}
            for key, value in updates.items():
                if hasattr(user, key):
                    setattr(user, key, value)
                    if key in ("depth_preference", "curiosity_preference"):
                        pref_updates[key] = value
                else:
                    logger.warning(f"User model has no attribute {key}")

            await self.db.commit()
            logger.info(f"Updated user profile for {user_id}: {updates}")

            if pref_updates:
                profile_write_service = ProfileWriteService(self.db, self.redis)
                await profile_write_service.set_explicit_preferences(
                    user_id=user_id,
                    updates=pref_updates,
                    evidence_refs_by_key={
                        key: [{"type": "user_state", "id": "user_profile", "schema_version": "user_profile.v1"}]
                        for key in pref_updates
                    },
                    source_type="user_state",
                    source="manual_edit",
                )

            # 2. 使缓存失效
            await self.invalidate_user_cache(user_id)

            return True
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}")
            await self.db.rollback()
            return False

    async def update_user_preferences(self, user_id: UUID, updates: dict[str, Any]) -> bool:
        """
        更新用户偏好设置并使缓存失效

        Args:
            user_id: 用户 ID
            updates: 要更新的偏好字段和值

        Returns:
            bool: 是否成功

        示例:
            await user_service.update_user_preferences(
                user_id,
                {"persona_type": "anime", "daily_cap": 10}
            )
        """
        try:
            # 1. 获取或创建推送偏好
            push_pref = await self._get_push_preference(user_id)
            if not push_pref:
                logger.warning(f"PushPreference not found for user {user_id}")
                return False

            # 2. 更新偏好
            for key, value in updates.items():
                if hasattr(push_pref, key):
                    setattr(push_pref, key, value)
                else:
                    logger.warning(f"PushPreference model has no attribute {key}")

            pref_updates = dict(updates)
            if "active_slots" in pref_updates:
                normalized = self._normalize_active_slots(
                    pref_updates.get("active_slots"),
                    pref_updates.get("timezone", push_pref.timezone if push_pref else "Asia/Shanghai"),
                )
                pref_updates["active_slots"] = normalized["slots"] if normalized else []
            if "enable_curiosity" in pref_updates:
                pref_updates["enable_curiosity_push"] = pref_updates.pop("enable_curiosity")

            profile_write_service = ProfileWriteService(self.db, self.redis)
            await profile_write_service.set_explicit_preferences(
                user_id=user_id,
                updates=pref_updates,
                evidence_refs_by_key={
                    key: [{"type": "user_state", "id": "user_service", "schema_version": "user_service.v1"}]
                    for key in pref_updates
                },
                source_type="user_state",
                source="manual_edit",
            )

            logger.info(f"Updated push preferences for {user_id}: {updates}")

            # 3. 使缓存失效
            await self.invalidate_user_cache(user_id)

            return True
        except Exception as e:
            logger.error(f"Failed to update user preferences for {user_id}: {e}")
            await self.db.rollback()
            return False


# Optional module-level alias for legacy imports (tests expect this symbol).
user_service = None
