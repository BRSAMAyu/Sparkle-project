from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

import app.services.tool_history_service as tool_history_module
from app.core.event_types import TOOL_HISTORY_RECORDED, TOOL_USAGE_EVENT
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

    publish.assert_awaited_once()
    args, _kwargs = publish.await_args
    assert args[0] == TOOL_HISTORY_RECORDED
    assert args[1]["event_type"] == TOOL_HISTORY_RECORDED
    assert args[1]["user_id"] == str(test_user.id)
    assert args[1]["tool_name"] == "search_knowledge"
    assert args[1]["success"] is True
    assert args[1]["tool_category"] == "research"
    assert args[1]["tool_history_id"] > 0


@pytest.mark.asyncio
async def test_record_context_aware_tool_execution_publishes_tool_usage_event_after_commit(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(tool_history_module.event_bus, "publish", publish)

    service = ToolHistoryService(db_session)
    await service.record_tool_execution(
        user_id=test_user.id,
        tool_name="translator",
        success=True,
        tool_category="translation",
        context_snapshot={
            "source_language": "zh",
            "target_language": "en",
            "text_length": 42,
        },
    )
    await db_session.commit()
    await asyncio.sleep(0)

    assert publish.await_count == 2
    usage_call = publish.await_args_list[1]
    assert usage_call.args[0] == TOOL_USAGE_EVENT
    assert usage_call.args[1]["event_type"] == TOOL_USAGE_EVENT
    assert usage_call.args[1]["tool_name"] == "translator"
    assert usage_call.args[1]["tool_history_id"] > 0


@pytest.mark.asyncio
async def test_recent_context_effects_are_prompt_safe(db_session, test_user) -> None:
    service = ToolHistoryService(db_session)
    await service.record_tool_execution(
        user_id=test_user.id,
        tool_name="translator",
        success=True,
        tool_category="translation",
        context_snapshot={
            "source_language": "zh",
            "target_language": "en",
            "text_length": 18,
        },
        input_args={"text_length": 18},
        output_summary="translation completed; raw text not stored",
    )
    await db_session.commit()

    effects = await service.get_recent_context_effects(test_user.id)

    assert effects[0]["tool_name"] == "translator"
    assert "zh->en" in effects[0]["summary"]
    assert "raw text" not in effects[0]["summary"].lower()
    assert effects[0]["privacy_note"] == "只保存安全摘要，不保存原始内容。"
