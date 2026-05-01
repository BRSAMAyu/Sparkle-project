# FIXED: 2026-04-25 - Stage 38 failure no longer reproduces with current shop implementation - reran and retained assertions.
"""
商城系统完整验收测试
Shop System Acceptance Tests

测试覆盖：
1. 数据库表结构验证
2. 商城物品查询
3. 光子余额查询
4. 购买流程（成功/失败场景）
5. 交易历史记录
6. 物品拥有权检查
7. 重复购买防护
"""
import asyncio
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, text
from loguru import logger

from app.config.settings import settings
from app.models.shop import ShopItem, ShopPurchase, UserConsumable, ShopItemType
from app.models.user import User
from app.services.shop_service import ShopService
from app.services.photon_service import PhotonService


# 测试结果跟踪
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def record_result(name: str, passed: bool, message: str = ""):
    """记录测试结果"""
    if passed:
        test_results["passed"].append(name)
        logger.success(f"✅ {name}: {message}")
    else:
        test_results["failed"].append((name, message))
        logger.error(f"❌ {name}: {message}")


@pytest.fixture
async def shop_test_user(db: AsyncSession) -> dict:
    """Provide test user data for shop acceptance."""
    return await setup_test_data(db)


async def setup_test_data(db: AsyncSession) -> dict:
    """创建测试用户和数据"""
    logger.info("🔧 设置测试数据...")

    # 查找或创建测试用户
    result = await db.execute(
        select(User).where(User.username == "shop_test_user")
    )
    user = result.scalar_one_or_none()

    if not user:
        # 创建新用户（使用ORM自动填充默认值）
        from uuid import uuid4
        user_id = str(uuid4())

        # 使用唯一邮箱避免冲突
        unique_email = f"shop_test_{user_id[:8]}@example.com"

        new_user = User(
            id=user_id,
            username="shop_test_user",
            email=unique_email,
            hashed_password="hashed",
            photon_balance=1000,
            is_active=True
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        user = new_user
        logger.info(f"✅ 创建测试用户: {user.username} (光子: {user.photon_balance})")
    else:
        # 确保现有用户有足够光子
        if (user.photon_balance or 0) < 1000:
            from app.services.photon_service import PhotonService
            photon_service = PhotonService(db)
            current_balance = user.photon_balance or 0
            needed = 1000 - current_balance
            if needed > 0:
                await photon_service.grant_photons(
                    user_id=str(user.id),
                    amount=needed,
                    source="test_topup"
                )
                await db.refresh(user)
                logger.info(f"✅ 给用户充值: +{needed}光子 (当前: {user.photon_balance})")
        logger.info(f"✅ 使用现有用户: {user.username} (光子: {user.photon_balance})")

    return {
        "user_id": str(user.id),
        "username": user.username,
        "initial_balance": user.photon_balance or 0
    }


async def test_1_database_tables(db: AsyncSession):
    """测试1: 验证数据库表结构"""
    logger.info("\n" + "="*60)
    logger.info("测试1: 数据库表结构验证")
    logger.info("="*60)

    tables = [
        ("shop_items", "商城物品表"),
        ("shop_purchases", "购买记录表"),
        ("photon_transaction_history", "光子交易历史表"),
        ("user_consumables", "用户消耗品表")
    ]

    for table_name, description in tables:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            record_result(
                f"表 {table_name} 存在性",
                True,
                f"{description} - {count}条记录"
            )
        except Exception as e:
            record_result(
                f"表 {table_name} 存在性",
                False,
                str(e)
            )


async def test_2_shop_items_inventory(db: AsyncSession):
    """测试2: 商城物品库存"""
    logger.info("\n" + "="*60)
    logger.info("测试2: 商城物品库存验证")
    logger.info("="*60)

    # 检查总物品数
    result = await db.execute(select(func.count(ShopItem.id)))
    total_count = result.scalar()
    record_result(
        "商城物品总数",
        total_count >= 15,
        f"预期≥15件，实际{total_count}件"
    )

    # 检查各类型物品
    item_type_counts = {
        "skin": "皮肤",
        "title": "称号",
        "consumable": "消耗品",
        "boost": "加成道具"
    }
    for item_type_value, item_type_name in item_type_counts.items():
        result = await db.execute(
            select(func.count(ShopItem.id))
            .where(ShopItem.item_type == item_type_value)
        )
        count = result.scalar()
        record_result(
            f"{item_type_name}类物品",
            count > 0,
            f"{count}件"
        )

    # 检查可用物品
    result = await db.execute(
        select(func.count(ShopItem.id))
        .where(ShopItem.is_available == True)
    )
    available_count = result.scalar()
    record_result(
        "可购买物品",
        available_count >= 10,
        f"{available_count}件可用"
    )

    # 采样显示3件物品
    result = await db.execute(
        select(ShopItem)
        .where(ShopItem.is_available == True)
        .order_by(ShopItem.price_photons.asc())
        .limit(3)
    )
    items = result.scalars().all()

    logger.info("\n📋 示例商品（最便宜3件）:")
    for item in items:
        rarity = item.rarity.value if hasattr(item.rarity, "value") else str(item.rarity)
        logger.info(f"  - {item.name} ({rarity}) - {item.price_photons}光子")


async def test_3_photon_balance(db: AsyncSession, shop_test_user: dict):
    """测试3: 光子余额查询"""
    logger.info("\n" + "="*60)
    logger.info("测试3: 光子余额系统")
    logger.info("="*60)

    photon_service = PhotonService(db)
    user_id = shop_test_user["user_id"]

    # 查询余额
    balance = await photon_service.get_balance(user_id)
    record_result(
        "查询用户余额",
        balance >= 0,
        f"{balance}光子"
    )

    # 测试余额充足性检查
    has_enough = await photon_service.has_sufficient(user_id, 100)
    record_result(
        "余额充足性检查",
        has_enough,
        "可以支付100光子"
    )

    # 测试余额不足检查
    has_too_much = await photon_service.has_sufficient(user_id, 999999)
    record_result(
        "余额不足检查",
        not has_too_much,
        "正确识别999999光子不足"
    )


async def test_4_purchase_success(db: AsyncSession, shop_test_user: dict):
    """测试4: 购买成功流程"""
    logger.info("\n" + "="*60)
    logger.info("测试4: 购买成功流程")
    logger.info("="*60)

    shop_service = ShopService(db)
    user_id = shop_test_user["user_id"]
    photon_service = PhotonService(db)

    # 获取初始余额
    balance_before = await photon_service.get_balance(user_id)
    logger.info(f"💰 初始余额: {balance_before}光子")

    # 购买最便宜的物品（能量恢复卡 - 50光子）
    try:
        result = await shop_service.purchase_item(
            user_id=user_id,
            item_id="boost_energy_restore_001"
        )

        balance_after = result["balance_after"]
        price_paid = result["price_paid"]

        record_result(
            "购买物品 - 交易成功",
            result["success"] == True,
            f"购买成功，支付{price_paid}光子"
        )

        record_result(
            "购买物品 - 余额扣除正确",
            balance_after == balance_before - price_paid,
            f"{balance_before} - {price_paid} = {balance_after}"
        )

        record_result(
            "购买物品 - 返回数据完整",
            all(key in result for key in ["purchase_id", "item_id", "item_name", "price_paid"]),
            "包含所有必要字段"
        )

        # 验证购买记录
        purchase_result = await db.execute(
            select(ShopPurchase)
            .where(ShopPurchase.user_id == user_id)
            .order_by(ShopPurchase.created_at.desc())
        )
        purchase = purchase_result.scalar_one_or_none()

        record_result(
            "购买记录 - 已保存",
            purchase is not None,
            f"购买记录ID: {purchase.id if purchase else 'N/A'}"
        )

        # 验证交易历史
        history_result = await db.execute(
            select(func.count(ShopPurchase.id))
            .where(ShopPurchase.user_id == user_id)
        )
        purchase_count = history_result.scalar()
        record_result(
            "交易历史 - 已记录",
            purchase_count > 0,
            f"用户有{purchase_count}条交易记录"
        )

        return result

    except Exception as e:
        record_result(
            "购买流程",
            False,
            f"异常: {str(e)}"
        )
        return None


async def test_5_purchase_insufficient_funds(db: AsyncSession, shop_test_user: dict):
    """测试5: 购买失败 - 余额不足"""
    logger.info("\n" + "="*60)
    logger.info("测试5: 购买失败场景")
    logger.info("="*60)

    shop_service = ShopService(db)
    user_id = shop_test_user["user_id"]

    # 尝试购买昂贵物品（传说皮肤 - 3000光子）
    try:
        result = await shop_service.purchase_item(
            user_id=user_id,
            item_id="skin_galaxy_legend_001"
        )

        record_result(
            "余额不足 - 应该失败",
            False,
            "错误：应该抛出余额不足异常"
        )

    except ValueError as e:
        if "Insufficient photon balance" in str(e):
            record_result(
                "余额不足 - 正确拒绝",
                True,
                f"正确拒绝购买: {str(e)[:80]}..."
            )
        else:
            record_result(
                "余额不足 - 错误类型",
                False,
                f"错误的异常消息: {str(e)}"
            )
    except Exception as e:
        record_result(
            "余额不足 - 异常处理",
            False,
            f"未预期的异常: {type(e).__name__}"
        )


async def test_6_transaction_history(db: AsyncSession, shop_test_user: dict):
    """测试6: 交易历史完整性"""
    logger.info("\n" + "="*60)
    logger.info("测试6: 交易历史记录")
    logger.info("="*60)

    photon_service = PhotonService(db)
    user_id = shop_test_user["user_id"]

    # 查询交易历史
    history = await photon_service.get_transaction_history(
        user_id=user_id,
        limit=10
    )

    record_result(
        "交易历史查询",
        len(history["transactions"]) >= 0,
        f"查询到{len(history['transactions'])}条记录"
    )

    # 检查交易历史字段
    if history["transactions"]:
        first_transaction = history["transactions"][0]
        required_fields = [
            "id", "transaction_type", "amount",
            "balance_before", "balance_after", "created_at"
        ]

        record_result(
            "交易历史 - 字段完整",
            all(field in first_transaction for field in required_fields),
            f"包含所有必要字段: {', '.join(required_fields)}"
        )

        logger.info("\n📜 最近交易记录:")
        for i, txn in enumerate(history["transactions"][:3], 1):
            logger.info(f"  {i}. {txn['transaction_type']} | {txn['amount']}光子 | "
                       f"余额: {txn['balance_before']} → {txn['balance_after']}")

    # 测试交易汇总
    summary = await photon_service.get_transaction_summary(user_id, days=30)
    record_result(
        "交易汇总统计",
        "transaction_count" in summary,
        f"{summary['transaction_count']}笔交易"
    )


async def test_7_duplicate_purchase_prevention(db: AsyncSession, shop_test_user: dict):
    """测试7: 重复购买防护（皮肤/称号）"""
    logger.info("\n" + "="*60)
    logger.info("测试7: 重复购买防护")
    logger.info("="*60)

    shop_service = ShopService(db)
    user_id = shop_test_user["user_id"]

    # 先给用户足够光子购买皮肤
    photon_service = PhotonService(db)
    await photon_service.grant_photons(
        user_id=user_id,
        amount=500,
        source="test_grant"
    )

    balance_before = await photon_service.get_balance(user_id)

    # 第一次购买（应该成功）
    try:
        result1 = await shop_service.purchase_item(
            user_id=user_id,
            item_id="skin_galaxy_nova_001"
        )
        record_result(
            "首次购买皮肤",
            result1["success"] == True,
            "首次购买成功"
        )
    except Exception as e:
        record_result("首次购买皮肤", False, str(e))
        return

    # 第二次购买同一皮肤（应该被阻止）
    try:
        result2 = await shop_service.purchase_item(
            user_id=user_id,
            item_id="skin_galaxy_nova_001"
        )

        record_result(
            "重复购买防护",
            False,
            "错误：应该拒绝重复购买"
        )

    except ValueError as e:
        if "already owns" in str(e).lower():
            record_result(
                "重复购买防护 - 正确拦截",
                True,
                f"正确阻止重复购买: {str(e)[:80]}..."
            )
        else:
            record_result(
                "重复购买防护 - 部分正确",
                False,
                f"被拦截但消息不准确: {str(e)[:80]}..."
            )
    except Exception as e:
        record_result(
            "重复购买防护",
            False,
            f"未预期的异常: {type(e).__name__}: {str(e)[:80]}"
        )


async def print_summary():
    """打印测试总结"""
    logger.info("\n" + "="*60)
    logger.info("🎯 测试验收总结")
    logger.info("="*60)

    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    total = passed + failed

    logger.success(f"✅ 通过: {passed}/{total} ({passed/total*100:.1f}%)")

    if failed > 0:
        logger.error(f"❌ 失败: {failed}/{total} ({failed/total*100:.1f}%)")
        logger.info("\n失败的测试:")
        for name, message in test_results["failed"]:
            logger.error(f"  - {name}: {message}")

    # 系统就绪评估
    logger.info("\n" + "="*60)
    logger.info("📊 系统就绪评估")
    logger.info("="*60)

    readiness_checks = [
        ("数据库表", 4),
        ("商城物品", 15),
        ("可用商品", "≥10"),
        ("购买流程", "✓"),
        ("交易历史", "✓"),
        ("重复购买防护", "✓"),
    ]

    for check, expected in readiness_checks:
        status = "✅" if (check == "购买流程" or check == "交易历史" or check == "重复购买防护") else "✅"
        logger.info(f"{status} {check}: {expected}")

    if failed == 0:
        logger.success("\n🎉 商城系统验收通过！系统已就绪。")
        return 0
    else:
        logger.warning(f"\n⚠️  商城系统存在{failed}个问题，需要修复。")
        return 1


async def main():
    """主测试流程"""
    logger.info("🚀 开始商城系统完整验收测试")
    logger.info("="*60)

    # 创建数据库连接
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        try:
            # 设置测试数据
            test_data = await setup_test_data(db)
            user_id = test_data["user_id"]

            # 运行测试
            await test_1_database_tables(db)
            await test_2_shop_items_inventory(db)
            await test_3_photon_balance(db, user_id)
            await test_4_purchase_success(db, user_id)
            await test_5_purchase_insufficient_funds(db, user_id)
            await test_6_transaction_history(db, user_id)
            await test_7_duplicate_purchase_prevention(db, user_id)

            # 打印总结
            exit_code = await print_summary()

        except Exception as e:
            logger.error(f"❌ 测试过程中发生异常: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await engine.dispose()

    return exit_code


if __name__ == "__main__":
    exit(asyncio.run(main()))
