"""
偏好推断服务 - 从用户反馈中学习并调整推断偏好
"""
from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    PREFERENCE_INFERENCE_CONFIDENCE,
    PREFERENCE_INFERENCE_TOTAL,
)

INFERENCE_STEP = 0.05       # 每次反馈调整幅度
MIN_INFERRED = 0.1          # 最小推断值
MAX_INFERRED = 0.9          # 最大推断值
CONFIDENCE_STEP = 0.1       # 置信度步长
MIN_CONFIDENCE = 0.3        # 最小置信度
MAX_CONFIDENCE = 0.95       # 最大置信度
DECAY_WEEKLY = 0.90         # 每周衰减系数

# 震荡抑制配置
COOLDOWN_PERIOD_SECONDS = 300  # 5分钟冷却期
OPPOSITE_DIRECTION_PENALTY = 0.5  # 相反方向调整幅度的惩罚系数


class PreferenceInferenceService:
    """从用户行为和反馈中推断用户偏好"""

    # 反馈原因到偏好调整的映射
    # 格式: (preference_key, delta, confidence_direction)
    REASON_ACTIONS = {
        "verbose": ("depth_preference", -INFERENCE_STEP, "decrease"),
        "incomplete": ("depth_preference", +INFERENCE_STEP, "increase"),
        "too_hard": ("depth_preference", -INFERENCE_STEP, "decrease"),
        "too_simple": ("depth_preference", +INFERENCE_STEP, "increase"),
        "misaligned": ("curiosity_preference", -INFERENCE_STEP, "decrease"),
    }

    # 连续行为模式推断
    # 注意：方向必须与行为含义一致，避免负反馈循环
    BEHAVIOR_PATTERNS = {
        "consecutive_shallow_likes": ("depth_preference", -INFERENCE_STEP),    # 喜欢浅显 -> 降低深度
        "consecutive_deep_engagement": ("depth_preference", +INFERENCE_STEP),  # 深度互动 -> 提高深度
        "quick_skips": ("depth_preference", -INFERENCE_STEP),                   # 快速跳过 -> 降低深度
        "push_ignore_spree": ("daily_cap", -1),                                 # 忽略推送 -> 减少上限
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def process_feedback(
        self,
        user_id: UUID,
        feedback_type: int,  # 1=up, -1=down
        reasons: list[str],
        metadata: dict | None = None
    ) -> dict[str, any]:
        """
        处理用户反馈，更新推断偏好

        Returns:
            更新后的偏好状态和变更记录
        """
        from app.services.personalization.preference_service import PreferenceService
        pref_service = PreferenceService(self.db, self.redis)

        prefs = await pref_service.get_preferences(user_id)
        inferred = prefs.inferred.copy() if prefs.inferred else {}

        applied_changes = {}
        normalized_reasons = self._normalize_reasons(reasons)

        for reason in normalized_reasons:
            if reason in self.REASON_ACTIONS:
                key, delta, conf_dir = self.REASON_ACTIONS[reason]

                # 获取当前推断值（默认为 0.5）
                current_value = inferred.get(key, 0.5)
                current_confidence = inferred.get(f"{key}_confidence", 0.5)

                # 震荡抑制：检查是否在冷却期内收到相反方向反馈
                last_direction_key = f"{key}_last_direction"
                last_update_key = f"{key}_last_updated"

                last_direction = inferred.get(last_direction_key)
                last_update_str = inferred.get(last_update_key)

                if last_direction and last_update_str:
                    try:
                        last_update = datetime.fromisoformat(last_update_str)
                        time_since = (datetime.utcnow() - last_update).total_seconds()

                        # 如果在冷却期内且方向相反，应用惩罚
                        if time_since < COOLDOWN_PERIOD_SECONDS and last_direction != conf_dir:
                            original_delta = delta
                            delta *= OPPOSITE_DIRECTION_PENALTY
                            logger.info(
                                f"Opposite feedback cooldown applied for {key}, "
                                f"delta reduced from {original_delta} to {delta}"
                            )
                    except Exception:
                        pass

                # 计算新值
                new_value = self._clamp(current_value + delta, MIN_INFERRED, MAX_INFERRED)

                # 更新置信度
                if conf_dir == "increase":
                    new_confidence = min(MAX_CONFIDENCE, current_confidence + CONFIDENCE_STEP)
                else:
                    new_confidence = max(MIN_CONFIDENCE, current_confidence + CONFIDENCE_STEP * 0.5)

                inferred[key] = new_value
                inferred[f"{key}_confidence"] = new_confidence
                inferred[f"{key}_last_updated"] = datetime.utcnow().isoformat()
                inferred[last_direction_key] = conf_dir  # 记录方向

                applied_changes[key] = {
                    "from": current_value,
                    "to": new_value,
                    "confidence": new_confidence,
                    "reason": reason
                }

                # 记录指标
                PREFERENCE_INFERENCE_TOTAL.labels(
                    preference_key=key,
                    direction=conf_dir,
                    source="feedback"
                ).inc()

                PREFERENCE_INFERENCE_CONFIDENCE.labels(
                    preference_key=key
                ).set(new_confidence)

        if applied_changes:
            # 更新数据库
            await pref_service.update_inferred(user_id, inferred)

            logger.info(
                f"Preference inference for user {user_id}: {len(applied_changes)} changes",
                extra={"changes": applied_changes}
            )

        return {
            "user_id": str(user_id),
            "changes": applied_changes,
            "inferred": inferred,
            "preference_version": (prefs.version or 0) + 1
        }

    async def process_behavior(
        self,
        user_id: UUID,
        behavior_type: str,
        value: any = None
    ) -> dict[str, any]:
        """
        处理用户行为模式，更新推断偏好
        """
        from app.services.personalization.preference_service import PreferenceService
        pref_service = PreferenceService(self.db, self.redis)

        prefs = await pref_service.get_preferences(user_id)
        inferred = prefs.inferred.copy() if prefs.inferred else {}

        applied_changes = {}

        if behavior_type in self.BEHAVIOR_PATTERNS:
            key, delta = self.BEHAVIOR_PATTERNS[behavior_type]

            # daily_cap 是整数类型，需要特殊处理
            if key == "daily_cap":
                current_value = inferred.get(key, 5)
                new_value = max(1, current_value + delta)
                inferred[key] = new_value
                inferred[f"{key}_confidence"] = 0.4
                inferred[f"{key}_last_updated"] = datetime.utcnow().isoformat()

                applied_changes[key] = {
                    "from": current_value,
                    "to": new_value,
                    "confidence": 0.4,
                    "source": "behavior"
                }
            else:
                current_value = inferred.get(key, 0.5)

                # 对于连续行为，使用更小的步长
                step = abs(delta) * 0.3
                if delta < 0:
                    new_value = max(MIN_INFERRED, current_value - step)
                else:
                    new_value = min(MAX_INFERRED, current_value + step)

                inferred[key] = new_value
                inferred[f"{key}_confidence"] = 0.4  # 行为推断置信度较低
                inferred[f"{key}_last_updated"] = datetime.utcnow().isoformat()

                applied_changes[key] = {
                    "from": current_value,
                    "to": new_value,
                    "confidence": 0.4,
                    "source": "behavior"
                }

            PREFERENCE_INFERENCE_TOTAL.labels(
                preference_key=key,
                direction="increase" if delta > 0 else "decrease",
                source="behavior"
            ).inc()

            PREFERENCE_INFERENCE_CONFIDENCE.labels(
                preference_key=key
            ).set(inferred.get(f"{key}_confidence", 0.4))

        if applied_changes:
            await pref_service.update_inferred(user_id, inferred)

        return {
            "user_id": str(user_id),
            "changes": applied_changes,
            "inferred": inferred
        }

    @staticmethod
    def _normalize_reasons(reasons: list[str]) -> list[str]:
        """标准化反馈原因"""
        normalized = []
        for reason in reasons:
            if isinstance(reason, int):
                # 从 FEEDBACK_REASON_MAP 反查
                from app.services.response_feedback_service import ResponseFeedbackService
                reason_str = ResponseFeedbackService.normalize_reasons([reason])[0]
                normalized.append(reason_str)
            else:
                normalized.append(str(reason).lower())
        return normalized

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))
