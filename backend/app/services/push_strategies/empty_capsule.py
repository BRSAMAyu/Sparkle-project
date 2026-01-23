"""
Empty Capsule Push Strategy

当用户没有未读胶囊时触发异步生成
"""
from typing import Dict, Any
from uuid import UUID

from app.models.user import User
from app.services.personalization import PushPolicyProfile
from app.services.push_strategies.strategy import PushStrategy


class EmptyCapsuleStrategy(PushStrategy):
    """
    空胶囊触发策略

    当用户没有未读胶囊时触发异步生成
    """
    trigger_type = "empty_capsule"

    async def should_trigger(self, user: User, policy: PushPolicyProfile) -> bool:
        """
        判断是否应该触发

        1. 检查频率设置 - 低频用户不触发
        2. 检查是否有未读胶囊 - 有则不触发
        3. 触发异步生成
        """
        # 1. 检查频率设置
        if policy.curiosity_frequency == "low":
            return False

        # 2. 检查是否有未读胶囊
        from app.services.curiosity_capsule_service import curiosity_capsule_service

        capsules = await curiosity_capsule_service.get_today_capsules(user.id, self.db)
        if len(capsules) > 0:
            return False

        # 3. 触发异步生成
        await self._schedule_capsule_generation(user, policy)
        return True

    async def get_context_data(self, user: User) -> Dict[str, Any]:
        """
        返回上下文数据
        """
        return {
            "capsule_type": "on_demand",
            "trigger_reason": "no_unread_capsules",
        }

    async def _schedule_capsule_generation(self, user: User, policy: PushPolicyProfile):
        """
        调度异步胶囊生成任务

        使用 Celery 异步任务生成胶囊
        """
        from app.core.celery_app import celery_app
        from loguru import logger

        # 获取用户偏好
        from app.services.personalization.preference_service import PreferenceService

        pref_service = PreferenceService(self.db)
        prefs_center = await pref_service.get_preferences(user.id)
        explicit_prefs = prefs_center.explicit or {}

        depth_preference = explicit_prefs.get("depth_preference", 0.5)
        curiosity_preference = explicit_prefs.get("curiosity_preference", 0.5)

        # 根据好奇心偏好计算生成数量
        if curiosity_preference < 0.3:
            requested_count = 1
        elif curiosity_preference < 0.7:
            requested_count = 2
        else:
            requested_count = 3

        # 调度 Celery 任务
        celery_app.send_task(
            "generate_capsules_batch",
            args=(
                str(user.id),
                depth_preference,
                curiosity_preference,
                "push_triggered",
                requested_count,
            ),
            queue="default",
        )

        logger.info(
            f"[EmptyCapsuleStrategy] Scheduled capsule generation for user {user.id}: "
            f"depth={depth_preference:.2f}, curiosity={curiosity_preference:.2f}, "
            f"count={requested_count}"
        )
