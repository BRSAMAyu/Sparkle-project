"""
偏好服务 - 统一的偏好数据访问层
"""

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ConcurrentModificationError(RuntimeError):
    """Raised when optimistic concurrency control detects a stale preference version."""


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
        return await self._update_inferred_with_retry(
            user_id,
            merge_fn=lambda _current: dict(inferred or {}),
        )

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

        return await self._update_inferred_with_retry(
            user_id,
            merge_fn=lambda current: {**current, **updates},
        )

    async def _update_inferred_with_retry(
        self,
        user_id: UUID,
        *,
        merge_fn,
        max_retries: int = 3,
    ) -> UserPreferencesCenter:
        for attempt in range(max_retries):
            prefs = await self._get_or_create(user_id)
            current_version = int(prefs.version or 0)
            merged_inferred = merge_fn(dict(prefs.inferred or {}))

            try:
                return await self._update_inferred_with_occ(
                    user_id=user_id,
                    inferred=merged_inferred,
                    expected_version=current_version,
                )
            except ConcurrentModificationError as exc:
                await self.db.rollback()
                if attempt >= max_retries - 1:
                    logger.error(
                        "Preference OCC exhausted for user {} after {} attempts: {}",
                        user_id,
                        max_retries,
                        exc,
                    )
                    raise
                logger.warning(
                    "Preference OCC conflict for user {}, retrying ({}/{})",
                    user_id,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(0.01 * (attempt + 1))

        raise ConcurrentModificationError(f"Failed to update preferences for {user_id}")

    async def _update_inferred_with_occ(
        self,
        *,
        user_id: UUID,
        inferred: dict,
        expected_version: int,
    ) -> UserPreferencesCenter:
        now = _utcnow()
        result = await self.db.execute(
            update(UserPreferencesCenter)
            .where(
                UserPreferencesCenter.user_id == user_id,
                UserPreferencesCenter.version == expected_version,
            )
            .values(
                inferred=dict(inferred or {}),
                version=expected_version + 1,
                last_inferred_update=now,
                updated_at=now,
            )
        )
        if result.rowcount == 0:
            raise ConcurrentModificationError(
                f"Preference version conflict for user {user_id}: expected {expected_version}"
            )

        await self.db.commit()
        refreshed = await self._get_or_create(user_id)
        await self._invalidate_cache(user_id)
        return self._fill_defaults(refreshed)

    async def save_preferences(self, user_id: UUID, prefs_center: UserPreferencesCenter) -> UserPreferencesCenter:
        """持久化偏好快照并递增版本。"""
        stored = await self._get_or_create(user_id)

        explicit = dict(prefs_center.explicit or {})
        inferred = dict(prefs_center.inferred or {})
        traits_prior = dict(prefs_center.traits_prior or {})
        trait_observation_state = dict(prefs_center.trait_observation_state or {})

        explicit_changed = explicit != (stored.explicit or {})
        inferred_changed = inferred != (stored.inferred or {})
        traits_changed = traits_prior != (stored.traits_prior or {})
        observation_state_changed = trait_observation_state != (stored.trait_observation_state or {})
        coldstart_changed = prefs_center.traits_coldstart_completed_at != stored.traits_coldstart_completed_at

        stored.explicit = explicit
        stored.inferred = inferred
        stored.traits_prior = traits_prior
        stored.trait_observation_state = trait_observation_state
        stored.traits_coldstart_completed_at = prefs_center.traits_coldstart_completed_at

        if explicit_changed:
            stored.last_explicit_update = _utcnow()
        if inferred_changed:
            stored.last_inferred_update = _utcnow()
        if explicit_changed or inferred_changed or traits_changed or observation_state_changed or coldstart_changed:
            stored.version = (stored.version or 0) + 1
            stored.updated_at = _utcnow()

        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(stored)

    async def update_traits(
        self,
        user_id: UUID,
        *,
        traits_prior: dict,
        trait_observation_state: dict | None = None,
        traits_coldstart_completed_at: datetime | None = None,
    ) -> UserPreferencesCenter:
        prefs = await self._get_or_create(user_id)
        prefs.traits_prior = dict(traits_prior or {})
        if trait_observation_state is not None:
            prefs.trait_observation_state = dict(trait_observation_state or {})
        if traits_coldstart_completed_at is not None:
            prefs.traits_coldstart_completed_at = traits_coldstart_completed_at
        prefs.version = (prefs.version or 0) + 1
        prefs.updated_at = _utcnow()
        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def update_trait_observation_state(self, user_id: UUID, state: dict) -> UserPreferencesCenter:
        prefs = await self._get_or_create(user_id)
        prefs.trait_observation_state = dict(state or {})
        prefs.version = (prefs.version or 0) + 1
        prefs.updated_at = _utcnow()
        await self.db.commit()
        await self._invalidate_cache(user_id)
        return self._fill_defaults(prefs)

    async def _get_db_version(self, user_id: UUID) -> int:
        """获取数据库中的版本号"""
        result = await self.db.execute(
            select(UserPreferencesCenter.version).where(UserPreferencesCenter.user_id == user_id)
        )
        version = result.scalar_one_or_none()
        return version or 0

    async def _get_or_create(self, user_id: UUID) -> UserPreferencesCenter:
        result = await self.db.execute(
            select(UserPreferencesCenter)
            .where(UserPreferencesCenter.user_id == user_id)
            .execution_options(populate_existing=True)
        )
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
            traits_prior={},
            trait_observation_state={},
        )
        self.db.add(prefs)
        await self.db.commit()
        return prefs

    def _fill_defaults(self, prefs: UserPreferencesCenter) -> UserPreferencesCenter:
        """填充默认值"""
        if prefs.explicit is None:
            prefs.explicit = {}
        if prefs.inferred is None:
            prefs.inferred = {}
        if prefs.traits_prior is None:
            prefs.traits_prior = {}
        if prefs.trait_observation_state is None:
            prefs.trait_observation_state = {}
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
            "traits_prior": prefs.traits_prior,
            "trait_observation_state": prefs.trait_observation_state,
            "traits_coldstart_completed_at": (
                prefs.traits_coldstart_completed_at.isoformat()
                if prefs.traits_coldstart_completed_at is not None
                else None
            ),
        }

    def _dict_to_model(self, data: dict) -> UserPreferencesCenter:
        coldstart_completed_at = data.get("traits_coldstart_completed_at")
        if isinstance(coldstart_completed_at, str) and coldstart_completed_at.strip():
            coldstart_completed_at = datetime.fromisoformat(coldstart_completed_at)
        else:
            coldstart_completed_at = None
        return UserPreferencesCenter(
            user_id=UUID(data["user_id"]),
            version=data.get("version", 1),
            explicit=data.get("explicit", {}),
            inferred=data.get("inferred", {}),
            traits_prior=data.get("traits_prior", {}),
            trait_observation_state=data.get("trait_observation_state", {}),
            traits_coldstart_completed_at=coldstart_completed_at,
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
