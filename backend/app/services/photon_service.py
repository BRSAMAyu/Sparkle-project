"""
光子积分服务
Photon Service - 处理光子积分的发放、扣除和余额查询
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from app.models.user import User
from app.core.cache import cache_service
from app.config import settings


class PhotonTransactionType:
    """光子交易类型"""
    GRANT_ACHIEVEMENT = "grant_achievement"      # 成就奖励
    GRANT_DAILY_FIRST = "grant_daily_first"      # 每日首胜
    GRANT_CONTRACT = "grant_contract"            # 契约完成
    GRANT_BONUS = "grant_bonus"                  # 额外奖励
    DEDUCT_CONTRACT = "deduct_contract"          # 契约失败扣除
    DEDUCT_PENALTY = "deduct_penalty"            # 惩罚扣除
    REFUND = "refund"                            # 退款


class PhotonService:
    """
    光子积分服务

    功能：
    - 发放光子积分
    - 扣除光子积分
    - 查询用户余额
    - 查询交易历史
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _update_balance(
        self,
        user_id: str,
        amount: int,
        delete_cache: bool = True
    ) -> tuple[int, int, User]:
        """
        内部方法：更新用户光子余额（不提交事务）

        Args:
            user_id: 用户ID
            amount: 变更数量（正数增加，负数减少）
            delete_cache: 是否删除缓存

        Returns:
            (old_balance, new_balance, user)
        """
        # 获取用户
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        old_balance = user.photon_balance or 0
        new_balance = old_balance + amount

        # 防止负余额（除非外部允许）
        if new_balance < 0:
            raise ValueError(
                f"Insufficient photon balance: {old_balance} < {abs(amount)}"
            )

        # 更新余额
        user.photon_balance = new_balance
        user.updated_at = datetime.utcnow()

        # 先删除缓存，防止脏读（在commit前删除确保一致性）
        if delete_cache:
            cache_key = f"{settings.APP_NAME}:photon:balance:{user_id}"
            await cache_service.delete(cache_key)

        await self.db.flush()  # flush但不commit
        return old_balance, new_balance, user

    async def grant_photons(
        self,
        user_id: str,
        amount: int,
        source: str,
        transaction_type: str = PhotonTransactionType.GRANT_ACHIEVEMENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发放光子积分

        Args:
            user_id: 用户ID
            amount: 积分数量（必须大于0）
            source: 来源说明（如 "achievement:ach_001"）
            transaction_type: 交易类型
            metadata: 额外元数据

        Returns:
            交易结果，包含新余额
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        # 使用内部方法更新余额（自动删除缓存）
        old_balance, new_balance, user = await self._update_balance(user_id, amount)

        # 提交事务
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            f"Granted {amount} photons to user {user_id}, "
            f"source={source}, type={transaction_type}, "
            f"old_balance={old_balance}, new_balance={new_balance}"
        )

        return {
            "user_id": user_id,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "source": source,
            "transaction_type": transaction_type,
            "timestamp": datetime.utcnow()
        }

    async def deduct_photons(
        self,
        user_id: str,
        amount: int,
        reason: str,
        transaction_type: str = PhotonTransactionType.DEDUCT_CONTRACT,
        metadata: Optional[Dict[str, Any]] = None,
        allow_negative: bool = False
    ) -> Dict[str, Any]:
        """
        扣除光子积分

        Args:
            user_id: 用户ID
            amount: 积分数量（必须大于0）
            reason: 扣除原因
            transaction_type: 交易类型
            metadata: 额外元数据
            allow_negative: 是否允许负余额（默认不允许）

        Returns:
            交易结果，包含新余额
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        # 先检查余额
        old_balance = await self.get_balance(user_id)
        if not allow_negative and old_balance < amount:
            raise ValueError(
                f"Insufficient photon balance: {old_balance} < {amount}"
            )

        # 使用内部方法更新余额（负数表示扣除，自动删除缓存）
        old_balance, new_balance, user = await self._update_balance(user_id, -amount)

        # 提交事务
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            f"Deducted {amount} photons from user {user_id}, "
            f"reason={reason}, type={transaction_type}, "
            f"old_balance={old_balance}, new_balance={new_balance}"
        )

        return {
            "user_id": user_id,
            "amount": -amount,  # 负数表示扣除
            "old_balance": old_balance,
            "new_balance": new_balance,
            "reason": reason,
            "transaction_type": transaction_type,
            "timestamp": datetime.utcnow()
        }

    async def get_balance(self, user_id: str) -> int:
        """
        查询用户光子余额（带缓存）

        Args:
            user_id: 用户ID

        Returns:
            当前余额
        """
        # 尝试从缓存读取
        cache_key = f"{settings.APP_NAME}:photon:balance:{user_id}"
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return int(cached)

        # 从数据库查询
        query = select(User.photon_balance).where(User.id == user_id)
        result = await self.db.execute(query)
        balance = result.scalar_one_or_none() or 0

        # 写入缓存（5分钟 TTL）
        await cache_service.set(cache_key, balance, ttl=300)

        return balance

    async def has_sufficient(
        self,
        user_id: str,
        amount: int
    ) -> bool:
        """
        检查用户是否有足够的光子积分

        Args:
            user_id: 用户ID
            amount: 需要的积分数量

        Returns:
            是否足够
        """
        balance = await self.get_balance(user_id)
        return balance >= amount

    async def transfer_photons(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        在用户之间转移光子积分

        Args:
            from_user_id: 转出用户ID
            to_user_id: 转入用户ID
            amount: 积分数量
            reason: 转移原因

        Returns:
            交易结果
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer to oneself")

        # 使用数据库事务确保原子性
        try:
            # 先检查转出用户余额
            from_balance = await self.get_balance(from_user_id)
            if from_balance < amount:
                raise ValueError(
                    f"Insufficient photon balance: {from_balance} < {amount}"
                )

            # 在单一事务中执行转账
            async with self.db.begin():
                # 扣除转出用户（使用内部方法，不提交）
                old_from, new_from, _ = await self._update_balance(
                    from_user_id, -amount, delete_cache=False
                )

                # 发放给转入用户（使用内部方法，不提交）
                old_to, new_to, _ = await self._update_balance(
                    to_user_id, amount, delete_cache=False
                )

                # 删除两个用户的缓存
                cache_key_from = f"{settings.APP_NAME}:photon:balance:{from_user_id}"
                cache_key_to = f"{settings.APP_NAME}:photon:balance:{to_user_id}"
                await cache_service.delete(cache_key_from)
                await cache_service.delete(cache_key_to)

            # 事务已自动提交
            logger.info(
                f"Transferred {amount} photons from {from_user_id} to {to_user_id}, "
                f"reason={reason}, from_balance={new_from}, to_balance={new_to}"
            )

            return {
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "amount": amount,
                "from_balance": new_from,
                "to_balance": new_to,
                "reason": reason
            }
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            raise


# 全局单例获取函数（需要在有 db session 的情况下使用）
async def get_photon_service(db: AsyncSession) -> PhotonService:
    """
    获取光子积分服务实例

    Args:
        db: 数据库会话

    Returns:
        PhotonService 实例
    """
    return PhotonService(db)
