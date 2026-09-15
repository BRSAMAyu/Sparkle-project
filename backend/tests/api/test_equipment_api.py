from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.achievements import router as achievements_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.users import router as users_router
from app.db.session import get_db
from app.models.achievement import GalaxySkin, UserGalaxySkin
from app.models.file_storage import StoredFile  # noqa: F401
from app.models.shop import ItemRarity, ShopItem, ShopItemType, ShopPurchase
from app.models.user import User


@pytest.fixture
def equipment_client(db_session):
    app = FastAPI()
    app.include_router(achievements_router, prefix="/achievements")
    app.include_router(inventory_router, prefix="/inventory")
    app.include_router(users_router, prefix="/users")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_achievement_skins_reads_equipped_state_from_user_source(db_session, equipment_client):
    client, state = equipment_client
    user = User(
        username="achievement_skin_reader",
        email="achievement_skin_reader@example.com",
        hashed_password="hashed",
        equipped_skin="legendary_anniversary",
        equipped_skin_source="achievement",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add_all(
        [
            GalaxySkin(
                id="default",
                name="默认",
                unlock_type="default",
                unlock_requirement={},
                skin_config={},
                rarity="common",
                sort_order=0,
            ),
            GalaxySkin(
                id="legendary_anniversary",
                name="周年传说",
                unlock_type="achievement",
                unlock_requirement={"achievement_id": "streak_365"},
                skin_config={"theme": "anniversary"},
                rarity="legendary",
                sort_order=1,
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
    state["current_user"] = user

    response = client.get("/achievements/skins")

    assert response.status_code == 200
    body = response.json()
    assert body["equipped_skin_id"] == "legendary_anniversary"
    equipped = next(item for item in body["data"] if item["id"] == "legendary_anniversary")
    assert equipped["is_equipped"] is True


@pytest.mark.asyncio
async def test_inventory_equip_updates_user_source_fields(db_session, equipment_client):
    client, state = equipment_client
    user = User(
        username="inventory_equip_user",
        email="inventory_equip_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    item = ShopItem(
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
    db_session.add(item)
    await db_session.flush()
    db_session.add(
        ShopPurchase(
            id=str(uuid4()),
            user_id=user.id,
            item_id=item.id,
            price_paid=100,
            photon_balance_before=200,
            photon_balance_after=100,
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.post("/inventory/equip", json={"item_type": "skin", "item_id": item.id})
    await db_session.refresh(user)

    assert response.status_code == 200
    assert user.equipped_skin == item.id
    assert user.equipped_skin_source == "shop"


@pytest.mark.asyncio
async def test_users_me_returns_equipment_source_fields(db_session, equipment_client):
    client, state = equipment_client
    user = User(
        username="user_profile_sources",
        email="user_profile_sources@example.com",
        hashed_password="hashed",
        equipped_skin="legendary_anniversary",
        equipped_skin_source="achievement",
        equipped_title="title_legend_scholar_001",
        equipped_title_source="shop",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    response = client.get("/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["equipped_skin_source"] == "achievement"
    assert body["equipped_title_source"] == "shop"
