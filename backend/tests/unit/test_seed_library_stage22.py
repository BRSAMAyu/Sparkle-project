from __future__ import annotations

import uuid

import pytest

from app.models.seed_content import LibraryCategory, LibraryVisibility, SeedLibrary
from app.models.user import User
from app.schemas.seed_content import SubscriptionCreate, SubscriptionUpdate
from app.services.seed_library_service import SeedLibraryService


@pytest.mark.asyncio
async def test_seed_subscription_uses_subscription_id_as_adoption_anchor(db_session) -> None:
    user = User(
        username="seed_stage22_user",
        email="seed_stage22_user@example.com",
        hashed_password="hashed",
    )
    library = SeedLibrary(
        id=uuid.uuid4(),
        name="Stage22 官方库",
        category=LibraryCategory.FEW_SHOT.value,
        visibility=LibraryVisibility.OFFICIAL.value,
        language="zh",
        is_official=True,
    )
    db_session.add_all([user, library])
    await db_session.commit()

    service = SeedLibraryService()
    subscription = await service.subscribe(
        db_session,
        library.id,
        user.id,
        SubscriptionCreate(priority=100, notes="applied"),
    )
    await db_session.commit()

    assert subscription is not None
    assert subscription.id is not None
    assert subscription.last_used_at is not None


@pytest.mark.asyncio
async def test_seed_not_suitable_feedback_reduces_quality_and_disables_subscription(db_session) -> None:
    user = User(
        username="seed_feedback_user",
        email="seed_feedback_user@example.com",
        hashed_password="hashed",
    )
    library = SeedLibrary(
        id=uuid.uuid4(),
        name="反馈测试库",
        category=LibraryCategory.FEW_SHOT.value,
        visibility=LibraryVisibility.OFFICIAL.value,
        language="zh",
        is_official=True,
        quality_score=7.2,
    )
    db_session.add_all([user, library])
    await db_session.commit()

    service = SeedLibraryService()
    await service.subscribe(
        db_session,
        library.id,
        user.id,
        SubscriptionCreate(priority=100, notes="applied"),
    )
    await db_session.commit()

    subscription = await service.update_subscription(
        db_session,
        library.id,
        user.id,
        SubscriptionUpdate(is_enabled=False, notes="not_suitable"),
    )
    await db_session.commit()
    refreshed_library = await service.get_library(db_session, library.id)

    assert subscription is not None
    assert subscription.is_enabled is False
    assert refreshed_library is not None
    assert refreshed_library.quality_score == 6.7
