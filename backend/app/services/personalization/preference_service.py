"""
偏好服务 - 统一的偏好数据访问层
"""
import json
from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import UserPreferencesCenter


class PreferenceService:
    """偏好服务 - 带缓存的偏好数据访问"""

    DEFAULT_EXPLICIT = {
        "depth_preference": 0.5,
        "curiosity_preference": 0.5,
        "persona_type": "coach",
        "daily_cap": 5,
        "timezone": "Asia/Shanghai",
        "active_slots": [],
        "learning_style": "balanced",
        "feedback_style": "balanced",
        "ai_verbosity": "balanced",
        "focus_duration_preference": 25,
        "enable_push": True,
        "enable_curiosity_push": True,
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.cache_ttl = 1800  # 30分钟

    async def get_preferences(self, user_id: UUID) -> UserPreferencesCenter:
        """获取用户偏好（带缓存）"""
        cache_key = f"user:prefs:center:{user_id}"

        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    db_version = await self._get_db_version(user_id)
                    if data.get("version") == db_version:
                        prefs = self._dict_to_model(data)
                        return self._fill_defaults(prefs)
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

        prefs = await self._get_or_create(user_id)

        prefs = self._fill_defaults(prefs)

        if self.redis:
            try:
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(self._model_to_dict(prefs), ensure_ascii=False),
                )
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return prefs

    async def update_explicit(self, user_id: UUID, updates: dict) -> UserPreferencesCenter:
        """更新显式偏好并递增版本"""
        if not updates:
            return await self.get_preferences(user_id)

        prefs = await self._get_or_create(user_id)
        if prefs.explicit is None:
            prefs.explicit = {}
        prefs.explicit.update(updates)
        prefs.version = (prefs.version or 0) + 1
        prefs.last_explicit_update = datetime.utcnow()
        prefs.updated_at = datetime.utcnow()

        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def update_inferred(self, user_id: UUID, updates: dict) -> UserPreferencesCenter:
        """更新推断偏好并递增版本"""
        if not updates:
            return await self.get_preferences(user_id)

        prefs = await self._get_or_create(user_id)
        if prefs.inferred is None:
            prefs.inferred = {}
        prefs.inferred.update(updates)
        prefs.version = (prefs.version or 0) + 1
        prefs.last_inferred_update = datetime.utcnow()
        prefs.updated_at = datetime.utcnow()

        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def _get_db_version(self, user_id: UUID) -> int:
        """获取数据库中的版本号"""
        result = await self.db.execute(
            select(UserPreferencesCenter.version).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        version = result.scalar_one_or_none()
        return version or 0

    async def _get_or_create(self, user_id: UUID) -> UserPreferencesCenter:
        result = await self.db.execute(
            select(UserPreferencesCenter).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()
        if prefs:
            return prefs
        prefs = UserPreferencesCenter(
            user_id=user_id,
            explicit=self.DEFAULT_EXPLICIT.copy(),
            inferred={},
        )
        self.db.add(prefs)
        await self.db.commit()
        return prefs

    def _fill_defaults(self, prefs: UserPreferencesCenter) -> UserPreferencesCenter:
        """填充默认值"""
        if prefs.explicit is None:
            prefs.explicit = {}
        for key, default in self.DEFAULT_EXPLICIT.items():
            if key not in prefs.explicit or prefs.explicit[key] is None:
                prefs.explicit[key] = default
        return prefs

    def _model_to_dict(self, prefs: UserPreferencesCenter) -> dict:
        return {
            "user_id": str(prefs.user_id),
            "version": prefs.version,
            "explicit": prefs.explicit,
            "inferred": prefs.inferred,
        }

    def _dict_to_model(self, data: dict) -> UserPreferencesCenter:
        return UserPreferencesCenter(
            user_id=UUID(data["user_id"]),
            version=data.get("version", 1),
            explicit=data.get("explicit", {}),
            inferred=data.get("inferred", {}),
        )

    async def _invalidate_cache(self, user_id: UUID) -> None:
        if not self.redis:
            return
        keys = [
            f"user:prefs:center:{user_id}",
            f"user:context:{user_id}",
            f"user:context:snapshot:{user_id}",
            f"user:preferences:{user_id}",
            f"user:analytics:{user_id}",
            f"user:stats:{user_id}",
        ]
        try:
            await self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Failed to invalidate preference caches: {e}")
