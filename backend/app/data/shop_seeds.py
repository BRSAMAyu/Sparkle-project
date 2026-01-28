"""
商城初始数据
Shop Seed Data - 初始商城物品数据

包含：
- 皮肤（Galaxy主题皮肤）
- 称号（成就相关）
- 消耗品（经验加成、光子加成等）
- 加成道具（连击冻结、提示解锁等）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.shop import (
    ShopItem, ShopItemType, ItemRarity
)


async def seed_shop_items(db: AsyncSession) -> None:
    """
    初始化商城物品数据

    如果表为空，则插入初始物品数据
    """
    # 检查是否已有数据
    query = select(ShopItem).limit(1)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("Shop items already seeded, skipping...")
        return

    logger.info("Seeding shop items...")

    shop_items = [
        # ========== 皮肤 (Skins) ==========
        ShopItem(
            id="skin_galaxy_nova_001",
            name="星河·新星",
            description="璀璨新星主题皮肤，让你的知识星系熠熠生辉",
            item_type=ShopItemType.SKIN,
            category="galaxy_theme",
            price_photons=500,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/skins/nova.png",
            rarity=ItemRarity.COMMON,
            item_config={"theme": "nova", "colors": ["#FF6B6B", "#4ECDC4"]},
            sort_order=10
        ),
        ShopItem(
            id="skin_galaxy_nebula_001",
            name="星河·星云",
            description="梦幻星云主题皮肤，探索知识的浩瀚宇宙",
            item_type=ShopItemType.SKIN,
            category="galaxy_theme",
            price_photons=800,
            original_price=1000,
            discount_percent=20,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/skins/nebula.png",
            rarity=ItemRarity.RARE,
            item_config={"theme": "nebula", "colors": ["#A29BFE", "#FD79A8"]},
            sort_order=20
        ),
        ShopItem(
            id="skin_galaxy_cosmic_001",
            name="星河·宇宙",
            description="深邃宇宙主题皮肤，感受时空的无限奥秘",
            item_type=ShopItemType.SKIN,
            category="galaxy_theme",
            price_photons=1500,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/skins/cosmic.png",
            rarity=ItemRarity.EPIC,
            item_config={"theme": "cosmic", "colors": ["#2D3436", "#6C5CE7"]},
            sort_order=30
        ),
        ShopItem(
            id="skin_galaxy_legend_001",
            name="星河·传说",
            description="限定传说皮肤，闪耀知识巅峰的光芒",
            item_type=ShopItemType.SKIN,
            category="galaxy_theme",
            price_photons=3000,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=True,
            stock_quantity=100,
            icon_url="https://assets.sparkle.ai/icons/skins/legend.png",
            rarity=ItemRarity.LEGENDARY,
            item_config={"theme": "legend", "colors": ["#FFD700", "#FFA500"], "special_effects": True},
            sort_order=100
        ),

        # ========== 称号 (Titles) ==========
        ShopItem(
            id="title_learner_001",
            name="知识探索者",
            description="完成首次学习获得",
            item_type=ShopItemType.TITLE,
            category="achievement_titles",
            price_photons=200,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/titles/explorer.png",
            rarity=ItemRarity.COMMON,
            item_config={"text": "🔍 知识探索者", "display_format": "prefix"},
            sort_order=5
        ),
        ShopItem(
            id="title_streak_master_001",
            name="连击大师",
            description="连续学习7天获得",
            item_type=ShopItemType.TITLE,
            category="achievement_titles",
            price_photons=600,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/titles/streak_master.png",
            rarity=ItemRarity.RARE,
            item_config={"text": "🔥 连击大师", "display_format": "suffix"},
            sort_order=15
        ),
        ShopItem(
            id="title_knowledge_keeper_001",
            name="知识守护者",
            description="掌握100个知识点获得",
            item_type=ShopItemType.TITLE,
            category="achievement_titles",
            price_photons=1200,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/titles/keeper.png",
            rarity=ItemRarity.EPIC,
            item_config={"text": "📚 知识守护者", "display_format": "prefix"},
            sort_order=25
        ),
        ShopItem(
            id="title_legend_scholar_001",
            name="传奇学者",
            description="限定称号，知识巅峰的象征",
            item_type=ShopItemType.TITLE,
            category="achievement_titles",
            price_photons=2500,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=True,
            stock_quantity=50,
            icon_url="https://assets.sparkle.ai/icons/titles/legend_scholar.png",
            rarity=ItemRarity.LEGENDARY,
            item_config={"text": "👑 传奇学者", "display_format": "prefix", "special_effect": True},
            sort_order=90
        ),

        # ========== 消耗品 (Consumables) ==========
        ShopItem(
            id="consumable_exp_boost_1x_001",
            name="经验加成卡（小）",
            description="2小时内学习经验+50%",
            item_type=ShopItemType.CONSUMABLE,
            category="exp_boosts",
            price_photons=100,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/consumables/exp_boost_small.png",
            rarity=ItemRarity.COMMON,
            item_config={
                "effect_type": "exp_boost",
                "multiplier": 1.5,
                "duration_hours": 2
            },
            sort_order=1
        ),
        ShopItem(
            id="consumable_exp_boost_2x_001",
            name="经验加成卡（大）",
            description="24小时内学习经验+100%",
            item_type=ShopItemType.CONSUMABLE,
            category="exp_boosts",
            price_photons=400,
            original_price=500,
            discount_percent=20,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/consumables/exp_boost_large.png",
            rarity=ItemRarity.RARE,
            item_config={
                "effect_type": "exp_boost",
                "multiplier": 2.0,
                "duration_hours": 24
            },
            sort_order=2
        ),
        ShopItem(
            id="consumable_photon_boost_001",
            name="光子加成卡",
            description="24小时内光子获取+50%",
            item_type=ShopItemType.CONSUMABLE,
            category="photon_boosts",
            price_photons=300,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/consumables/photon_boost.png",
            rarity=ItemRarity.RARE,
            item_config={
                "effect_type": "photon_boost",
                "multiplier": 1.5,
                "duration_hours": 24
            },
            sort_order=3
        ),

        # ========== 加成道具 (Boosts) ==========
        ShopItem(
            id="boost_streak_freeze_001",
            name="连击冻结卡",
            description="冻结连胜状态1天，不计入断连",
            item_type=ShopItemType.BOOST,
            category="streak_protection",
            price_photons=150,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/boosts/streak_freeze.png",
            rarity=ItemRarity.COMMON,
            item_config={
                "effect_type": "streak_freeze",
                "charges": 1,
                "description": "冻结连胜1天"
            },
            sort_order=4
        ),
        ShopItem(
            id="boost_hint_reveal_001",
            name="提示解锁卡（5次）",
            description="解锁5次额外提示机会",
            item_type=ShopItemType.BOOST,
            category="hint_boosts",
            price_photons=80,
            original_price=100,
            discount_percent=20,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/boosts/hint_reveal.png",
            rarity=ItemRarity.COMMON,
            item_config={
                "effect_type": "hint_reveal",
                "charges": 5,
                "description": "额外提示5次"
            },
            sort_order=6
        ),
        ShopItem(
            id="boost_energy_restore_001",
            name="能量恢复卡",
            description="立即恢复100点能量",
            item_type=ShopItemType.BOOST,
            category="energy_boosts",
            price_photons=50,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/boosts/energy_restore.png",
            rarity=ItemRarity.COMMON,
            item_config={
                "effect_type": "energy_restore",
                "amount": 100,
                "description": "恢复100能量"
            },
            sort_order=7
        ),
        ShopItem(
            id="boost_custom_avatar_001",
            name="自定义头像卡",
            description="解锁自定义头像功能（永久）",
            item_type=ShopItemType.BOOST,
            category="avatar_unlocks",
            price_photons=1000,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://assets.sparkle.ai/icons/boosts/custom_avatar.png",
            rarity=ItemRarity.EPIC,
            item_config={
                "effect_type": "custom_avatar",
                "permanent": True,
                "description": "永久解锁自定义头像"
            },
            sort_order=40
        ),
    ]

    # 批量插入
    for item in shop_items:
        db.add(item)

    await db.commit()

    logger.info(f"Successfully seeded {len(shop_items)} shop items")


async def clear_shop_items(db: AsyncSession) -> None:
    """清空商城物品（仅用于测试）"""
    from sqlalchemy import delete

    await db.execute(delete(ShopItem))
    await db.commit()
    logger.warning("All shop items cleared")
