from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import cache as cache_module
from app.models.base import Base
from app.models.idempotency_key import IdempotencyKey
from app.models.shop import ShopItem, ShopPurchase, UserConsumable
from app.models.user import User
from app.services import photon_service as photon_service_module
from app.services.shop_service import ShopService


async def _cache_get(*_args, **_kwargs):
    return None


async def _cache_set(*_args, **_kwargs):
    return True


async def _cache_delete(*_args, **_kwargs):
    return True


async def _seed_user(session_factory, *, username: str, email: str) -> User:
    async with session_factory() as session:
        user = User(
            username=username,
            email=email,
            hashed_password="hashed",
            photon_balance=500,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _seed_item(session_factory) -> None:
    async with session_factory() as session:
        item = ShopItem(
            id="shop_boost_stage39",
            name="Stage39 Boost",
            description="Boost for idempotency tests",
            item_type="consumable",
            category="boost",
            price_photons=100,
            rarity="common",
            is_available=True,
            is_limited=False,
            stock_quantity=10,
            sort_order=1,
            item_config={"effect_type": "exp_boost"},
        )
        session.add(item)
        await session.commit()


@pytest.mark.asyncio
async def test_same_idempotency_key_concurrent_purchase_replays_single_order(tmp_path, monkeypatch):
    monkeypatch.setattr(photon_service_module.cache_service, "get", _cache_get)
    monkeypatch.setattr(photon_service_module.cache_service, "set", _cache_set)
    monkeypatch.setattr(photon_service_module.cache_service, "delete", _cache_delete)
    monkeypatch.setattr(cache_module.cache_service, "delete", _cache_delete)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'shop_idempotency.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user = await _seed_user(
        session_factory,
        username="shop_idem_user",
        email="shop_idem_user@example.com",
    )
    await _seed_item(session_factory)

    async def worker() -> dict:
        async with session_factory() as session:
            return await ShopService(session).purchase_item(
                user_id=str(user.id),
                item_id="shop_boost_stage39",
                idempotency_key="same-key",
            )

    results = await asyncio.gather(*(worker() for _ in range(10)))

    async with session_factory() as session:
        stored_user = await session.execute(select(User).where(User.id == user.id))
        purchases = await session.execute(select(ShopPurchase).where(ShopPurchase.user_id == user.id))
        consumables = await session.execute(select(UserConsumable).where(UserConsumable.user_id == user.id))
        idempotency_rows = await session.execute(select(IdempotencyKey).where(IdempotencyKey.user_id == user.id))

    purchase_ids = {result["purchase_id"] for result in results}
    replayed_count = sum(1 for result in results if result["replayed"])

    assert len(purchase_ids) == 1
    assert replayed_count == 9
    assert stored_user.scalar_one().photon_balance == 400
    assert len(purchases.scalars().all()) == 1
    assert consumables.scalar_one().quantity == 1
    assert len(idempotency_rows.scalars().all()) == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_same_raw_idempotency_key_is_scoped_per_user(tmp_path, monkeypatch):
    monkeypatch.setattr(photon_service_module.cache_service, "get", _cache_get)
    monkeypatch.setattr(photon_service_module.cache_service, "set", _cache_set)
    monkeypatch.setattr(photon_service_module.cache_service, "delete", _cache_delete)
    monkeypatch.setattr(cache_module.cache_service, "delete", _cache_delete)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'shop_idempotency_scope.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_one = await _seed_user(
        session_factory,
        username="shop_scope_user_one",
        email="shop_scope_user_one@example.com",
    )
    user_two = await _seed_user(
        session_factory,
        username="shop_scope_user_two",
        email="shop_scope_user_two@example.com",
    )
    await _seed_item(session_factory)

    async with session_factory() as session:
        service = ShopService(session)
        first = await service.purchase_item(
            user_id=str(user_one.id),
            item_id="shop_boost_stage39",
            idempotency_key="shared-key",
        )

    async with session_factory() as session:
        service = ShopService(session)
        second = await service.purchase_item(
            user_id=str(user_two.id),
            item_id="shop_boost_stage39",
            idempotency_key="shared-key",
        )

    async with session_factory() as session:
        users = await session.execute(
            select(User).where(User.id.in_([user_one.id, user_two.id]))
        )
        idempotency_rows = await session.execute(select(IdempotencyKey))

    balances = sorted(user.photon_balance for user in users.scalars().all())
    keys = sorted(row.key for row in idempotency_rows.scalars().all())

    assert first["purchase_id"] != second["purchase_id"]
    assert balances == [400, 400]
    assert len(keys) == 2
    assert keys[0] != keys[1]

    await engine.dispose()
