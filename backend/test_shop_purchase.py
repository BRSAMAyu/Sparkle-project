#!/usr/bin/env python3
"""
测试商城购买流程

完整流程：
1. 创建测试用户
2. 给用户发放光子
3. 浏览商城物品
4. 购买皮肤
5. 验证皮肤装备
6. 购买称号
7. 验证称号装备
8. 购买消耗品
9. 使用消耗品
10. 查看交易历史
"""
import asyncio
import sys
sys.path.insert(0, '/Users/a/code/sparkle-flutter/backend')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.shop import ShopItem, ShopPurchase, UserConsumable
from app.core.security import get_password_hash
from app.services.photon_service import PhotonService
from app.services.shop_service import ShopService
from app.config import settings


async def main():
    """测试购买流程"""
    # 创建数据库连接
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as db:
        # 1. 创建或获取测试用户
        print("\n📝 步骤1: 创建测试用户...")
        user = await _get_or_create_test_user(db)
        print(f"✅ 用户: {user.username} (ID: {user.id})")
        print(f"   当前光子余额: {user.photon_balance}")

        # 2. 发放光子积分
        print("\n💰 步骤2: 发放光子积分...")
        photon_service = PhotonService(db)
        result = await photon_service.grant_photons(
            user_id=str(user.id),
            amount=5000,
            source="test_grant",
            transaction_type="admin_adjustment",
            extra_data={"purpose": "shop_test"}
        )
        print(f"✅ 发放成功！新余额: {result['new_balance']}")

        # 3. 浏览商城物品
        print("\n🛒 步骤3: 浏览商城物品...")
        shop_service = ShopService(db)
        items = await shop_service.get_available_items(user_id=str(user.id))

        print(f"\n📦 可用物品 ({len(items)} 件):")
        skins = [i for i in items if i['item_type'] == 'skin']
        titles = [i for i in items if i['item_type'] == 'title']
        consumables = [i for i in items if i['item_type'] in ['consumable', 'boost']]

        print(f"\n   🎨 皮肤 ({len(skins)} 件):")
        for item in skins[:2]:  # 只显示前2个
            print(f"      - {item['name']}: {item['price_photons']} 光子")
            print(f"        配置: {item['item_config']}")

        print(f"\n   🏷️  称号 ({len(titles)} 件):")
        for item in titles[:2]:
            print(f"      - {item['name']}: {item['price_photons']} 光子")
            print(f"        配置: {item['item_config']}")

        print(f"\n   ⚡ 消耗品 ({len(consumables)} 件):")
        for item in consumables[:2]:
            print(f"      - {item['name']}: {item['price_photons']} 光子")

        # 4. 购买皮肤
        print("\n🎨 步骤4: 购买皮肤...")
        if skins:
            skin_to_buy = skins[0]
            skin_id = skin_to_buy['id']
            print(f"   购买: {skin_to_buy['name']} ({skin_to_buy['price_photons']} 光子)")

            purchase_result = await shop_service.purchase_item(
                user_id=str(user.id),
                item_id=skin_id
            )
            print(f"✅ 购买成功！")
            print(f"   购买ID: {purchase_result['purchase_id']}")
            print(f"   新余额: {purchase_result['balance_after']}")

            # 验证皮肤已装备
            await db.refresh(user)
            print(f"   装备的皮肤: {user.equipped_skin}")
            print(f"   皮肤配置: {skin_to_buy['item_config']}")

        # 5. 购买称号
        print("\n🏷️  步骤5: 购买称号...")
        if titles:
            title_to_buy = titles[0]
            title_id = title_to_buy['id']
            print(f"   购买: {title_to_buy['name']} ({title_to_buy['price_photons']} 光子)")

            purchase_result = await shop_service.purchase_item(
                user_id=str(user.id),
                item_id=title_id
            )
            print(f"✅ 购买成功！")
            print(f"   购买ID: {purchase_result['purchase_id']}")
            print(f"   新余额: {purchase_result['balance_after']}")

            # 验证称号已装备
            await db.refresh(user)
            print(f"   装备的称号: {user.equipped_title}")
            print(f"   称号配置: {title_to_buy['item_config']}")

        # 6. 购买消耗品
        print("\n⚡ 步骤6: 购买消耗品...")
        consumable_to_buy = None
        for item in consumables:
            if item['price_photons'] <= user.photon_balance:
                consumable_to_buy = item
                break

        if consumable_to_buy:
            print(f"   购买: {consumable_to_buy['name']} ({consumable_to_buy['price_photons']} 光子)")

            purchase_result = await shop_service.purchase_item(
                user_id=str(user.id),
                item_id=consumable_to_buy['id']
            )
            print(f"✅ 购买成功！")
            print(f"   新余额: {purchase_result['balance_after']}")

            # 查看用户背包
            print("\n🎒 步骤7: 查看用户背包...")
            inventory = await shop_service.get_user_inventory(str(user.id))

            print(f"\n   皮肤 ({len(inventory['skins'])} 件):")
            for skin in inventory['skins']:
                print(f"      - {skin['name']} {'✓ 装备中' if skin['is_equipped'] else ''}")

            print(f"\n   称号 ({len(inventory['titles'])} 件):")
            for title in inventory['titles']:
                print(f"      - {title['name']} {'✓ 装备中' if title['is_equipped'] else ''}")

            print(f"\n   消耗品 ({len(inventory['consumables'] + inventory['boosts'])} 件):")
            for item in inventory['consumables'] + inventory['boosts']:
                print(f"      - {item['name']}: {item['quantity']} 个")

        # 7. 查看交易历史
        print("\n📊 步骤8: 查看交易历史...")
        transactions = await photon_service.get_transaction_history(
            user_id=str(user.id),
            limit=10
        )

        print(f"\n   最近 {len(transactions['transactions'])} 笔交易:")
        for tx in transactions['transactions'][:5]:
            print(f"      - {tx['transaction_type']}: {tx['amount']} 光子")
            print(f"        余额: {tx['balance_before']} -> {tx['balance_after']}")

        print("\n" + "="*60)
        print("✅ 测试完成！")
        print("="*60)


async def _get_or_create_test_user(db: AsyncSession) -> User:
    """获取或创建测试用户"""
    # 尝试查找现有用户
    query = select(User).where(User.username == "shop_test_user")
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user:
        return user

    # 创建新用户
    user = User(
        username="shop_test_user",
        email="shop_test@example.com",
        hashed_password=get_password_hash("test123"),
        nickname="商城测试用户",
        photon_balance=100,  # 初始余额
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


if __name__ == "__main__":
    asyncio.run(main())
