from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import MEMORY_SETTINGS_UPDATE_TOTAL
from app.models.user_memory_settings import UserMemorySettings
from app.services.memory_policy_evaluator import MemoryPolicyEvaluator
from app.services.profile_write_service import ProfileWriteService

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "allow_preferences": True,
    "allow_goals": True,
    "allow_episodic": True,
    "allow_inferred_episodic": True,
    "capture_level": "medium",
    "blocked_pref_keys": [],
    "blocked_sources": [],
}

#: C-07：读权限门字段（MemoryPolicyEvaluator 读侧逐条消费）。任一变化都会
#: 改变「哪些记忆允许进入 context」，因此必须 epoch bump（缓存键变）+ 派生
#: 缓存 DEL——不区分收紧/放宽方向：放宽后缓存里的旧裁剪视图同样失真。
#: ``capture_level`` 是写侧采集档位（当前读路径无消费者），不在此列。
READ_GATE_FIELDS: frozenset[str] = frozenset(
    {
        "enabled",
        "allow_preferences",
        "allow_goals",
        "allow_episodic",
        "allow_inferred_episodic",
        "blocked_pref_keys",
        "blocked_sources",
    }
)


class MemorySettingsService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def get_or_create(self, user_id: UUID) -> UserMemorySettings:
        record = await self._get_settings(user_id)
        if record:
            return record
        record = UserMemorySettings(user_id=user_id, **DEFAULT_SETTINGS)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_settings(
        self,
        user_id: UUID,
        updates: dict[str, Any],
    ) -> UserMemorySettings:
        record = await self.get_or_create(user_id)
        before = _snapshot(record)

        for key, value in updates.items():
            if value is None:
                continue
            if hasattr(record, key):
                setattr(record, key, value)

        # C-07：读权限门字段变化 → epoch bump 与设置变更**同事务**生效
        # （软删/纠正/权限收紧三类失效面的第三面）。epoch 是 context cache
        # 版本键的组成信号（context_cache_key.resolve_context_cache_versions）
        # 与读侧门比对基准（context_manager），bump 后旧缓存键自然孤儿化。
        # 只写 MemoryCorrection epoch_bump 审计行（bump 助手内置），不发
        # memory.invalidated 事件——该事件词表语义是「记忆记录被失效」，
        # 设置变更不是记忆记录变异；设置侧事实由 diff 日志 +
        # MEMORY_SETTINGS_UPDATE_TOTAL 承载。
        read_gate_changed = bool(READ_GATE_FIELDS & set(_diff_snapshot(before, _snapshot(record)).keys()))
        epoch_bumped = 0
        if read_gate_changed:
            from app.services.memory_invalidation_pipeline import _bump_memory_epoch_in_txn

            epoch_bumped = await _bump_memory_epoch_in_txn(self.db, user_id, reason="permission_change:memory_settings")

        await self.db.commit()
        await self.db.refresh(record)

        if read_gate_changed:
            # 提交后 DEL 派生缓存（加速；读侧 epoch 门/版本键是保证）。
            from app.services.memory_invalidation_pipeline import MemoryInvalidationPipeline

            await MemoryInvalidationPipeline(self.db, self.redis).invalidate_derived_caches(
                user_id=user_id,
                kinds=set(),
            )
            logger.info(
                "Memory settings permission gate changed, epoch bumped user_id={} epoch={}",
                user_id,
                epoch_bumped,
            )

        newly_blocked = set(record.blocked_pref_keys or []) - set(before.get("blocked_pref_keys", []))
        if newly_blocked:
            related_keys = sorted(
                {
                    candidate
                    for key in newly_blocked
                    for candidate in MemoryPolicyEvaluator.expand_blocked_preference_key(key)
                }
            )
            profile_write_service = ProfileWriteService(self.db, self.redis)
            await profile_write_service.remove_inferred_keys(
                user_id=user_id,
                keys=related_keys,
            )

        diff = _diff_snapshot(before, _snapshot(record))
        if diff:
            MEMORY_SETTINGS_UPDATE_TOTAL.inc()
            logger.info(
                "Memory settings updated user_id={user_id} changes={changes}",
                user_id=user_id,
                changes=diff,
            )
        return record

    async def _get_settings(self, user_id: UUID) -> UserMemorySettings | None:
        result = await self.db.execute(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id,
                UserMemorySettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


def _snapshot(record: UserMemorySettings) -> dict[str, Any]:
    return {
        "enabled": record.enabled,
        "allow_preferences": record.allow_preferences,
        "allow_goals": record.allow_goals,
        "allow_episodic": record.allow_episodic,
        "allow_inferred_episodic": getattr(record, "allow_inferred_episodic", True),
        "capture_level": record.capture_level,
        "blocked_pref_keys": list(record.blocked_pref_keys or []),
        "blocked_sources": list(record.blocked_sources or []),
    }


def _diff_snapshot(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for key, value in after.items():
        if before.get(key) != value:
            if key in {"blocked_pref_keys", "blocked_sources"}:
                diff[key] = {
                    "from_count": len(before.get(key, [])),
                    "to_count": len(value or []),
                }
            else:
                diff[key] = {"from": before.get(key), "to": value}
    return diff
