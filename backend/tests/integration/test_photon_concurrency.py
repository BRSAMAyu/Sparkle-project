from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.user import User
from app.services import photon_service as photon_service_module
from app.services.photon_service import PhotonService


@pytest.mark.asyncio
async def test_concurrent_deductions_never_make_balance_negative(tmp_path, monkeypatch):
    async def _cache_get(*_args, **_kwargs):
        return None

    async def _cache_set(*_args, **_kwargs):
        return True

    async def _cache_delete(*_args, **_kwargs):
        return True

    monkeypatch.setattr(photon_service_module.cache_service, "get", _cache_get)
    monkeypatch.setattr(photon_service_module.cache_service, "set", _cache_set)
    monkeypatch.setattr(photon_service_module.cache_service, "delete", _cache_delete)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'photon_concurrency.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            username="photon_concurrency",
            email="photon_concurrency@example.com",
            hashed_password="hashed",
            photon_balance=50,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    async def worker() -> bool:
        async with session_factory() as session:
            service = PhotonService(session)
            try:
                await service.deduct_photons(
                    user_id=user_id,
                    amount=1,
                    reason="concurrency-test",
                )
                return True
            except ValueError as exc:
                assert "Insufficient photon balance" in str(exc)
                return False

    results = await asyncio.gather(*(worker() for _ in range(100)))

    async with session_factory() as session:
        stored_user = await session.execute(select(User).where(User.id == user_id))
        final_balance = stored_user.scalar_one().photon_balance

    assert sum(results) == 50
    assert final_balance >= 0
    assert final_balance == 0

    await engine.dispose()
