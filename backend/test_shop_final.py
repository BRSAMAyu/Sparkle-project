#!/usr/bin/env python3
"""
测试商城购买 - 简化版
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
    """简化测试"""
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

        print(f"✅ 用户: {user.username}")
        print(f"   光子余额: {user.photon_balance}")
        print(f"   装备的皮肤: {user.equipped_skin}")
        print(f"   装备的称号: {user.equipped_title}")

        # 2. 直接查询商城物品
        print("\n📦 商城物品:")
        query = select(ShopItem).where(ShopItem.is_available == True).limit(5)
        result = await db.execute(query)
        items = result.scalars().all()

        for item in items:
            print(f"\n   {item.name}")
            print(f"   - ID: {item.id}")
            print(f"   - 类型: {item.item_type}")
            print(f"   - 价格: {item.price_photons} 光子")

        # 3. 测试购买皮肤
        if items:
            item = items[0]  # 第一个物品
            print(f"\n🛒 购买: {item.name} ({item.price_photons} 光子)")

            # Save user_id before purchase attempt
            user_id = str(user.id)
            shop_service = ShopService(db)

            try:
                purchase_result = await shop_service.purchase_item(
                    user_id=user_id,
                    item_id=item.id
                )
                print(f"✅ 购买成功！")
                print(f"   购买ID: {purchase_result.get('purchase_id')}")
                print(f"   新余额: {purchase_result.get('balance_after')}")
                print(f"   物品类型: {purchase_result.get('item_type')}")

                # 验证装备状态
                result = await db.execute(select(User).where(User.id == user.id))
                user = result.scalar_one()

                if item.item_type == "skin":
                    print(f"   ✅ 皮肤已装备: {user.equipped_skin}")
                    if user.equipped_skin:
                        # 查询皮肤配置
                        skin_query = select(ShopItem).where(ShopItem.id == user.equipped_skin)
                        skin_result = await db.execute(skin_query)
                        skin = skin_result.scalar_one_or_none()
                        if skin and skin.item_config:
                            print(f"   🎨 皮肤配置: {skin.item_config}")
                elif item.item_type == "title":
                    print(f"   ✅ 称号已装备: {user.equipped_title}")
                    if user.equipped_title:
                        title_query = select(ShopItem).where(ShopItem.id == user.equipped_title)
                        title_result = await db.execute(title_query)
                        title = title_result.scalar_one_or_none()
                        if title and title.item_config:
                            print(f"   🏷️  称号配置: {title.item_config}")

            except Exception as e:
                print(f"❌ 购买失败: {e}")
                import traceback
                traceback.print_exc()

        # 4. 查看交易历史
        print("\n📊 交易历史:")
        photon_service = PhotonService(db)
        transactions = await photon_service.get_transaction_history(
            user_id=user_id,
            limit=5
        )

        for tx in transactions['transactions']:
            print(f"   - {tx['transaction_type']}: {tx['amount']} 光子")
            if tx.get('source'):
                print(f"     来源: {tx['source']}")

        print("\n" + "="*60)
        print("✅ 测试完成！")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
