#!/usr/bin/env python3
"""
商城数据初始化脚本
Initialize Shop Data

用法:
    python scripts/init_shop.py              # 初始化商城数据
    python scripts/init_shop.py --clear      # 清空商城数据（测试用）
    python scripts/init_shop.py --list       # 列出当前商城物品
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.data.shop_seeds import seed_shop_items, clear_shop_items
from app.models.shop import ShopItem
from sqlalchemy import select, func


@click.group()
def cli():
    """商城数据管理工具"""
    pass


@cli.command()
@click.option('--clear-first', is_flag=True, help='先清空现有数据')
def init(clear_first: bool):
    """初始化商城数据"""
    asyncio.run(_init(clear_first))


async def _init(clear_first: bool = False):
    """初始化商城物品"""
    # 创建数据库连接
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # 清空数据（如果需要）
            if clear_first:
                logger.warning("Clearing existing shop items...")
                await clear_shop_items(session)

            # 初始化数据
            await seed_shop_items(session)

            # 统计并显示结果
            count_query = select(func.count(ShopItem.id))
            count_result = await session.execute(count_query)
            total = count_result.scalar_one()

            logger.success(f"✅ Shop initialization complete! Total items: {total}")

            # 按类型统计
            type_query = select(
                ShopItem.item_type,
                func.count(ShopItem.id)
            ).group_by(ShopItem.item_type)

            type_result = await session.execute(type_query)
            logger.info("\n📊 Shop items by type:")
            for item_type, count in type_result:
                logger.info(f"  - {item_type.value}: {count} items")

        except Exception as e:
            logger.error(f"❌ Failed to initialize shop: {e}")
            raise
        finally:
            await engine.dispose()


@cli.command()
def clear():
    """清空商城数据"""
    asyncio.run(_clear())


async def _clear():
    """清空商城物品"""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            await clear_shop_items(session)
            logger.success("✅ All shop items cleared")
        except Exception as e:
            logger.error(f"❌ Failed to clear shop: {e}")
            raise
        finally:
            await engine.dispose()


@cli.command()
@click.option('--type', 'item_type', help='按类型筛选')
@click.option('--min-price', type=int, help='最低价格')
@click.option('--max-price', type=int, help='最高价格')
def list(item_type: str = None, min_price: int = None, max_price: int = None):
    """列出商城物品"""
    asyncio.run(_list(item_type, min_price, max_price))


async def _list(item_type: str = None, min_price: int = None, max_price: int = None):
    """列出商城物品"""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            query = select(ShopItem)

            # 应用筛选
            if item_type:
                query = query.where(ShopItem.item_type == item_type)
            if min_price:
                query = query.where(ShopItem.price_photons >= min_price)
            if max_price:
                query = query.where(ShopItem.price_photons <= max_price)

            query = query.order_by(
                ShopItem.sort_order.desc(),
                ShopItem.price_photons.asc()
            )

            result = await session.execute(query)
            items = result.scalars().all()

            if not items:
                logger.warning("📭 No items found")
                return

            logger.success(f"\n🛒 商城物品列表 (共{len(items)}件):\n")

            for item in items:
                discount_badge = f" [{item.discount_percent}% off]" if item.discount_percent else ""
                limited_badge = " 🏆 限量" if item.is_limited else ""
                stock_info = f" (库存: {item.stock_quantity})" if item.is_limited else ""

                logger.info(
                    f"{item.rarity.value.upper()} | {item.item_type.value} | "
                    f"{item.id}"
                )
                logger.info(
                    f"  名称: {item.name}{discount_badge}{limited_badge}"
                )
                logger.info(
                    f"  价格: {item.price_photons} 光子"
                )
                logger.info(
                    f"  描述: {item.description or 'N/A'}"
                )
                logger.info("")

        except Exception as e:
            logger.error(f"❌ Failed to list items: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    cli()
