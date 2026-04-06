from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

import app.services.tool_history_service as tool_history_module
from app.core.event_types import TOOL_HISTORY_RECORDED
from app.services.tool_history_service import ToolHistoryService


@pytest.mark.asyncio
async def test_record_tool_execution_publishes_refresh_event_after_commit(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(tool_history_module.event_bus, "publish", publish)

    service = ToolHistoryService(db_session)
    await service.record_tool_execution(
        user_id=test_user.id,
        tool_name="search_knowledge",
        success=True,
        tool_category="research",
    )
    await db_session.commit()
    await asyncio.sleep(0)

    publish.assert_awaited_once_with(
        TOOL_HISTORY_RECORDED,
        {
            "event_type": TOOL_HISTORY_RECORDED,
            "user_id": str(test_user.id),
            "tool_name": "search_knowledge",
            "success": True,
            "tool_category": "research",
        },
    )
