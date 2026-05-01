"""
Budget Optimization Service
预算优化服务

Intelligent budget allocation for context packs using multi-armed bandit algorithms.
"""
import math
from datetime import datetime, timedelta, UTC

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_pack import ContextPackRun
from app.services.budget_tuning_service import BudgetTuningService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BudgetOptimizationService:
    """预算优化服务 - 智能预算分配算法"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tuning_service = BudgetTuningService(db)

    async def optimize_budget_allocation(
        self,
        user_id: str,
        total_budget: int,
        context_packs: list[str],
        performance_window_days: int = 7,
    ) -> dict[str, int]:
        """
        优化预算分配

        使用多臂老虎机算法基于历史效果动态调整预算

        Args:
            user_id: 用户ID
            total_budget: 总预算（Token数）
            context_packs: 上下文包ID列表
            performance_window_days: 性能评估窗口（天）

        Returns:
            Dict[str, int]: 上下文包ID到预算的映射
        """
        # 1. Get performance data for each context pack
        pack_performance = await self._get_pack_performance(
            user_id,
            context_packs,
            performance_window_days,
        )

        # 2. Calculate optimal allocation using UCB1 algorithm
        allocation = await self._ucb1_allocate(
            total_budget,
            pack_performance,
        )

        # 3. Apply constraints (minimum and maximum budgets)
        allocation = await self._apply_constraints(
            allocation,
            total_budget,
            min_budget_per_pack=int(total_budget * 0.05),  # 5% minimum
            max_budget_per_pack=int(total_budget * 0.5),   # 50% maximum
        )

        logger.info(
            f"Optimized budget allocation for user {user_id}: {allocation}"
        )

        return allocation

    async def _get_pack_performance(
        self,
        user_id: str,
        context_pack_ids: list[str],
        days: int,
    ) -> dict[str, dict[str, float]]:
        """
        获取上下文包性能数据

        Args:
            user_id: 用户ID
            context_pack_ids: 上下文包ID列表
            days: 回溯天数

        Returns:
            Dict mapping pack_id to performance metrics
        """
        cutoff_date = _utcnow() - timedelta(days=days)

        performance = {}

        for pack_id in context_pack_ids:
            filters = [
                ContextPackRun.user_id == user_id,
                ContextPackRun.created_at >= cutoff_date,
            ]
            if hasattr(ContextPackRun, "context_pack_id"):
                filters.append(ContextPackRun.context_pack_id == pack_id)
            elif hasattr(ContextPackRun, "intent"):
                # Backward compatibility for schema versions where pack_id was not persisted.
                filters.append(ContextPackRun.intent == pack_id)

            # Get recent runs
            result = await self.db.execute(
                select(ContextPackRun)
                .where(and_(*filters))
                .order_by(ContextPackRun.created_at.desc())
            )
            runs = result.scalars().all()

            if not runs:
                # No data, use default
                performance[pack_id] = {
                    'avg_reward': 0.5,
                    'run_count': 0,
                    'avg_tokens_used': 100,
                }
                continue

            # Calculate metrics
            total_reward = 0.0
            total_tokens = 0
            successful_runs = 0

            for run in runs:
                def _read(field: str, default):
                    if isinstance(run, dict):
                        return run.get(field, default)
                    value = getattr(run, field, None)
                    if value is None and hasattr(run, "metadata_payload"):
                        metadata = getattr(run, "metadata_payload", {}) or {}
                        return metadata.get(field, default)
                    return value if value is not None else default

                # Simple reward: 1.0 if success, 0.0 otherwise
                # In practice, use more sophisticated reward
                reward = 1.0 if _read("success", False) else 0.0
                total_reward += reward
                total_tokens += _read("tokens_used", 0)
                if _read("success", False):
                    successful_runs += 1

            performance[pack_id] = {
                'avg_reward': total_reward / len(runs) if runs else 0.5,
                'run_count': len(runs),
                'avg_tokens_used': total_tokens / len(runs) if runs else 100,
                'success_rate': successful_runs / len(runs) if runs else 0,
            }

        return performance

    async def _ucb1_allocate(
        self,
        total_budget: int,
        performance: dict[str, dict[str, float]],
    ) -> dict[str, int]:
        """
        使用UCB1算法分配预算

        UCB1 = Average Reward + Exploration Bonus

        Args:
            total_budget: 总预算
            performance: 性能数据

        Returns:
            Dict[str, int]: 预算分配
        """
        if not performance:
            return {}

        allocation = {}
        total_count = sum(p['run_count'] for p in performance.values())

        # Calculate UCB1 scores
        scores = {}
        for pack_id, metrics in performance.items():
            count = metrics['run_count']
            avg_reward = metrics['avg_reward']

            if count == 0:
                # Unexplored arm, prioritize
                scores[pack_id] = float('inf')
            else:
                # UCB1 formula
                safe_total_count = max(1, total_count)
                exploration_bonus = (2 * math.log(safe_total_count) / count) ** 0.5
                scores[pack_id] = avg_reward + exploration_bonus

        # Allocate budget proportionally to scores
        total_score = sum(s for s in scores.values() if s != float('inf'))

        for pack_id, score in scores.items():
            if score == float('inf'):
                # Unexplored, give minimum allocation
                allocation[pack_id] = int(total_budget * 0.1)  # 10%
            else:
                ratio = score / total_score if total_score > 0 else 0
                allocation[pack_id] = int(total_budget * ratio)

        return allocation

    async def _apply_constraints(
        self,
        allocation: dict[str, int],
        total_budget: int,
        min_budget_per_pack: int,
        max_budget_per_pack: int,
    ) -> dict[str, int]:
        """
        应用约束条件

        Args:
            allocation: 原始分配
            total_budget: 总预算
            min_budget_per_pack: 每包最小预算
            max_budget_per_pack: 每包最大预算

        Returns:
            Dict[str, int]: 约束后的分配
        """
        # Apply minimum constraint
        for pack_id in allocation:
            if allocation[pack_id] < min_budget_per_pack:
                allocation[pack_id] = min_budget_per_pack

        # Apply maximum constraint
        for pack_id in allocation:
            if allocation[pack_id] > max_budget_per_pack:
                allocation[pack_id] = max_budget_per_pack

        # Ensure total doesn't exceed budget
        total_allocated = sum(allocation.values())
        if total_allocated > total_budget:
            # Scale down proportionally
            scale_factor = total_budget / total_allocated
            for pack_id in allocation:
                allocation[pack_id] = int(allocation[pack_id] * scale_factor)

        return allocation

    async def evaluate_roi(
        self,
        user_id: str,
        context_pack_id: str,
        days: int = 30,
    ) -> dict[str, float]:
        """
        评估预算使用ROI (投资回报率)

        ROI = 学习效果 / Token消耗

        Args:
            user_id: 用户ID
            context_pack_id: 上下文包ID
            days: 评估天数

        Returns:
            Dict with ROI metrics
        """
        performance = await self._get_pack_performance(
            user_id,
            [context_pack_id],
            days,
        )

        if context_pack_id not in performance:
            return {'roi': 0.0, 'learning_effect': 0.0, 'token_cost': 0.0}

        metrics = performance[context_pack_id]

        # Calculate ROI
        # Learning effect approximated by success rate
        learning_effect = metrics['avg_reward']
        # Token cost is proportional to tokens used
        token_cost = metrics['avg_tokens_used']

        roi = learning_effect / token_cost if token_cost > 0 else 0.0

        return {
            'roi': roi,
            'learning_effect': learning_effect,
            'token_cost': token_cost,
            'success_rate': metrics.get('success_rate', 0.0),
        }
