"""
推断偏好衰减服务 - 基于时间衰减推断偏好值
"""
from datetime import datetime, timedelta
from uuid import UUID
from typing import Dict, List, Optional
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import UserPreferencesCenter
from app.core.metrics import PREFERENCE_DECAY_APPLIED_TOTAL


# 衰减配置
DECAY_WEEKLY_FACTOR = 0.90      # 每周衰减系数
DECAY_MIN_CONFIDENCE = 0.25     # 最小置信度阈值
DECAY_RESET_THRESHOLD = 0.30    # 低于此值则重置
DECAY_CHECK_INTERVAL_DAYS = 7   # 检查间隔（天）
MAX_AGE_DAYS = 90               # 最大保留天数


class InferredPreferenceDecayService:
    """推断偏好衰减服务"""

    # 需要衰减的偏好键（数值型）
    DECAY_KEYS = {
        "depth_preference",
        "curiosity_preference",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_decay_to_user(self, user_id: UUID) -> Dict[str, any]:
        """
        对单个用户的推断偏好应用衰减

        Returns:
            衰减结果统计
        """
        result = await self.db.execute(
            select(UserPreferencesCenter).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()

        if not prefs or not prefs.inferred:
            return {"status": "no_data", "changes": 0}

        changes = 0
        reset_keys = []
        decayed_values = {}

        now = datetime.utcnow()
        inferred = prefs.inferred.copy()

        # 检查最后更新时间
        if prefs.last_inferred_update:
            days_since_update = (now - prefs.last_inferred_update).days
        else:
            days_since_update = 30  # 默认值

        for key in self.DECAY_KEYS:
            if key not in inferred:
                continue

            current_value = inferred[key]
            if not isinstance(current_value, (int, float)):
                continue

            # 计算衰减：向基准值 (baseline=0.5) 回归
            # 公式：decayed = baseline + (current - baseline) * decay_factor
            # 验证：0.5 + (0.2 - 0.5) * 0.9 = 0.23 (低值向中性回归)
            # 验证：0.5 + (0.8 - 0.5) * 0.9 = 0.77 (高值向中性回归)
            baseline = 0.5
            weeks_elapsed = days_since_update / 7.0
            decay_factor = DECAY_WEEKLY_FACTOR ** weeks_elapsed
            decayed_value = baseline + (current_value - baseline) * decay_factor

            # 衰减置信度
            confidence_key = f"{key}_confidence"
            current_confidence = inferred.get(confidence_key, 0.5)
            decayed_confidence = current_confidence * decay_factor

            if decayed_value < DECAY_RESET_THRESHOLD:
                # 重置为默认值
                inferred[key] = 0.5
                inferred[confidence_key] = 0.3
                reset_keys.append(key)
                PREFERENCE_DECAY_APPLIED_TOTAL.labels(
                    preference_key=key,
                    action="reset"
                ).inc()
            elif decayed_value != current_value:
                # 应用衰减值
                inferred[key] = max(0.1, decayed_value)
                inferred[confidence_key] = max(DECAY_MIN_CONFIDENCE, decayed_confidence)
                inferred[f"{key}_last_decayed"] = now.isoformat()
                decayed_values[key] = {
                    "from": current_value,
                    "to": inferred[key],
                    "factor": decay_factor
                }
                PREFERENCE_DECAY_APPLIED_TOTAL.labels(
                    preference_key=key,
                    action="decay"
                ).inc()

            changes += 1

        # 清理过期的推断数据
        cleaned = self._cleanup_stale_data(inferred, now)

        if changes > 0 or cleaned > 0:
            prefs.inferred = inferred
            prefs.last_inferred_update = now
            prefs.updated_at = now
            prefs.version = (prefs.version or 0) + 1

            await self.db.commit()

            logger.info(
                f"Decay applied for user {user_id}: "
                f"changes={changes}, reset={len(reset_keys)}, cleaned={cleaned}"
            )

        return {
            "status": "applied",
            "changes": changes,
            "reset_keys": reset_keys,
            "decayed_values": decayed_values,
            "cleaned": cleaned
        }

    async def apply_decay_batch(self, limit: int = 100, offset: int = 0) -> Dict[str, any]:
        """
        批量应用衰减到所有有推断偏好的活跃用户

        Args:
            limit: 每批处理的用户数
            offset: 偏移量，用于分页

        Returns:
            批量处理统计
        """
        # 获取有推断偏好的用户（使用 user_id 排序保证分页一致性）
        result = await self.db.execute(
            select(UserPreferencesCenter)
            .where(
                UserPreferencesCenter.inferred.isnot(None),
                UserPreferencesCenter.inferred != '{}'
            )
            .order_by(UserPreferencesCenter.user_id)
            .limit(limit)
            .offset(offset)
        )
        prefs_list = result.scalars().all()

        total_processed = 0
        total_changes = 0
        total_resets = 0
        errors = []

        for prefs in prefs_list:
            try:
                result = await self.apply_decay_to_user(prefs.user_id)
                total_processed += 1
                total_changes += result.get("changes", 0)
                total_resets += len(result.get("reset_keys", []))
            except Exception as e:
                logger.error(f"Error decaying preferences for user {prefs.user_id}: {e}")
                errors.append(str(prefs.user_id))

        logger.info(
            f"Batch decay completed: "
            f"processed={total_processed}, changes={total_changes}, resets={total_resets}, errors={len(errors)}"
        )

        return {
            "processed": total_processed,
            "changes": total_changes,
            "resets": total_resets,
            "errors": errors
        }

    def _cleanup_stale_data(self, inferred: Dict, now: datetime) -> int:
        """清理过期的推断数据"""
        cleaned = 0
        keys_to_remove = []

        for key, value in list(inferred.items()):
            if key.endswith("_last_updated") or key.endswith("_last_decayed"):
                try:
                    if isinstance(value, str):
                        value_datetime = datetime.fromisoformat(value)
                    else:
                        continue
                    if (now - value_datetime).days > MAX_AGE_DAYS:
                        # 移除相关的所有推断数据
                        base_key = key.replace("_last_updated", "").replace("_last_decayed", "")
                        keys_to_remove.append(base_key)
                except (ValueError, TypeError):
                    pass

        for key in keys_to_remove:
            inferred.pop(key, None)
            inferred.pop(f"{key}_confidence", None)
            inferred.pop(f"{key}_last_updated", None)
            inferred.pop(f"{key}_last_decayed", None)
            inferred.pop(f"{key}_last_direction", None)
            cleaned += 1

        return cleaned
