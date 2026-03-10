from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.achievement import UserGalaxySkin, UserTitle
from app.models.shop import ItemRarity, ShopItem, ShopItemType, ShopPurchase
from app.models.user import User
from app.services.equipment_service import EquipmentService, EquipmentSource


async def _create_user(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_equip_achievement_skin_updates_user_and_flags(db_session):
    user = await _create_user(db_session, "equip_skin_user")
    db_session.add_all(
        [
            UserGalaxySkin(
                user_id=user.id,
                skin_id="default",
                unlocked_at=datetime.utcnow() - timedelta(days=1),
                unlock_source="achievement",
                is_equipped=True,
            ),
            UserGalaxySkin(
                user_id=user.id,
                skin_id="legendary_anniversary",
                unlocked_at=datetime.utcnow(),
                unlock_source="achievement",
                is_equipped=False,
            ),
        ]
    )
    await db_session.commit()

    result = await EquipmentService(db_session).equip_achievement_skin(str(user.id), "legendary_anniversary")
    await db_session.refresh(user)

    flags = (
        await db_session.execute(
            select(UserGalaxySkin).where(UserGalaxySkin.user_id == user.id).order_by(UserGalaxySkin.skin_id)
        )
    ).scalars().all()

    assert result["equipped_skin_id"] == "legendary_anniversary"
    assert user.equipped_skin == "legendary_anniversary"
    assert user.equipped_skin_source == EquipmentSource.ACHIEVEMENT
    assert {flag.skin_id: flag.is_equipped for flag in flags} == {
        "default": False,
        "legendary_anniversary": True,
    }


@pytest.mark.asyncio
async def test_equip_shop_title_clears_achievement_flags(db_session):
    user = await _create_user(db_session, "equip_shop_title_user")
    db_session.add(
        UserTitle(
            user_id=user.id,
            title_id="night_owl",
            title_name="深夜学者",
            title_display="深夜学者",
            source_achievement_id="night_owl",
            is_equipped=True,
            unlocked_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    shop_title = ShopItem(
        id="title_legend_scholar_001",
        name="传奇学者",
        item_type=ShopItemType.TITLE,
        category="achievement_titles",
        price_photons=100,
        is_available=True,
        is_limited=False,
        rarity=ItemRarity.LEGENDARY,
        sort_order=1,
    )
    db_session.add(shop_title)
    db_session.add(
        ShopPurchase(
            id=str(uuid4()),
            user_id=user.id,
            item_id=shop_title.id,
            price_paid=100,
            photon_balance_before=200,
            photon_balance_after=100,
        )
    )
    await db_session.commit()

    result = await EquipmentService(db_session).equip_shop_title(str(user.id), shop_title.id)
    await db_session.refresh(user)

    title_flags = (
        await db_session.execute(select(UserTitle).where(UserTitle.user_id == user.id))
    ).scalars().all()

    assert result["equipped_title"] == shop_title.id
    assert user.equipped_title == shop_title.id
    assert user.equipped_title_source == EquipmentSource.SHOP
    assert all(flag.is_equipped is False for flag in title_flags)


@pytest.mark.asyncio
async def test_backfill_preserves_shop_equipment_and_falls_back_to_latest_achievement_flag(db_session):
    shop_user = await _create_user(db_session, "backfill_shop_user")
    achievement_user = await _create_user(db_session, "backfill_achievement_user")

    shop_skin = ShopItem(
        id="skin_galaxy_nova_001",
        name="星河·新星",
        item_type=ShopItemType.SKIN,
        category="galaxy_theme",
        price_photons=100,
        is_available=True,
        is_limited=False,
        rarity=ItemRarity.COMMON,
        sort_order=1,
    )
    db_session.add(shop_skin)
    db_session.add(
        ShopPurchase(
            id=str(uuid4()),
            user_id=shop_user.id,
            item_id=shop_skin.id,
            price_paid=100,
            photon_balance_before=200,
            photon_balance_after=100,
        )
    )
    shop_user.equipped_skin = shop_skin.id

    db_session.add_all(
        [
            UserGalaxySkin(
                user_id=shop_user.id,
                skin_id="default",
                unlocked_at=datetime.utcnow() - timedelta(days=3),
                unlock_source="achievement",
                is_equipped=True,
            ),
            UserGalaxySkin(
                user_id=achievement_user.id,
                skin_id="default",
                unlocked_at=datetime.utcnow() - timedelta(days=2),
                unlock_source="achievement",
                is_equipped=True,
            ),
            UserGalaxySkin(
                user_id=achievement_user.id,
                skin_id="legendary_anniversary",
                unlocked_at=datetime.utcnow(),
                unlock_source="achievement",
                is_equipped=True,
            ),
        ]
    )
    await db_session.commit()

    summary = await EquipmentService(db_session).backfill_user_equipment_state()
    await db_session.refresh(shop_user)
    await db_session.refresh(achievement_user)

    achievement_flags = (
        await db_session.execute(
            select(UserGalaxySkin).where(UserGalaxySkin.user_id == achievement_user.id).order_by(UserGalaxySkin.skin_id)
        )
    ).scalars().all()

    assert summary["users_processed"] >= 2
    assert shop_user.equipped_skin == shop_skin.id
    assert shop_user.equipped_skin_source == EquipmentSource.SHOP
    assert achievement_user.equipped_skin == "legendary_anniversary"
    assert achievement_user.equipped_skin_source == EquipmentSource.ACHIEVEMENT
    assert {flag.skin_id: flag.is_equipped for flag in achievement_flags} == {
        "default": False,
        "legendary_anniversary": True,
    }
