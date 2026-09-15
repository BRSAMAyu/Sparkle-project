from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import app.services.capsule_favorite_service as capsule_favorite_module
from app.core.event_types import CAPSULE_FAVORITE_UPDATED
from app.models.curiosity_capsule import CuriosityCapsule
from app.services.capsule_favorite_service import CapsuleFavoriteService


@pytest.mark.asyncio
async def test_add_favorite_publishes_content_refresh_event(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(capsule_favorite_module.event_bus, "publish", publish)

    capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="Capsule",
        content="content",
    )
    db_session.add(capsule)
    await db_session.commit()
    await db_session.refresh(capsule)

    favorite = await CapsuleFavoriteService().add_favorite(
        user_id=test_user.id,
        capsule_id=capsule.id,
        db=db_session,
    )

    assert favorite.capsule_id == capsule.id
    publish.assert_awaited_once_with(
        CAPSULE_FAVORITE_UPDATED,
        {
            "event_type": CAPSULE_FAVORITE_UPDATED,
            "user_id": str(test_user.id),
            "capsule_id": str(capsule.id),
            "action": "favorited",
        },
    )
