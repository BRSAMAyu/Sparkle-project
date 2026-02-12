#!/usr/bin/env python3
"""
简化的商城购买测试
"""
import asyncio
import sys
sys.path.insert(0, '/Users/a/code/sparkle-flutter/backend')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.shop import ShopItem
from app.core.security import get_password_hash
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
            print("❌ 测试用户不存在，请先运行完整测试")
            return

        print(f"✅ 用户: {user.username}")
        print(f"   光子余额: {user.photon_balance}")
        print(f"   装备的皮肤: {user.equipped_skin}")
        print(f"   装备的称号: {user.equipped_title}")

        # 2. 直接查询商城物品（绕过Service层）
        print("\n📦 商城物品:")
        query = select(ShopItem).where(ShopItem.is_available == True).limit(5)
        result = await db.execute(query)
        items = result.scalars().all()

        for item in items:
            print(f"\n   {item.name}")
            print(f"   - ID: {item.id}")
            print(f"   - 类型: {item.item_type.value if hasattr(item.item_type, 'value') else item.item_type}")
            print(f"   - 价格: {item.price_photons} 光子")
            print(f"   - 配置: {item.item_config}")

        # 3. 购买最便宜的皮肤
        skin_item = None
        query = select(ShopItem).where(
            ShopItem.is_available == True,
            ShopItem.item_type == 'skin'  # 使用字符串比较
        ).order_by(ShopItem.price_photons.asc()).limit(1)
        result = await db.execute(query)
        skin_item = result.scalar_one_or_none()

        if skin_item:
            print(f"\n🎨 购买皮肤: {skin_item.name} ({skin_item.price_photons} 光子)")
            shop_service = ShopService(db)

            try:
                purchase_result = await shop_service.purchase_item(
                    user_id=str(user.id),
                    item_id=skin_item.id
                )
                print(f"✅ 购买成功！")
                print(f"   购买ID: {purchase_result['purchase_id']}")
                print(f"   新余额: {purchase_result['balance_after']}")

                # 重新查询用户以获取装备信息
                user_result = await db.execute(select(User).where(User.id == user.id))
                user = user_result.scalar_one()
                print(f"   装备的皮肤: {user.equipped_skin}")

                if user.equipped_skin:
                    print(f"   皮肤配置: {skin_item.item_config}")

            except Exception as e:
                print(f"❌ 购买失败: {e}")

        # 4. 查看购买历史
        print("\n📊 购买历史:")
        photon_service = PhotonService(db)
        transactions = await photon_service.get_transaction_history(
            user_id=str(user.id),
            limit=5
        )

        for tx in transactions['transactions']:
            print(f"   - {tx['transaction_type']}: {tx['amount']} 光子")
            if tx['source']:
                print(f"     来源: {tx['source']}")


if __name__ == "__main__":
    asyncio.run(main())
