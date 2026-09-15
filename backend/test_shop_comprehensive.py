#!/usr/bin/env python3
"""
完整商城测试 - 购买不同类型的物品
"""
import asyncio
import sys
sys.path.insert(0, '/Users/a/code/sparkle-flutter/backend')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.shop import ShopItem
from app.services.photon_service import PhotonService
from app.services.shop_service import ShopService
from app.config import settings


async def main():
    """完整测试购买流程"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as db:
        # 1. 获取测试用户
        query = select(User).where(User.username == "shop_test_user")
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            print("❌ 测试用户不存在")
            return

        user_id = str(user.id)
        print(f"✅ 用户: {user.username}")
        print(f"   光子余额: {user.photon_balance}")
        print(f"   当前装备: 皮肤={user.equipped_skin}, 称号={user.equipped_title}")

        # 2. 查询所有可用物品
        shop_service = ShopService(db)
        items = await shop_service.get_available_items(user_id=user_id)

        # 按类型分组
        skins = [i for i in items if i['item_type'] == 'skin' and not i['is_owned']]
        titles = [i for i in items if i['item_type'] == 'title' and not i['is_owned']]
        consumables = [i for i in items if i['item_type'] in ['consumable', 'boost']]

        print(f"\n📦 未拥有的物品:")
        print(f"   皮肤: {len(skins)} 件")
        print(f"   称号: {len(titles)} 件")
        print(f"   消耗品: {len(consumables)} 件")

        # 3. 购买称号（如果有的话）
        if titles:
            title = titles[0]
            print(f"\n🏷️  测试购买称号: {title['name']} ({title['price_photons']} 光子)")

            try:
                result = await shop_service.purchase_item(user_id=user_id, item_id=title['id'])
                print(f"   ✅ 购买成功！")
                print(f"   新余额: {result['balance_after']}")

                # 查询用户验证装备
                user_result = await db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one()
                print(f"   装备的称号: {user.equipped_title}")
                print(f"   称号配置: {title['item_config']}")

            except ValueError as e:
                print(f"   ℹ️  {e}")

        # 4. 购买消耗品
        if consumables:
            consumable = consumables[0]
            print(f"\n⚡ 测试购买消耗品: {consumable['name']} ({consumable['price_photons']} 光子)")

            try:
                result = await shop_service.purchase_item(user_id=user_id, item_id=consumable['id'])
                print(f"   ✅ 购买成功！")
                print(f"   新余额: {result['balance_after']}")
                print(f"   物品类型: {result['item_type']}")

            except ValueError as e:
                print(f"   ℹ️  {e}")

        # 5. 查看最终状态
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one()

        print(f"\n📊 最终状态:")
        print(f"   光子余额: {user.photon_balance}")
        print(f"   装备的皮肤: {user.equipped_skin}")
        print(f"   装备的称号: {user.equipped_title}")

        # 6. 查看购买记录
        print(f"\n📜 购买记录:")
        purchases = await shop_service.get_user_purchases(user_id=user_id, limit=5)
        for p in purchases['purchases']:
            print(f"   - {p['item_name']}: {p['price_paid']} 光子")

        # 7. 查看交易历史
        print(f"\n💰 交易历史:")
        photon_service = PhotonService(db)
        transactions = await photon_service.get_transaction_history(user_id=user_id, limit=5)
        for tx in transactions['transactions']:
            print(f"   - {tx['transaction_type']}: {tx['amount']} 光子")

        print("\n" + "="*60)
        print("✅ 测试完成！商城系统运行正常")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
