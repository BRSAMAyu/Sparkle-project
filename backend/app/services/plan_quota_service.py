"""
Plan Quota Service
并行计划数限制服务 - P0优先级

功能:
- 限制用户可同时拥有的活跃计划数量
- 支持配额扩展机制（VIP用户）
- 自动主计划选择逻辑
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.exceptions import QuotaExceededError
from app.models.plan import Plan, PlanPriority


@dataclass
class QuotaStatus:
    """配额状态"""
    used: int           # 已使用配额
    limit: int          # 配额上限
    remaining: int      # 剩余配额
    is_unlimited: bool  # 是否无限制
    primary_plan_id: UUID | None = None  # 当前主计划ID


class PlanQuotaService:
    """
    计划配额管理服务

    职责:
    - 检查用户是否可以创建新计划
    - 获取用户配额状态
    - 自动设置和管理主计划
    """

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self._cache_ttl = 300  # 5分钟缓存

    async def check_quota_available(
        self,
        user_id: UUID,
        plan_type: str | None = None
    ) -> tuple[bool, str]:
        """
        检查用户是否可以创建新计划

        Args:
            user_id: 用户ID
            plan_type: 计划类型（可选，未来可能按类型限制）

        Returns:
            (是否允许, 失败原因)
        """
        quota = await self._get_user_quota(user_id)

        # 无限制用户
        if quota == settings.PLAN_QUOTA_UNLIMITED:
            return True, ""

        active_count = await self._count_active_plans(user_id)

        if active_count >= quota:
            reason = f"已达计划数量上限({quota}个)，请归档旧计划或升级账户"
            logger.info(f"User {user_id} quota exceeded: {active_count}/{quota}")
            return False, reason

        return True, ""

    async def check_and_raise(
        self,
        user_id: UUID,
        plan_type: str | None = None
    ) -> None:
        """
        检查配额并在超限时抛出异常

        Args:
            user_id: 用户ID
            plan_type: 计划类型

        Raises:
            QuotaExceededError: 配额超限
        """
        available, reason = await self.check_quota_available(user_id, plan_type)
        if not available:
            quota = await self._get_user_quota(user_id)
            active_count = await self._count_active_plans(user_id)
            raise QuotaExceededError(
                message=reason,
                detail={"plan_type": plan_type},
                current_count=active_count,
                max_quota=quota
            )

    async def get_quota_status(self, user_id: UUID) -> QuotaStatus:
        """
        获取用户配额状态

        Args:
            user_id: 用户ID

        Returns:
            QuotaStatus: 配额状态详情
        """
        quota = await self._get_user_quota(user_id)
        active_count = await self._count_active_plans(user_id)
        primary_plan = await self._get_primary_plan(user_id)

        is_unlimited = quota == settings.PLAN_QUOTA_UNLIMITED
        remaining = float('inf') if is_unlimited else max(0, quota - active_count)

        return QuotaStatus(
            used=active_count,
            limit=quota,
            remaining=int(remaining) if not is_unlimited else -1,
            is_unlimited=is_unlimited,
            primary_plan_id=primary_plan.id if primary_plan else None
        )

    async def auto_set_primary_plan(
        self,
        user_id: UUID,
        new_plan_id: UUID | None = None
    ) -> UUID | None:
        """
        自动设置主计划

        优先级逻辑:
        1. 如果指定了new_plan_id，设为主计划
        2. 否则，选择优先级最高的活跃计划
        3. 优先级相同时，选择target_date最近的
        4. 都相同时，选择最新创建的

        Args:
            user_id: 用户ID
            new_plan_id: 指定的新主计划ID（可选）

        Returns:
            新主计划的ID，如果没有活跃计划则返回None
        """
        # 清除所有主计划标记
        await self._clear_primary_flags(user_id)

        if new_plan_id:
            # 设置指定计划为主计划
            await self._set_primary(user_id, new_plan_id)
            return new_plan_id

        # 自动选择主计划
        primary_plan = await self._select_best_primary_plan(user_id)

        if primary_plan:
            await self._set_primary(user_id, primary_plan.id)
            return primary_plan.id

        return None

    async def set_primary_plan(
        self,
        user_id: UUID,
        plan_id: UUID
    ) -> bool:
        """
        手动设置指定计划为主计划

        Args:
            user_id: 用户ID
            plan_id: 计划ID

        Returns:
            是否设置成功
        """
        # 验证计划存在且属于该用户
        query = select(Plan).where(
            and_(
                Plan.id == plan_id,
                Plan.user_id == user_id,
                Plan.is_active
            )
        )
        result = await self.db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            logger.warning(f"Plan {plan_id} not found or inactive for user {user_id}")
            return False

        # 清除其他主计划标记并设置新主计划
        await self._clear_primary_flags(user_id)
        await self._set_primary(user_id, plan_id)

        logger.info(f"Primary plan set to {plan_id} for user {user_id}")
        return True

    async def ensure_primary_exists(self, user_id: UUID) -> UUID | None:
        """
        确保用户有主计划（如果有活跃计划的话）

        如果没有主计划但有活跃计划，自动选择一个

        Args:
            user_id: 用户ID

        Returns:
            主计划ID
        """
        primary = await self._get_primary_plan(user_id)
        if primary:
            return primary.id

        # 没有主计划，自动选择
        return await self.auto_set_primary_plan(user_id)

    # ============ 私有方法 ============

    async def _get_user_quota(self, user_id: UUID) -> int:
        """
        获取用户配额限制

        TRACKED(TD-007): 未来可以从用户订阅信息中获取
        """
        # 先检查缓存
        if self.redis:
            cache_key = f"plan_quota:{user_id}"
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return int(cached)
            except Exception as e:
                logger.warning(f"Redis get quota failed: {e}")

        # 默认返回免费用户配额
        # TRACKED(TD-007): 查询用户订阅状态，返回对应配额
        return settings.PLAN_QUOTA_DEFAULT

    async def _count_active_plans(self, user_id: UUID) -> int:
        """统计用户活跃计划数"""
        query = select(func.count(Plan.id)).where(
            and_(
                Plan.user_id == user_id,
                Plan.is_active
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one() or 0

    async def _get_primary_plan(self, user_id: UUID) -> Plan | None:
        """获取用户当前主计划"""
        query = select(Plan).where(
            and_(
                Plan.user_id == user_id,
                Plan.is_active,
                Plan.is_primary
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _clear_primary_flags(self, user_id: UUID) -> None:
        """清除用户所有计划的主计划标记"""
        stmt = (
            update(Plan)
            .where(
                and_(
                    Plan.user_id == user_id,
                    Plan.is_primary
                )
            )
            .values(is_primary=False)
        )
        await self.db.execute(stmt)

    async def _set_primary(self, user_id: UUID, plan_id: UUID) -> None:
        """设置指定计划为主计划"""
        stmt = (
            update(Plan)
            .where(
                and_(
                    Plan.id == plan_id,
                    Plan.user_id == user_id
                )
            )
            .values(is_primary=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def _select_best_primary_plan(self, user_id: UUID) -> Plan | None:
        """
        选择最佳主计划

        优先级排序:
        1. priority (CRITICAL > HIGH > NORMAL > LOW)
        2. target_date (最近的优先)
        3. created_at (最新的优先)
        """
        from sqlalchemy import case, nullslast

        # 优先级权重映射
        priority_order = case(
            (Plan.priority == PlanPriority.CRITICAL, 1),
            (Plan.priority == PlanPriority.HIGH, 2),
            (Plan.priority == PlanPriority.NORMAL, 3),
            (Plan.priority == PlanPriority.LOW, 4),
            else_=5
        )

        query = (
            select(Plan)
            .where(
                and_(
                    Plan.user_id == user_id,
                    Plan.is_active
                )
            )
            .order_by(
                priority_order,           # 优先级高的在前
                nullslast(Plan.target_date),  # 截止日期近的在前，无截止日期的在后
                Plan.created_at.desc()    # 最新创建的在前
            )
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_plans_sorted_by_priority(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> list[Plan]:
        """
        获取按优先级排序的计划列表

        Args:
            user_id: 用户ID
            include_inactive: 是否包含非活跃计划

        Returns:
            排序后的计划列表
        """
        from sqlalchemy import case, nullslast

        priority_order = case(
            (Plan.priority == PlanPriority.CRITICAL, 1),
            (Plan.priority == PlanPriority.HIGH, 2),
            (Plan.priority == PlanPriority.NORMAL, 3),
            (Plan.priority == PlanPriority.LOW, 4),
            else_=5
        )

        conditions = [Plan.user_id == user_id]
        if not include_inactive:
            conditions.append(Plan.is_active)

        query = (
            select(Plan)
            .where(and_(*conditions))
            .order_by(
                Plan.is_primary.desc(),   # 主计划在最前
                priority_order,
                nullslast(Plan.target_date),
                Plan.created_at.desc()
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
