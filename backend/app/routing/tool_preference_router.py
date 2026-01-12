"""
Tool Preference Router - 工具偏好路由

基于工具执行历史，学习用户的工具偏好，
优化后续工具选择和工作流路由
"""
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_history import UserToolHistory
from app.services.tool_history_service import ToolHistoryService
from app.learning.bayesian_learner import BayesianLearner


class ToolPreferenceRouter:
    """基于工具历史的偏好路由器"""

    def __init__(self, db_session: AsyncSession, user_id: uuid.UUID, redis_client=None):
        self.db_session = db_session
        self.user_id = user_id
        self.history_service = ToolHistoryService(db_session)

        if redis_client:
            from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
            self.learner = PersistentBayesianLearner(redis_client, str(user_id))
        else:
            self.learner = BayesianLearner()

    async def get_preferred_tools(
        self,
        category: Optional[str] = None,
        limit: int = 5,
        days: int = 30
    ) -> List[str]:
        """
        获取用户偏好的工具列表

        Args:
            category: 工具类别 (plan, task, focus, etc.)
            limit: 返回数量限制
            days: 时间范围

        Returns:
            工具名称列表，按偏好度排序
        """
        preferences = await self.history_service.get_user_preferred_tools(
            user_id=self.user_id,
            limit=limit,
            days=days
        )

        preferred = [p.tool_name for p in preferences]

        logger.info(f"User {self.user_id} preferred tools: {preferred}")

        return preferred

    async def estimate_tool_success_probability(
        self,
        tool_name: str,
        context: Optional[Dict] = None
    ) -> float:
        """
        估计工具成功概率

        Args:
            tool_name: 工具名称
            context: 当前上下文

        Returns:
            成功概率 (0-1)
        """
        # 获取工具统计信息
        stats = await self.history_service.get_tool_success_rate(
            user_id=self.user_id,
            tool_name=tool_name,
            days=30
        )

        # 转换为概率 (0-1)
        success_prob = stats / 100.0

        # 如果context提供，可以进行上下文调整
        if context:
            # 根据时间的生产力峰值调整
            productivity_factor = self._get_productivity_factor(context)
            success_prob *= productivity_factor

        return min(success_prob, 1.0)

    async def rank_tools_by_success(
        self,
        tool_names: List[str],
        context: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        根据成功率对工具进行排序

        Args:
            tool_names: 工具名称列表
            context: 当前上下文

        Returns:
            (工具名, 成功率) 元组列表，按成功率降序排列
        """
        ranked = []

        for tool_name in tool_names:
            success_prob = await self.estimate_tool_success_probability(
                tool_name=tool_name,
                context=context
            )
            ranked.append((tool_name, success_prob))

        # 按成功率排序
        ranked.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Ranked tools: {ranked}")

        return ranked

    async def should_retry_tool(
        self,
        tool_name: str,
        last_failure_time: datetime
    ) -> bool:
        """
        根据历史判断是否应该重试工具

        Args:
            tool_name: 工具名称
            last_failure_time: 最后一次失败的时间

        Returns:
            是否应该重试
        """
        # 获取该工具最近7天的成功率
        recent_stats = await self.history_service.get_tool_success_rate(
            user_id=self.user_id,
            tool_name=tool_name,
            days=7
        )

        # 如果最近成功率 > 50%，值得重试
        if recent_stats > 50:
            return True

        # 如果距上次失败超过3小时，也值得重试
        time_since_failure = datetime.utcnow() - last_failure_time
        if time_since_failure > timedelta(hours=3):
            return True

        return False

    async def get_fallback_tools(
        self,
        primary_tool: str,
        limit: int = 3
    ) -> List[str]:
        """
        获取备选工具列表

        Args:
            primary_tool: 主工具名称
            limit: 返回数量限制

        Returns:
            备选工具列表
        """
        # 获取用户所有已使用过的工具
        all_tools = await self._get_all_used_tools()

        # 排除主工具
        candidates = [t for t in all_tools if t != primary_tool]

        # 按成功率排序
        ranked = await self.rank_tools_by_success(candidates[:10])

        # 返回前N个
        fallbacks = [tool_name for tool_name, _ in ranked[:limit]]

        logger.info(f"Fallback tools for {primary_tool}: {fallbacks}")

        return fallbacks

    async def update_learner_from_history(self) -> None:
        """
        从历史记录更新BayesianLearner

        这个方法定期调用，让学习器根据实际执行历史优化路由决策
        """
        try:
            # 获取最近30天的执行历史
            since = datetime.utcnow() - timedelta(days=30)

            query = select(UserToolHistory).where(
                and_(
                    UserToolHistory.user_id == self.user_id,
                    UserToolHistory.created_at >= since
                )
            ).order_by(desc(UserToolHistory.created_at))

            results = await self.db_session.execute(query)
            records = results.scalars().all()

            # 对每条记录，更新学习器
            for record in records:
                # 工具执行可以看作是 "当前状态" -> "该工具" 的转移
                # success 表示该工具在此状态下是否有效
                source = f"state_{record.tool_category or 'general'}"
                target = record.tool_name

                success = 1 if record.success else 0
                self.learner.update(source, target, success)

            logger.info(f"Updated learner from {len(records)} historical records")

        except Exception as e:
            logger.error(f"Failed to update learner from history: {e}")

    async def _get_all_used_tools(self) -> List[str]:
        """获取用户已使用过的所有工具"""
        query = select(
            UserToolHistory.tool_name
        ).where(
            UserToolHistory.user_id == self.user_id
        ).distinct()

        results = await self.db_session.execute(query)
        return [row[0] for row in results.fetchall()]

    def _get_productivity_factor(self, context: Dict) -> float:
        """
        根据上下文计算生产力因子

        Args:
            context: 执行上下文

        Returns:
            生产力因子 (0.8-1.2)
        """
        # 获取当前小时
        current_hour = datetime.now().hour

        # 根据用户的生产力模式调整
        # 早晨 (6-9)、上午 (9-12)、下午 (14-17) 效率更高
        if 6 <= current_hour < 9:
            return 1.1
        elif 9 <= current_hour < 12:
            return 1.2  # 黄金时段
        elif 14 <= current_hour < 17:
            return 1.1
        elif 17 <= current_hour < 20:
            return 1.0  # 正常
        else:
            return 0.8  # 晚上效率低

    async def generate_tool_recommendation(
        self,
        intent: str,
        available_tools: List[str]
    ) -> str:
        """
        基于意图和用户历史，推荐最合适的工具

        Args:
            intent: 用户意图 (exam_prep, task_decompose, etc.)
            available_tools: 可用工具列表

        Returns:
            推荐的工具名称
        """
        # 按成功率排序可用工具
        ranked = await self.rank_tools_by_success(available_tools)

        if not ranked:
            return available_tools[0] if available_tools else None

        recommended_tool, confidence = ranked[0]

        logger.info(
            f"Recommended tool for intent '{intent}': {recommended_tool} "
            f"(confidence: {confidence:.2f})"
        )

        return recommended_tool

    async def get_tool_stats_snapshot(self, tool_name: str) -> Dict:
        """获取工具统计快照"""
        stats = await self.history_service.get_tool_statistics(
            user_id=self.user_id,
            tool_name=tool_name,
            days=30
        )

        return {
            'tool_name': stats.tool_name,
            'success_rate': stats.success_rate,
            'usage_count': stats.usage_count,
            'avg_time_ms': stats.avg_time_ms,
            'last_used_at': stats.last_used_at.isoformat() if stats.last_used_at else None,
        }
