"""
Next Action Selection Service

追踪用户对next_action的点击/跳过行为，学习用户偏好
"""
from typing import Optional, Dict, Any
from uuid import UUID
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case

from app.models.next_action_selection import NextActionSelection
from app.services.personalization.preference_service import PreferenceService


class NextActionSelectionService:
    """
    Next Action Selection 服务

    核心功能：
    - 记录用户对next_action的选择行为
    - 根据选择历史学习用户偏好
    - 计算某类action的选择率
    """

    # Action类型到偏好字段的映射
    ACTION_PREFERENCE_MAPPING = {
        "quick_review": "prefers_review",
        "light_expand": "prefers_expand",
        "practice_apply": "prefers_practice",
        "rest_break": "prefers_rest",
        "continue_plan": "prefers_continue_plan",
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)

    async def record_selection(
        self,
        user_id: UUID,
        task_id: UUID,
        action_type: str,
        action_title: str,
        selected: bool = False,
        skipped: bool = False,
        display_position: Optional[int] = None,
        displayed_actions_count: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> NextActionSelection:
        """
        记录用户对next_action的选择行为

        Args:
            user_id: 用户ID
            task_id: 任务ID
            action_type: Action类型 (quick_review, light_expand, etc.)
            action_title: Action标题
            selected: 用户是否点击了该action
            skipped: 用户是否跳过了所有建议
            display_position: 在列表中的位置 (0-based)
            displayed_actions_count: 总共显示了多少个建议
            context: 额外上下文信息

        Returns:
            NextActionSelection记录
        """
        selection = NextActionSelection(
            user_id=user_id,
            task_id=task_id,
            action_type=action_type,
            action_title=action_title,
            selected=selected,
            skipped=skipped,
            display_position=display_position,
            displayed_actions_count=displayed_actions_count,
            context=context,
        )
        self.db.add(selection)
        await self.db.flush()

        logger.info(
            f"[NextActionSelection] Recorded: user={user_id}, action_type={action_type}, "
            f"selected={selected}, skipped={skipped}"
        )

        # 如果是明确的选择行为，触发偏好学习
        if selected or skipped:
            await self._learn_from_selection(user_id, action_type, selected)

        await self.db.commit()
        await self.db.refresh(selection)

        return selection

    async def _learn_from_selection(
        self,
        user_id: UUID,
        action_type: str,
        selected: bool,
    ):
        """
        根据用户选择行为学习偏好

        逻辑：
        - 选择了某类action -> 增加对该类型的偏好
        - 跳过了某类action -> 轻微降低对该类型的偏好
        """
        if action_type not in self.ACTION_PREFERENCE_MAPPING:
            logger.debug(f"[NextActionSelection] Unknown action_type: {action_type}")
            return

        # 计算偏好更新量
        updates: Dict[str, float] = {}

        if selected:
            # 选择了某类action，增加偏好
            updates["action_type_preference"] = {action_type: 0.1}

            # 特定类型的偏好更新
            if action_type == "rest_break":
                # 用户选择了休息，可能表示疲劳
                updates["fatigue_sensitive"] = 0.05
            elif action_type == "quick_review":
                # 用户喜欢回顾，强化深度偏好
                updates["depth_preference"] = 0.02
            elif action_type == "light_expand":
                # 用户喜欢拓展，强化深度偏好
                updates["depth_preference"] = 0.03

        # 应用偏好更新（使用inferred模式）
        await self.preference_service.update_inferred(user_id, updates)
        logger.debug(f"[NextActionSelection] Learned preference for user {user_id}: {updates}")

    async def get_selection_rate(
        self,
        user_id: UUID,
        action_type: str,
        days: int = 30,
    ) -> float:
        """
        计算某类action的选择率

        Args:
            user_id: 用户ID
            action_type: Action类型
            days: 统计最近多少天的数据

        Returns:
            选择率 (0.0 - 1.0)
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # 统计该类型的显示次数和选择次数
        result = await self.db.execute(
            select(
                func.count(NextActionSelection.id).label("total"),
                func.sum(case((NextActionSelection.selected == True, 1), else_=0)).label("selected"),
            )
            .where(
                and_(
                    NextActionSelection.user_id == user_id,
                    NextActionSelection.action_type == action_type,
                    NextActionSelection.created_at >= cutoff_date,
                )
            )
            .group_by(NextActionSelection.action_type)
        )
        row = result.first()

        if not row or row.total == 0:
            return 0.0

        return float(row.selected) / float(row.total)

    async def get_user_action_preferences(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict[str, float]:
        """
        获取用户对各类型action的选择率

        Args:
            user_id: 用户ID
            days: 统计最近多少天的数据

        Returns:
            {action_type: selection_rate} 字典
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # 统计各类型的显示次数和选择次数
        result = await self.db.execute(
            select(
                NextActionSelection.action_type,
                func.count(NextActionSelection.id).label("total"),
                func.sum(case((NextActionSelection.selected == True, 1), else_=0)).label("selected"),
            )
            .where(
                and_(
                    NextActionSelection.user_id == user_id,
                    NextActionSelection.created_at >= cutoff_date,
                )
            )
            .group_by(NextActionSelection.action_type)
        )

        preferences = {}
        for row in result:
            if row.total > 0:
                preferences[row.action_type] = float(row.selected) / float(row.total)

        return preferences

    async def get_skipped_count(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> int:
        """
        获取用户跳过next_action的次数

        Args:
            user_id: 用户ID
            days: 统计最近多少天的数据

        Returns:
            跳过次数
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(func.count(NextActionSelection.id))
            .where(
                and_(
                    NextActionSelection.user_id == user_id,
                    NextActionSelection.skipped == True,
                    NextActionSelection.created_at >= cutoff_date,
                )
            )
        )
        return result.scalar() or 0


# Singleton instance
next_action_selection_service = NextActionSelectionService
