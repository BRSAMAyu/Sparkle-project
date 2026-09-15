from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.user import User
from app.services.personalization.preference_service import (
    ConcurrentModificationError,
    PreferenceService,
)


@pytest.mark.asyncio
async def test_update_inferred_occ_detects_stale_version(db_session, test_user):
    service = PreferenceService(db_session)
    await service.get_preferences(test_user.id)

    with pytest.raises(ConcurrentModificationError, match="expected 0"):
        await service._update_inferred_with_occ(
            user_id=test_user.id,
            inferred={"focus_mode": "deep"},
            expected_version=0,
        )


@pytest.mark.asyncio
async def test_update_inferred_retries_after_conflict(db_session, test_user, monkeypatch):
    service = PreferenceService(db_session)
    await service.get_preferences(test_user.id)

    original = service._update_inferred_with_occ
    attempts = 0

    async def flaky_occ(*, user_id, inferred, expected_version):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConcurrentModificationError("synthetic conflict")
        return await original(
            user_id=user_id,
            inferred=inferred,
            expected_version=expected_version,
        )

    monkeypatch.setattr(service, "_update_inferred_with_occ", flaky_occ)

    updated = await service.update_inferred(test_user.id, {"focus_mode": "deep"})

    assert attempts == 2
    assert updated.inferred["focus_mode"] == "deep"


@pytest.mark.asyncio
async def test_concurrent_occ_write_allows_only_one_winner(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'prefs_occ.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            username="pref_occ_user",
            email="pref_occ_user@example.com",
            hashed_password="hashed",
            photon_balance=0,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    async with session_factory() as session:
        await PreferenceService(session).get_preferences(user_id)

    async def worker(value: str):
        async with session_factory() as session:
            service = PreferenceService(session)
            return await service._update_inferred_with_occ(
                user_id=user_id,
                inferred={"focus_mode": value},
                expected_version=1,
            )

    results = await asyncio.gather(worker("deep"), worker("light"), return_exceptions=True)

    success_count = sum(1 for result in results if not isinstance(result, Exception))
    conflict_count = sum(1 for result in results if isinstance(result, ConcurrentModificationError))

    assert success_count == 1
    assert conflict_count == 1

    await engine.dispose()
