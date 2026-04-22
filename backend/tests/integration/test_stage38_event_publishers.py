from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AuthorizationError
from app.models.base import Base
from app.models.user import User
from app.schemas.seed_content import (
    LibraryCategoryEnum,
    LibraryCreate,
    LibraryVisibilityEnum,
    SubscriptionCreate,
)
from app.services.seed_library_service import SeedLibraryService
from app.services.shop_service import ShopService
from app.services.theater.prediction_theater_service import PredictionTheaterService


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_library_events_publish_created_and_consumed(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr("app.services.seed_library_service.event_bus_reliable.publish", publish)

    owner = User(
        id=uuid4(),
        username="seed_owner",
        email="seed_owner@example.com",
        hashed_password="hashed",
    )
    db_session.add(owner)
    await db_session.commit()

    service = SeedLibraryService()
    library = await service.create_library(
        db_session,
        LibraryCreate(
            name="Stage38 Seed Library",
            description="seed events",
            category=LibraryCategoryEnum.CUSTOM,
            visibility=LibraryVisibilityEnum.PUBLIC,
            language="zh",
        ),
        owner.id,
    )
    await service.subscribe(
        db_session,
        library.id,
        owner.id,
        SubscriptionCreate(priority=3, notes="applied"),
    )

    assert publish.await_count == 2
    first_payload = publish.await_args_list[0].args[1]
    second_payload = publish.await_args_list[1].args[1]
    assert first_payload["event_type"] == "seed.created"
    assert first_payload["user_id"] == str(owner.id)
    assert second_payload["event_type"] == "seed.consumed"
    assert second_payload["user_id"] == str(owner.id)


class _DummyExecuteResult:
    def __init__(self, scalar_result):
        self._scalar_result = scalar_result

    def scalar_one_or_none(self):
        return self._scalar_result


class _DummyTx:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _DummyDB:
    def __init__(self, item):
        self.item = item
        self.added = []
        self.rolled_back = False

    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _DummyTx()

    async def execute(self, query):
        return _DummyExecuteResult(self.item)

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_shop_purchase_emits_initiated_and_completed_events(monkeypatch: pytest.MonkeyPatch) -> None:
    item = SimpleNamespace(
        id="consumable_boost",
        name="Boost",
        item_type="consumable",
        price_photons=20,
        rarity="common",
        is_limited=False,
        stock_quantity=10,
        item_config={},
    )
    db = _DummyDB(item)
    service = ShopService(db)
    published: list[tuple[str, dict]] = []

    async def record_event(event_type: str, payload: dict[str, str]) -> None:
        published.append((event_type, payload))

    monkeypatch.setattr(service, "_publish_purchase_event", record_event)
    monkeypatch.setattr(service, "_check_item_ownership", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "_grant_item_to_user", AsyncMock())
    monkeypatch.setattr(
        service.photon_service,
        "_update_balance",
        AsyncMock(return_value=(100, 80, None)),
    )
    monkeypatch.setattr(service.photon_service, "record_transaction", AsyncMock())
    monkeypatch.setattr("app.core.cache.cache_service.delete", AsyncMock())

    result = await service.purchase_item(user_id="user-1", item_id=item.id)

    assert result["success"] is True
    assert [event for event, _ in published] == [
        "shop.purchase_initiated",
        "shop.purchase_completed",
    ]
    assert published[0][1]["user_id"] == "user-1"
    assert published[1][1]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_theater_access_denied_publishes_user_scoped_event(monkeypatch: pytest.MonkeyPatch) -> None:
    service = object.__new__(PredictionTheaterService)
    publish = AsyncMock()
    monkeypatch.setattr(
        "app.services.theater.prediction_theater_service.event_bus_reliable.publish",
        publish,
    )

    with pytest.raises(AuthorizationError):
        await service._raise_prediction_access_denied(user_id=uuid4(), prediction_id="pred-1")

    payload = publish.await_args.args[1]
    assert payload["event_type"] == "theater.access_denied"
    assert payload["user_id"] == payload["requester_id"]
