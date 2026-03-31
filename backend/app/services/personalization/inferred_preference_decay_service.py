"""
推断偏好衰减服务 - 基于时间衰减推断偏好值
"""
from datetime import timezone, datetime
from math import isclose
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import PREFERENCE_DECAY_APPLIED_TOTAL
from app.models.user_preferences import UserPreferencesCenter

# 衰减配置
DECAY_WEEKLY_FACTOR = 0.90      # 每周衰减系数
DECAY_MIN_CONFIDENCE = 0.25     # 最小置信度阈值
DECAY_CHECK_INTERVAL_DAYS = 7   # 检查间隔（天）
MAX_AGE_DAYS = 90               # 最大保留天数


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InferredPreferenceDecayService:
    """推断偏好衰减服务"""
    NON_DECAY_SUFFIXES = (
        "_confidence",
        "_last_updated",
        "_last_decayed",
        "_last_direction",
    )
    NON_DECAY_EXACT_KEYS = {
        "push_receptivity_last_updated",
    }
    NON_DECAY_TOKEN_PATTERNS = (
        "_count",
        ".count",
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_decay_to_user(self, user_id: UUID) -> dict[str, any]:
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

        now = _utcnow()
        inferred = prefs.inferred.copy()

        for key, current_value in list(inferred.items()):
            if not self._should_decay_key(key, current_value):
                continue

            last_touched = self._resolve_last_touched_at(inferred, key, prefs.last_inferred_update)
            if last_touched is None:
                continue
            days_since_update = max((now - last_touched).days, 0)
            if days_since_update < DECAY_CHECK_INTERVAL_DAYS:
                continue

            baseline = 0.5
            weeks_elapsed = days_since_update / 7.0
            decay_factor = DECAY_WEEKLY_FACTOR ** weeks_elapsed
            decayed_value = baseline + (float(current_value) - baseline) * decay_factor

            confidence_key = f"{key}_confidence"
            current_confidence = inferred.get(confidence_key, 0.5)
            if isinstance(current_confidence, bool) or not isinstance(current_confidence, (int, float)):
                current_confidence = 0.5
            decayed_confidence = max(DECAY_MIN_CONFIDENCE, float(current_confidence) * decay_factor)

            next_value = self._normalize_decayed_value(key, current_value, decayed_value)
            if isclose(float(next_value), float(current_value), rel_tol=0.0, abs_tol=1e-6):
                continue

            inferred[key] = next_value
            inferred[confidence_key] = decayed_confidence
            inferred[f"{key}_last_decayed"] = now.isoformat()
            decayed_values[key] = {
                "from": current_value,
                "to": next_value,
                "factor": decay_factor,
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

    def _should_decay_key(self, key: str, value: object) -> bool:
        if key in self.NON_DECAY_EXACT_KEYS:
            return False
        if any(key.endswith(suffix) for suffix in self.NON_DECAY_SUFFIXES):
            return False
        if any(token in key for token in self.NON_DECAY_TOKEN_PATTERNS):
            return False
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return True

    def _resolve_last_touched_at(
        self,
        inferred: dict[str, object],
        key: str,
        fallback: datetime | None,
    ) -> datetime | None:
        for candidate in (inferred.get(f"{key}_last_updated"), inferred.get(f"{key}_last_decayed")):
            if isinstance(candidate, str):
                try:
                    return datetime.fromisoformat(candidate)
                except ValueError:
                    continue
        return fallback

    def _normalize_decayed_value(self, key: str, original_value: float | int, decayed_value: float) -> float | int:
        clamped = max(0.0, min(1.0, decayed_value)) if self._looks_like_ratio(key, original_value) else max(0.0, decayed_value)
        if isinstance(original_value, int) and not isinstance(original_value, bool) and self._should_round_to_int(key):
            return int(round(clamped))
        return round(clamped, 4)

    @staticmethod
    def _looks_like_ratio(key: str, original_value: float | int) -> bool:
        if 0.0 <= float(original_value) <= 1.0:
            return True
        ratio_tokens = (
            "rate",
            "ratio",
            "score",
            "preference",
            "completion",
            "receptivity",
            "accuracy",
            "consistency",
            "complexity",
            "delegate",
            "approval",
            "quality",
        )
        return any(token in key for token in ratio_tokens)

    @staticmethod
    def _should_round_to_int(key: str) -> bool:
        return any(token in key for token in ("duration", "_hours", "hour_", "minutes"))

    async def apply_decay_batch(self, limit: int = 100, offset: int = 0) -> dict[str, any]:
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

    def _cleanup_stale_data(self, inferred: dict, now: datetime) -> int:
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
