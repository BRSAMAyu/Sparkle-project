"""
User Service
用户服务封装，提供用户上下文和偏好数据
"""
from typing import Optional, Dict, Any
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, PushPreference
from app.schemas.user import UserContext, UserPreferences


class UserService:
    """
    用户服务
    提供用户上下文、偏好设置等数据
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        logger.info("UserService initialized")

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
        获取用户上下文（用于 LLM Prompt）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[UserContext]: 用户上下文，如果获取失败则返回 None
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None

            # 获取推送偏好
            push_pref = await self._get_push_preference(user_id)

            # 构建上下文
            context = UserContext(
                user_id=str(user_id),
                nickname=user.nickname or user.username,
                timezone=push_pref.timezone if push_pref else "Asia/Shanghai",
                language="zh-CN",  # 默认中文
                is_pro=user.flame_level >= 3,  # 火花等级 3+ 为 Pro
                preferences={
                    "depth_preference": user.depth_preference,
                    "curiosity_preference": user.curiosity_preference,
                    "flame_level": user.flame_level,
                    "flame_brightness": user.flame_brightness,
                },
                # 动态偏好
                active_slots=push_pref.active_slots if push_pref else None,
                daily_cap=push_pref.daily_cap if push_pref else 5,
                persona_type=push_pref.persona_type if push_pref else "coach",
            )

            logger.debug(f"Retrieved context for user {user_id}: {context.nickname}")
            return context

        except Exception as e:
            logger.error(f"Failed to get context for user {user_id}: {e}")
            return None

    async def get_preferences(self, user_id: UUID) -> Optional[UserPreferences]:
        """
        获取用户偏好设置（用于个性化推荐）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[UserPreferences]: 用户偏好
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            push_pref = await self._get_push_preference(user_id)

            prefs = UserPreferences(
                learning_depth=user.depth_preference,
                curiosity_level=user.curiosity_preference,
                schedule_preferences=push_pref.active_slots if push_pref else None,
                weather_preferences=user.weather_preferences or {},
                notification_enabled=push_pref.enable_curiosity if push_pref else True,
                persona_type=push_pref.persona_type if push_pref else "coach",
                daily_cap=push_pref.daily_cap if push_pref else 5,
            )

            return prefs

        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}")
            return None

    async def get_analytics_summary(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        获取用户分析摘要（用于 LLM 上下文）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[Dict]: 分析摘要
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            # 简单的活跃度分析
            is_active = user.last_login_at is not None
            active_level = "active" if is_active else "inactive"
            
            # 基于火花等级的活跃度
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
        获取用户统计信息（用于展示和分析）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[Dict]: 统计信息
        """
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

            return stats

        except Exception as e:
            logger.error(f"Failed to get user stats for user {user_id}: {e}")
            return None
