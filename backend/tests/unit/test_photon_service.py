"""
光子积分服务测试

测试 PhotonService 的核心功能：
- 发放光子
- 扣除光子
- 查询余额
- 余额不足检查
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
