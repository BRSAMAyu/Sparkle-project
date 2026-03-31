from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visual_element import VisualElement, VisualElementRarity, VisualElementType, VisualElementUnlockSource
from app.schemas.visual_element import UnlockElementRequest, VisualElementResponse
from app.services.visual_element_service import VisualElementService


@pytest.mark.asyncio
async def test_unlock_element_uses_flush_when_transaction_is_external():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.sync_session.info = {"external_transaction_managed": True}

    service = VisualElementService(db)
    element = VisualElement(
        id="bg_tx",
        name="Tx Background",
        description="tx",
        element_type=VisualElementType.BACKGROUND,
        rarity=VisualElementRarity.RARE,
        unlock_source=VisualElementUnlockSource.ACHIEVEMENT,
        config={},
        is_active=True,
        is_default=False,
        sort_order=1,
    )

    service._get_element_by_id = AsyncMock(return_value=element)
    service._is_element_unlocked = AsyncMock(return_value=False)
    service._build_element_response = MagicMock(
        return_value=VisualElementResponse(
            id=element.id,
            name=element.name,
            description=element.description,
            element_type=element.element_type,
            rarity=element.rarity,
            preview_url=None,
            icon_url=None,
            category=None,
            config={},
            unlock_source=element.unlock_source,
            is_default=False,
            sort_order=element.sort_order,
            is_unlocked=True,
            unlocked_at=None,
            is_equipped=False,
        )
    )

    await service.unlock_element(
        user_id=uuid4(),
        request=UnlockElementRequest(element_id="bg_tx", source="achievement", source_id="achv-1"),
    )

    db.flush.assert_awaited_once()
    db.commit.assert_not_called()
