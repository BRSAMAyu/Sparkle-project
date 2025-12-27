"""
User Service - 生产级实现
用户服务封装，提供用户上下文和偏好数据

特性:
- Cache-Aside 模式: Redis 缓存 + 数据库回源
- JSON 序列化: 兼容性好，支持多语言
- 缓存失效: 用户更新时自动失效
- 容错降级: 缓存/DB 故障时优雅降级
"""
import json
from typing import Optional, Dict, Any
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, PushPreference
from app.schemas.user import UserContext, UserPreferences
from app.core.metrics import CACHE_HIT_COUNT


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

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        根据用户 ID 获取用户实体
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[User]: 用户实体，如果不存在则返回 None
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id, User.is_active == True)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_context(self, user_id: UUID) -> Optional[UserContext]:
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
                    logger.debug(f"Cache HIT for user {user_id}")
                    return context
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

            # 处理 active_slots: 数据库是列表，需要转换为字典格式
            active_slots = None
            if push_pref and push_pref.active_slots:
                if isinstance(push_pref.active_slots, list):
                    # 转换为字典格式
                    active_slots = {"slots": push_pref.active_slots}
                else:
                    active_slots = push_pref.active_slots

            context = UserContext(
                user_id=str(user_id),
                nickname=user.nickname or user.username,
                timezone=push_pref.timezone if push_pref else "Asia/Shanghai",
                language="zh-CN",
                is_pro=user.flame_level >= 3,
                preferences={
                    "depth_preference": user.depth_preference,
                    "curiosity_preference": user.curiosity_preference,
                    "flame_level": user.flame_level,
                    "flame_brightness": user.flame_brightness,
                },
                active_slots=active_slots,
                daily_cap=push_pref.daily_cap if push_pref else 5,
                persona_type=push_pref.persona_type if push_pref else "coach",
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

    async def get_preferences(self, user_id: UUID) -> Optional[UserPreferences]:
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

            # 处理 schedule_preferences: 数据库是列表，需要转换为字典格式
            schedule_preferences = None
            if push_pref and push_pref.active_slots:
                if isinstance(push_pref.active_slots, list):
                    schedule_preferences = {"slots": push_pref.active_slots}
                else:
                    schedule_preferences = push_pref.active_slots

            prefs = UserPreferences(
                learning_depth=user.depth_preference,
                curiosity_level=user.curiosity_preference,
                schedule_preferences=schedule_preferences,
                weather_preferences=user.weather_preferences or {},
                notification_enabled=push_pref.enable_curiosity if push_pref else True,
                persona_type=push_pref.persona_type if push_pref else "coach",
                daily_cap=push_pref.daily_cap if push_pref else 5,
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

    async def get_analytics_summary(self, user_id: UUID) -> Optional[Dict[str, Any]]:
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

    async def _get_push_preference(self, user_id: UUID) -> Optional[PushPreference]:
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

            from datetime import datetime
            user.last_login_at = datetime.utcnow()
            await self.db.commit()
            logger.debug(f"Updated last login for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            return False

    async def get_user_stats(self, user_id: UUID) -> Optional[Dict[str, Any]]:
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

    async def update_user_profile(self, user_id: UUID, updates: Dict[str, Any]) -> bool:
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

            for key, value in updates.items():
                if hasattr(user, key):
                    setattr(user, key, value)
                else:
                    logger.warning(f"User model has no attribute {key}")

            await self.db.commit()
            logger.info(f"Updated user profile for {user_id}: {updates}")

            # 2. 使缓存失效
            await self.invalidate_user_cache(user_id)

            return True
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}")
            await self.db.rollback()
            return False

    async def update_user_preferences(self, user_id: UUID, updates: Dict[str, Any]) -> bool:
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

            await self.db.commit()
            logger.info(f"Updated push preferences for {user_id}: {updates}")

            # 3. 使缓存失效
            await self.invalidate_user_cache(user_id)

            return True
        except Exception as e:
            logger.error(f"Failed to update user preferences for {user_id}: {e}")
            await self.db.rollback()
            return False