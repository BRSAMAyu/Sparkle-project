"""
光子积分服务测试

测试 PhotonService 的核心功能：
- 发放光子
- 扣除光子
- 查询余额
- 余额不足检查
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import PhotonTransactionHistory
from app.services.photon_service import PhotonService, PhotonTransactionType
from app.models.user import User


@pytest.mark.asyncio
async def test_grant_photons(db_session: AsyncSession, test_user: User):
    """测试发放光子积分"""
    service = PhotonService(db_session)

    # 初始余额应该为 0
    initial_balance = await service.get_balance(str(test_user.id))
    assert initial_balance == 0

    # 发放 100 光子
    result = await service.grant_photons(
        user_id=str(test_user.id),
        amount=100,
        source="test_reward",
        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT
    )

    assert result["amount"] == 100
    assert result["old_balance"] == 0
    assert result["new_balance"] == 100

    # 验证余额已更新
    new_balance = await service.get_balance(str(test_user.id))
    assert new_balance == 100


@pytest.mark.asyncio
async def test_deduct_photons(db_session: AsyncSession, test_user: User):
    """测试扣除光子积分"""
    service = PhotonService(db_session)

    # 先发放 100 光子
    await service.grant_photons(
        user_id=str(test_user.id),
        amount=100,
        source="initial",
    )

    # 扣除 30 光子
    result = await service.deduct_photons(
        user_id=str(test_user.id),
        amount=30,
        reason="test_purchase"
    )

    assert result["amount"] == -30
    assert result["old_balance"] == 100
    assert result["new_balance"] == 70

    # 验证余额
    balance = await service.get_balance(str(test_user.id))
    assert balance == 70


@pytest.mark.asyncio
async def test_insufficient_balance(db_session: AsyncSession, test_user: User):
    """测试余额不足"""
    service = PhotonService(db_session)

    # 发放 50 光子
    await service.grant_photons(
        user_id=str(test_user.id),
        amount=50,
        source="initial"
    )

    # 尝试扣除 100 光子（应该失败）
    with pytest.raises(ValueError, match="Insufficient photon balance"):
        await service.deduct_photons(
            user_id=str(test_user.id),
            amount=100,
            reason="test"
        )

    # 余额应该保持不变
    balance = await service.get_balance(str(test_user.id))
    assert balance == 50


@pytest.mark.asyncio
async def test_deduct_photons_records_history(db_session: AsyncSession, test_user: User):
    service = PhotonService(db_session)

    await service.grant_photons(
        user_id=str(test_user.id),
        amount=100,
        source="initial",
    )

    result = await service.deduct_photons(
        user_id=str(test_user.id),
        amount=30,
        reason="shop:test",
        record_history=True,
        related_item_id="shop-item-1",
    )

    history_result = await db_session.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == test_user.id,
            PhotonTransactionHistory.related_item_id == "shop-item-1",
        )
    )
    history = history_result.scalar_one()

    assert result["old_balance"] == 100
    assert result["new_balance"] == 70
    assert history.amount == -30
    assert history.balance_before == 100
    assert history.balance_after == 70


@pytest.mark.asyncio
async def test_deduct_photons_skips_commit_when_transaction_managed_externally(
    db_session: AsyncSession,
    test_user: User,
):
    service = PhotonService(db_session)

    await service.grant_photons(
        user_id=str(test_user.id),
        amount=40,
        source="initial",
    )
    db_session.sync_session.info["external_transaction_managed"] = True

    await service.deduct_photons(
        user_id=str(test_user.id),
        amount=15,
        reason="managed",
        record_history=True,
        related_item_id="managed-deduct",
    )

    await db_session.rollback()
    await db_session.refresh(test_user)
    history_result = await db_session.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == test_user.id,
            PhotonTransactionHistory.related_item_id == "managed-deduct",
        )
    )

    assert test_user.photon_balance == 40
    assert history_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_has_sufficient(db_session: AsyncSession, test_user: User):
    """测试余额检查"""
    service = PhotonService(db_session)

    # 发放 50 光子
    await service.grant_photons(
        user_id=str(test_user.id),
        amount=50,
        source="initial"
    )

    # 检查余额
    assert await service.has_sufficient(str(test_user.id), 30) is True
    assert await service.has_sufficient(str(test_user.id), 50) is True
    assert await service.has_sufficient(str(test_user.id), 51) is False


@pytest.mark.asyncio
async def test_cache_invalidation(db_session: AsyncSession, test_user: User):
    """测试缓存失效机制"""
    from app.core.cache import cache_service
    from app.config import settings

    service = PhotonService(db_session)
    cache_key = f"{settings.APP_NAME}:photon:balance:{test_user.id}"

    # 发放光子
    await service.grant_photons(
        user_id=str(test_user.id),
        amount=100,
        source="test"
    )

    # 缓存应该已被删除
    cached = await cache_service.get(cache_key)
    assert cached is None


@pytest.mark.asyncio
async def test_get_balance_with_cache(db_session: AsyncSession, test_user: User):
    """测试余额查询缓存"""
    from app.core.cache import cache_service
    from app.config import settings

    service = PhotonService(db_session)

    # 先设置一些余额
    await service.grant_photons(
        user_id=str(test_user.id),
        amount=100,
        source="initial"
    )

    # 第一次查询（从数据库）
    balance1 = await service.get_balance(str(test_user.id))
    assert balance1 == 100

    # 手动设置缓存
    cache_key = f"{settings.APP_NAME}:photon:balance:{test_user.id}"
    await cache_service.set(cache_key, 200, ttl=300)

    # 第二次查询（应该从缓存读取）
    balance2 = await service.get_balance(str(test_user.id))
    assert balance2 == 200  # 从缓存读取的值


@pytest.mark.asyncio
async def test_grant_photons_is_idempotent_for_achievement_rewards(
    db_session: AsyncSession,
    test_user: User,
):
    service = PhotonService(db_session)

    first = await service.grant_photons(
        user_id=str(test_user.id),
        amount=80,
        source="achievement:achv_repeatable",
        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
        related_item_id="achv_repeatable",
        metadata={"achievement_name": "重复奖励测试"},
        record_history=True,
    )
    second = await service.grant_photons(
        user_id=str(test_user.id),
        amount=80,
        source="achievement:achv_repeatable",
        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
        related_item_id="achv_repeatable",
        metadata={"achievement_name": "重复奖励测试"},
        record_history=True,
    )

    assert first["new_balance"] == 80
    assert second["deduplicated"] is True
    assert await service.get_balance(str(test_user.id)) == 80

    history_result = await db_session.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == test_user.id,
            PhotonTransactionHistory.related_item_id == "achv_repeatable",
        )
    )
    history = history_result.scalars().all()
    assert len(history) == 1


@pytest.mark.asyncio
async def test_grant_photons_skips_commit_when_transaction_managed_externally(
    db_session: AsyncSession,
    test_user: User,
):
    service = PhotonService(db_session)
    db_session.sync_session.info["external_transaction_managed"] = True

    await service.grant_photons(
        user_id=str(test_user.id),
        amount=40,
        source="achievement:managed",
        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
        related_item_id="managed",
        record_history=True,
    )

    await db_session.rollback()
    await db_session.refresh(test_user)
    assert test_user.photon_balance == 0


@pytest.mark.asyncio
async def test_transfer_photons_returns_real_transaction_id_and_updates_balances(
    db_session: AsyncSession,
    test_user: User,
):
    service = PhotonService(db_session)
    other_user = User(
        username="transfer_target",
        email="transfer_target@example.com",
        hashed_password="hashed",
        photon_balance=10,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    await service.grant_photons(
        user_id=str(test_user.id),
        amount=100,
        source="initial",
    )

    result = await service.transfer_photons(
        from_user_id=str(test_user.id),
        to_user_id=str(other_user.id),
        amount=30,
        reason="gift",
    )

    out_txn = await db_session.get(PhotonTransactionHistory, result["transfer_id"])
    assert out_txn is not None
    assert result["from_balance"] == 70
    assert result["to_balance"] == 40
    assert out_txn.user_id == test_user.id
    assert out_txn.amount == -30


@pytest.mark.asyncio
async def test_get_transaction_summary_aggregates_in_sql(
    db_session: AsyncSession,
    test_user: User,
):
    service = PhotonService(db_session)

    await service.grant_photons(
        user_id=str(test_user.id),
        amount=120,
        source="achievement:a1",
        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
        record_history=True,
        related_item_id="achievement-a1",
    )
    await service.deduct_photons(
        user_id=str(test_user.id),
        amount=50,
        reason="shop:test",
        record_history=True,
        related_item_id="shop-item-1",
    )

    summary = await service.get_transaction_summary(str(test_user.id), days=30)

    assert summary["total_income"] == 120
    assert summary["total_expense"] == 50
    assert summary["net_change"] == 70
    assert summary["transaction_count"] == 2
    assert summary["by_type"][PhotonTransactionType.GRANT_ACHIEVEMENT] == 120
