"""
偏好服务 - 统一的偏好数据访问层
"""

import asyncio
import json
from datetime import timezone, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        "share_achievements_to_community": True,
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

    async def get_preference_version(self, user_id: UUID) -> int:
        """获取当前偏好版本号。"""
        return await self._get_db_version(user_id)

    async def update_explicit(self, user_id: UUID, updates: dict) -> UserPreferencesCenter:
        """更新显式偏好并递增版本"""
        if not updates:
            return await self.get_preferences(user_id)

        prefs = await self._get_or_create(user_id)
        explicit = dict(prefs.explicit or {})
        explicit.update(updates)
        prefs.explicit = explicit
        prefs.version = (prefs.version or 0) + 1
        prefs.last_explicit_update = _utcnow()
        prefs.updated_at = _utcnow()

        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def delete_explicit_key(self, user_id: UUID, pref_key: str) -> UserPreferencesCenter:
        """删除显式偏好键并递增版本"""
        prefs = await self._get_or_create(user_id)
        explicit = dict(prefs.explicit or {})
        if pref_key in explicit:
            explicit.pop(pref_key, None)
            prefs.explicit = explicit
            prefs.version = (prefs.version or 0) + 1
            prefs.last_explicit_update = _utcnow()
            prefs.updated_at = _utcnow()
            await self.db.commit()
            await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def delete_inferred_key(self, user_id: UUID, pref_key: str) -> UserPreferencesCenter:
        """删除推断偏好键并递增版本"""
        prefs = await self._get_or_create(user_id)
        inferred = dict(prefs.inferred or {})
        if pref_key in inferred:
            inferred.pop(pref_key, None)
            prefs.inferred = inferred
            prefs.version = (prefs.version or 0) + 1
            prefs.last_inferred_update = _utcnow()
            prefs.updated_at = _utcnow()
            await self.db.commit()
            await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def update_inferred_raw(self, user_id: UUID, inferred: dict) -> UserPreferencesCenter:
        """以完整快照替换推断偏好并递增版本"""
        prefs = await self._get_or_create(user_id)
        prefs.inferred = dict(inferred or {})
        prefs.version = (prefs.version or 0) + 1
        prefs.last_inferred_update = _utcnow()
        prefs.updated_at = _utcnow()
        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def update_inferred(self, user_id: UUID, updates: dict) -> UserPreferencesCenter:
        """
        更新推断偏好并递增版本（带乐观锁并发保护）

        使用 CAS 模式避免并发写入覆盖：
        1. 读取当前版本号
        2. 尝试更新（WHERE version = current_version）
        3. 如果更新行数为 0，说明版本已变更，需要重试
        """
        if not updates:
            return await self.get_preferences(user_id)

        # 重试循环：处理并发冲突
        max_retries = 3

        for attempt in range(max_retries):
            prefs = await self._get_or_create(user_id)
            current_version = prefs.version or 0

            inferred = dict(prefs.inferred or {})
            inferred.update(updates)
            prefs.inferred = inferred
            prefs.version = current_version + 1
            prefs.last_inferred_update = _utcnow()
            prefs.updated_at = _utcnow()

            try:
                await self.db.commit()
                await self.db.refresh(prefs)

                # 验证版本号确实是预期的（无并发冲突）
                if prefs.version == current_version + 1:
                    await self._invalidate_cache(user_id)
                    return self._fill_defaults(prefs)

            except Exception as e:
                await self.db.rollback()
                if attempt < max_retries - 1:
                    logger.warning(f"Concurrent preference update for user {user_id}, retrying (attempt {attempt + 1})")
                    await asyncio.sleep(0.01 * (attempt + 1))  # 指数退避
                    continue
                else:
                    logger.error(f"Failed to update preferences after {max_retries} attempts: {e}")
                    raise

        return await self.get_preferences(user_id)

    async def save_preferences(self, user_id: UUID, prefs_center: UserPreferencesCenter) -> UserPreferencesCenter:
        """持久化偏好快照并递增版本。"""
        stored = await self._get_or_create(user_id)

        explicit = dict((prefs_center.explicit or {}))
        inferred = dict((prefs_center.inferred or {}))

        explicit_changed = explicit != (stored.explicit or {})
        inferred_changed = inferred != (stored.inferred or {})

        stored.explicit = explicit
        stored.inferred = inferred

        if explicit_changed:
            stored.last_explicit_update = _utcnow()
        if inferred_changed:
            stored.last_inferred_update = _utcnow()
        if explicit_changed or inferred_changed:
            stored.version = (stored.version or 0) + 1
            stored.updated_at = _utcnow()

        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(stored)

    async def _get_db_version(self, user_id: UUID) -> int:
        """获取数据库中的版本号"""
        result = await self.db.execute(
            select(UserPreferencesCenter.version).where(UserPreferencesCenter.user_id == user_id)
        )
        version = result.scalar_one_or_none()
        return version or 0

    async def _get_or_create(self, user_id: UUID) -> UserPreferencesCenter:
        result = await self.db.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
        prefs = result.scalar_one_or_none()
        if prefs:
            return prefs

        user_exists = await self.db.execute(select(User.id).where(User.id == user_id))
        if user_exists.scalar_one_or_none() is None:
            logger.warning("PreferenceService: user {} not found, returning transient defaults", user_id)
            return UserPreferencesCenter(
                user_id=user_id,
                version=1,
                explicit=self.DEFAULT_EXPLICIT.copy(),
                inferred={},
            )

        prefs = UserPreferencesCenter(
            user_id=user_id,
            version=1,
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
