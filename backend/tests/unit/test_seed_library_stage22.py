from __future__ import annotations

import uuid

import pytest

from app.models.seed_content import ItemType, LibraryCategory, LibraryVisibility, SeedItem, SeedLibrary
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


@pytest.mark.asyncio
async def test_seed_library_adoption_actions_include_plan_task_and_safe_share(db_session) -> None:
    library = SeedLibrary(
        id=uuid.uuid4(),
        name="函数学习种子",
        category=LibraryCategory.TEACHING_CONTENT.value,
        visibility=LibraryVisibility.OFFICIAL.value,
        language="zh",
        tags=["math", "function"],
        is_official=True,
    )
    exercise = SeedItem(
        id=uuid.uuid4(),
        library_id=library.id,
        item_type=ItemType.EXERCISE.value,
        title="完成一次函数练习",
        content="画出 y = 2x + 1 的图像。",
        subject="math",
        tags=["linear-function"],
        order_index=0,
        is_active=True,
    )
    db_session.add_all([library, exercise])
    await db_session.commit()

    service = SeedLibraryService()
    actions = await service.get_library_adoption_actions(db_session, library)
    action_types = {action["action_type"] for action in actions}

    assert "create_plan" in action_types
    assert "create_task" in action_types
    assert "share_to_community" in action_types
    share_action = next(action for action in actions if action["action_type"] == "share_to_community")
    assert share_action["payload"]["permission"] == "adopt"
    assert share_action["payload"]["safe_share"] is True
