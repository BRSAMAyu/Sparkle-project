from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.aurora.schemas import DistilledStrategyLifecycle
from app.learning.retrieval import RetrievalQueryInput, build_distilled_strategy_refs
from app.learning.seed_bridge import import_seed_library_content
from app.learning.strategy_store import DistilledStrategyStore, StrategyQuery
from app.models.base import Base
from app.models.distilled_strategy_cache import DistilledStrategyCacheEntry  # noqa: F401


async def _store_factory(db_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory


def _strategy():
    return import_seed_library_content()[0]


@pytest.mark.asyncio
async def test_rule_v_restart_loss_regression_strategy_survives_store_reinstantiation(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "distilled_strategy_cache.db"
    engine, session_factory = await _store_factory(db_path)
    try:
        created = _strategy()
        first_store = DistilledStrategyStore(session_factory)
        await first_store.create(created)

        reloaded_store = DistilledStrategyStore(session_factory)
        loaded = await reloaded_store.get(created.id)

        assert loaded.id == created.id
        assert loaded.title == created.title
        assert loaded.status == created.status
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rule_v_restart_loss_regression_transition_state_survives_restart(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "distilled_strategy_transition.db"
    engine, session_factory = await _store_factory(db_path)
    try:
        created = _strategy().model_copy(update={"status": DistilledStrategyLifecycle.DISTILLED})
        first_store = DistilledStrategyStore(session_factory)
        await first_store.create(created)
        await first_store.transition(created.id, DistilledStrategyLifecycle.USER_REVIEWED, user_authorization=True)

        reloaded_store = DistilledStrategyStore(session_factory)
        reviewed = await reloaded_store.get(created.id)
        filtered = await reloaded_store.list(StrategyQuery(statuses=(DistilledStrategyLifecycle.USER_REVIEWED,)))

        assert reviewed.status == DistilledStrategyLifecycle.USER_REVIEWED
        assert reviewed.user_authorization is True
        assert [item.id for item in filtered] == [created.id]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rule_v_restart_loss_regression_retrieval_uses_persisted_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPARKLE_WS7_RETRIEVAL_ENABLED", "true")
    db_path = tmp_path / "distilled_strategy_retrieval.db"
    engine, session_factory = await _store_factory(db_path)
    try:
        strategy = _strategy()
        first_store = DistilledStrategyStore(session_factory)
        await first_store.create(strategy)

        reloaded_store = DistilledStrategyStore(session_factory)
        refs = await build_distilled_strategy_refs(
            RetrievalQueryInput(text="一元二次方程 示例"),
            reloaded_store,
        )

        assert refs == [strategy.id]
    finally:
        await engine.dispose()
