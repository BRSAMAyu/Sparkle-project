"""
光子积分服务
Photon Service - 处理光子积分的发放、扣除和余额查询
"""
from __future__ import annotations
from datetime import timezone, datetime
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import and_, case, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.config import settings
from app.core.cache import cache_service
from app.models.shop import PhotonTransactionHistory
from app.models.shop import PhotonTransactionType as DBPhotonTransactionType
from app.models.user import User


def _utcnow() -> datetime:
    """Return naive UTC datetime compatible with existing DB fields."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PhotonTransactionType:
    """光子交易类型"""
    GRANT_ACHIEVEMENT = "grant_achievement"      # 成就奖励
    GRANT_DAILY_FIRST = "grant_daily_first"      # 每日首胜
    GRANT_CONTRACT = "grant_contract"            # 契约完成
    GRANT_BONUS = "grant_bonus"                  # 额外奖励
    DEDUCT_CONTRACT = "deduct_contract_stake"    # 契约失败扣除
    DEDUCT_CONTRACT_STAKE = "deduct_contract_stake"
    DEDUCT_PENALTY = "penalty"                   # 惩罚扣除
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

    def _is_transaction_managed_externally(self) -> bool:
        return bool(self.db.sync_session.info.get("external_transaction_managed"))

    async def _lock_user_balance_row(self, user_id: str) -> User:
        query = (
            select(User)
            .options(lazyload("*"))
            .where(User.id == user_id)
            .with_for_update()
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    async def _find_existing_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: int,
        source: str,
        related_item_id: str | None,
    ) -> PhotonTransactionHistory | None:
        query = (
            select(PhotonTransactionHistory)
            .where(
                PhotonTransactionHistory.user_id == user_id,
                PhotonTransactionHistory.transaction_type == transaction_type,
                PhotonTransactionHistory.amount == amount,
                PhotonTransactionHistory.source == source,
                PhotonTransactionHistory.related_item_id == related_item_id,
            )
            .order_by(desc(PhotonTransactionHistory.created_at))
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _finalize_balance_mutation(
        self,
        user: User,
        *,
        manage_transaction: bool,
    ) -> None:
        if manage_transaction:
            await self.db.commit()
            await self.db.refresh(user)
            return

        await self.db.flush()

    async def _update_balance(
        self,
        user_id: str,
        amount: int,
        delete_cache: bool = True,
        lock_for_update: bool = True,
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
        # 获取用户：强制禁用关系 eager load，避免 FOR UPDATE 与外连接冲突
        query = select(User).options(lazyload("*")).where(User.id == user_id)
        if lock_for_update:
            query = query.with_for_update()
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
        user.updated_at = _utcnow()

        # 先删除缓存，防止脏读（在commit前删除确保一致性）
        if delete_cache:
            cache_key = f"{settings.APP_NAME}:photon:balance:{user_id}"
            await cache_service.delete(cache_key)

        await self.db.flush()  # flush但不commit
        return old_balance, new_balance, user

    async def _deduct_balance_atomically(
        self,
        user_id: str,
        amount: int,
        *,
        allow_negative: bool,
    ) -> tuple[int, int]:
        update_stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                photon_balance=User.photon_balance - amount,
                updated_at=_utcnow(),
            )
        )
        if not allow_negative:
            update_stmt = update_stmt.where(User.photon_balance >= amount)

        result = await self.db.execute(
            update_stmt.returning(User.photon_balance)
        )
        new_balance = result.scalar_one_or_none()

        if new_balance is None:
            existing_balance_result = await self.db.execute(
                select(User.photon_balance).where(User.id == user_id)
            )
            existing_balance = existing_balance_result.scalar_one_or_none()
            if existing_balance is None:
                raise ValueError(f"User {user_id} not found")
            if not allow_negative:
                raise ValueError(
                    f"Insufficient photon balance: {existing_balance} < {amount}"
                )
            raise ValueError(f"Failed to deduct photons for user {user_id}")

        cache_key = f"{settings.APP_NAME}:photon:balance:{user_id}"
        await cache_service.delete(cache_key)

        return int(new_balance) + amount, int(new_balance)

    async def grant_photons(
        self,
        user_id: str,
        amount: int,
        source: str,
        transaction_type: str = PhotonTransactionType.GRANT_ACHIEVEMENT,
        extra_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        related_item_id: str | None = None,
        record_history: bool = False,
        manage_transaction: bool | None = None,
    ) -> dict[str, Any]:
        """
        发放光子积分

        Args:
            user_id: 用户ID
            amount: 积分数量（必须大于0）
            source: 来源说明（如 "achievement:ach_001"）
            transaction_type: 交易类型
            extra_data: 额外元数据

        Returns:
            交易结果，包含新余额
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        transaction_metadata = extra_data if extra_data is not None else metadata
        should_manage_transaction = (
            not self._is_transaction_managed_externally()
            if manage_transaction is None
            else manage_transaction
        )

        locked_user: User | None = None
        if record_history:
            locked_user = await self._lock_user_balance_row(user_id)
            existing_transaction = await self._find_existing_transaction(
                user_id=user_id,
                transaction_type=transaction_type,
                amount=amount,
                source=source,
                related_item_id=related_item_id,
            )
            if existing_transaction is not None:
                logger.info(
                    "Skipped duplicate photon grant for user %s, source=%s, type=%s, related_item_id=%s",
                    user_id,
                    source,
                    transaction_type,
                    related_item_id,
                )
                return {
                    "user_id": user_id,
                    "amount": amount,
                    "old_balance": existing_transaction.balance_before,
                    "new_balance": existing_transaction.balance_after,
                    "source": source,
                    "transaction_type": transaction_type,
                    "timestamp": existing_transaction.created_at or _utcnow(),
                    "extra_data": existing_transaction.extra_data or transaction_metadata,
                    "deduplicated": True,
                }

        # 使用内部方法更新余额（自动删除缓存）
        old_balance, new_balance, user = await self._update_balance(
            user_id,
            amount,
            lock_for_update=locked_user is None,
        )

        if record_history:
            await self.record_transaction(
                user_id=user_id,
                transaction_type=transaction_type,
                amount=amount,
                balance_before=old_balance,
                balance_after=new_balance,
                source=source,
                related_item_id=related_item_id,
                extra_data=transaction_metadata,
            )

        await self._finalize_balance_mutation(
            user,
            manage_transaction=should_manage_transaction,
        )

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
            "timestamp": _utcnow(),
            "extra_data": transaction_metadata,
            "deduplicated": False,
        }

    async def deduct_photons(
        self,
        user_id: str,
        amount: int,
        reason: str,
        transaction_type: str = PhotonTransactionType.DEDUCT_CONTRACT,
        extra_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        related_item_id: str | None = None,
        allow_negative: bool = False,
        record_history: bool = False,
        manage_transaction: bool | None = None,
    ) -> dict[str, Any]:
        """
        扣除光子积分

        Args:
            user_id: 用户ID
            amount: 积分数量（必须大于0）
            reason: 扣除原因
            transaction_type: 交易类型
            extra_data: 额外元数据
            allow_negative: 是否允许负余额（默认不允许）

        Returns:
            交易结果，包含新余额
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        transaction_metadata = extra_data if extra_data is not None else metadata
        should_manage_transaction = (
            not self._is_transaction_managed_externally()
            if manage_transaction is None
            else manage_transaction
        )

        old_balance, new_balance = await self._deduct_balance_atomically(
            user_id=user_id,
            amount=amount,
            allow_negative=allow_negative,
        )

        if record_history:
            await self.record_transaction(
                user_id=user_id,
                transaction_type=transaction_type,
                amount=-amount,
                balance_before=old_balance,
                balance_after=new_balance,
                source=reason,
                related_item_id=related_item_id,
                extra_data=transaction_metadata,
            )

        if should_manage_transaction:
            await self.db.commit()
        else:
            await self.db.flush()

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
            "timestamp": _utcnow(),
            "extra_data": transaction_metadata,
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
    ) -> dict[str, Any]:
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
            owns_transaction = not self.db.in_transaction()
            tx_context = self.db.begin() if owns_transaction else self.db.begin_nested()

            # 在单一事务中执行转账
            async with tx_context:
                locked_users: dict[str, User] = {}
                for lock_user_id in sorted({from_user_id, to_user_id}):
                    locked_users[lock_user_id] = await self._lock_user_balance_row(lock_user_id)

                from_user = locked_users[from_user_id]
                to_user = locked_users[to_user_id]
                old_from = from_user.photon_balance or 0
                old_to = to_user.photon_balance or 0

                if old_from < amount:
                    raise ValueError(
                        f"Insufficient photon balance: {old_from} < {amount}"
                    )

                new_from = old_from - amount
                new_to = old_to + amount
                from_user.photon_balance = new_from
                from_user.updated_at = _utcnow()
                to_user.photon_balance = new_to
                to_user.updated_at = _utcnow()
                await self.db.flush()

                # 记录转出用户交易历史（修复bug：转账未记录交易）
                transfer_out_transaction = await self.record_transaction(
                    user_id=from_user_id,
                    transaction_type="transfer_out",
                    amount=-amount,
                    balance_before=old_from,
                    balance_after=new_from,
                    source=f"Transfer to {to_user_id}",
                    extra_data={"recipient_id": to_user_id, "reason": reason}
                )

                # 记录转入用户交易历史
                await self.record_transaction(
                    user_id=to_user_id,
                    transaction_type="transfer_in",
                    amount=amount,
                    balance_before=old_to,
                    balance_after=new_to,
                    source=f"Transfer from {from_user_id}",
                    extra_data={"sender_id": from_user_id, "reason": reason}
                )

            cache_key_from = f"{settings.APP_NAME}:photon:balance:{from_user_id}"
            cache_key_to = f"{settings.APP_NAME}:photon:balance:{to_user_id}"
            await cache_service.delete(cache_key_from)
            await cache_service.delete(cache_key_to)

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
                "reason": reason,
                "transfer_id": str(transfer_out_transaction.id),
            }
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            raise

    async def record_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        source: str | None = None,
        related_item_id: str | None = None,
        extra_data: dict[str, Any] | None = None
    ) -> PhotonTransactionHistory:
        """
        记录光子交易历史

        Args:
            user_id: 用户ID
            transaction_type: 交易类型
            amount: 变动数量
            balance_before: 交易前余额
            balance_after: 交易后余额
            source: 来源描述
            related_item_id: 相关物品ID
            extra_data: 额外元数据

        Returns:
            交易历史记录
        """
        # 映射交易类型字符串到枚举
        try:
            db_transaction_type = DBPhotonTransactionType(transaction_type)
        except ValueError:
            # 如果不在枚举中，使用默认值
            logger.warning(f"Unknown transaction type: {transaction_type}, using admin_adjustment")
            db_transaction_type = DBPhotonTransactionType.ADMIN_ADJUSTMENT

        transaction = PhotonTransactionHistory(
            id=str(uuid4()),
            user_id=user_id,
            transaction_type=db_transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            related_item_id=related_item_id,
            extra_data=extra_data
        )

        self.db.add(transaction)
        await self.db.flush()

        return transaction

    async def get_transaction_history(
        self,
        user_id: str,
        transaction_type: str | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> dict[str, Any]:
        """
        查询用户交易历史

        Args:
            user_id: 用户ID
            transaction_type: 可选的交易类型筛选
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            交易历史列表和分页信息
        """
        # 构建查询

        query = select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == user_id
        )

        if transaction_type:
            try:
                db_transaction_type = DBPhotonTransactionType(transaction_type)
                query = query.where(PhotonTransactionHistory.transaction_type == db_transaction_type)
            except ValueError:
                logger.warning(f"Unknown transaction type filter: {transaction_type}")

        # 按时间倒序
        query = query.order_by(desc(PhotonTransactionHistory.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        transactions = result.scalars().all()

        # 查询总数
        count_query = select(func.count(PhotonTransactionHistory.id)).where(
            PhotonTransactionHistory.user_id == user_id
        )
        if transaction_type:
            try:
                db_transaction_type = DBPhotonTransactionType(transaction_type)
                count_query = count_query.where(
                    PhotonTransactionHistory.transaction_type == db_transaction_type
                )
            except ValueError:
                pass

        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar_one()

        # 转换为字典列表
        transactions_data = []
        for t in transactions:
            transactions_data.append({
                "id": str(t.id),
                "transaction_type": t.transaction_type,
                "amount": t.amount,
                "balance_before": t.balance_before,
                "balance_after": t.balance_after,
                "source": t.source,
                "related_item_id": t.related_item_id,
                "extra_data": t.extra_data,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })

        return {
            "transactions": transactions_data,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    async def get_transaction_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> dict[str, Any]:
        """
        获取交易汇总统计

        Args:
            user_id: 用户ID
            days: 统计最近多少天

        Returns:
            汇总统计数据
        """
        from datetime import timedelta

        since_date = _utcnow() - timedelta(days=days)

        base_filter = and_(
            PhotonTransactionHistory.user_id == user_id,
            PhotonTransactionHistory.created_at >= since_date
        )
        summary_query = select(
            func.coalesce(
                func.sum(case((PhotonTransactionHistory.amount > 0, PhotonTransactionHistory.amount), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((PhotonTransactionHistory.amount < 0, -PhotonTransactionHistory.amount), else_=0)),
                0,
            ),
            func.count(PhotonTransactionHistory.id),
        ).where(base_filter)
        summary_result = await self.db.execute(summary_query)
        total_income, total_expense, transaction_count = summary_result.one()

        by_type_query = (
            select(
                PhotonTransactionHistory.transaction_type,
                func.coalesce(func.sum(PhotonTransactionHistory.amount), 0),
            )
            .where(base_filter)
            .group_by(PhotonTransactionHistory.transaction_type)
        )
        by_type_result = await self.db.execute(by_type_query)

        by_type = {}
        for transaction_type, amount in by_type_result.all():
            type_key = transaction_type.value if hasattr(transaction_type, "value") else str(transaction_type)
            by_type[type_key] = int(amount or 0)

        net_change = int(total_income or 0) - int(total_expense or 0)

        return {
            "total_income": int(total_income or 0),
            "total_expense": int(total_expense or 0),
            "net_change": net_change,
            "transaction_count": int(transaction_count or 0),
            "by_type": by_type,
            "period_days": days
        }


# 全局单例获取函数（需要在有 db session 的情况下使用）
def get_photon_service(db: AsyncSession) -> PhotonService:
    """
    获取光子积分服务实例

    Args:
        db: 数据库会话

    Returns:
        PhotonService 实例
    """
    return PhotonService(db)
