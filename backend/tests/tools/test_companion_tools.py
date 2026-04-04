from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.orchestration.dynamic_tool_registry import DynamicToolRegistry
from app.tools.base import TOOL_RUNTIME_CONTEXT_KEY
from app.tools.companion_tools import (
    AdjustCompanionStateParams,
    AdjustCompanionStateTool,
    GetCompanionStateParams,
    GetCompanionStateTool,
    WriteRelationshipNoteParams,
    WriteRelationshipNoteTool,
)


class _DbSessionStub:
    def __init__(self, runtime_context: dict | None = None) -> None:
        self.sync_session = SimpleNamespace(info={TOOL_RUNTIME_CONTEXT_KEY: runtime_context or {}})


@pytest.mark.asyncio
async def test_companion_tools_register_in_dynamic_registry():
    registry = DynamicToolRegistry()
    registry.register_from_module("app.tools.companion_tools")

    assert registry.get_tool("get_companion_state") is not None
    assert registry.get_tool("adjust_companion_state") is not None
    assert registry.get_tool("write_companion_growth_note") is not None
    assert registry.get_tool("write_relationship_note") is not None
    assert registry.get_tool("get_self_revision_history") is not None


@pytest.mark.asyncio
async def test_adjust_companion_state_rejects_invalid_field():
    tool = AdjustCompanionStateTool()
    result = await tool.execute(
        AdjustCompanionStateParams(
            field="identity_kernel",
            value="rewritten",
            reason="Not allowed",
            evidence={"source": "conversation", "snippet": "nope", "measurable_effect": False},
            confidence=0.9,
        ),
        user_id="00000000-0000-0000-0000-000000000000",
        db_session=_DbSessionStub({"session_id": "session-1"}),
    )

    assert result.success is False
    assert result.error_type == "invalid_field"


@pytest.mark.asyncio
async def test_get_companion_state_uses_runtime_context_defaults(monkeypatch):
    fake_service = SimpleNamespace(
        get_effective_state=AsyncMock(return_value={"candor_calibration": 0.7}),
        get_relationship_profile=AsyncMock(return_value={"trust_level": 0.5}),
        get_self_revision_history=AsyncMock(return_value=[{"field": "candor_calibration"}]),
    )
    monkeypatch.setattr("app.tools.companion_tools.CompanionStateService", lambda *args, **kwargs: fake_service)

    tool = GetCompanionStateTool()
    result = await tool.execute(
        GetCompanionStateParams(),
        user_id="00000000-0000-0000-0000-000000000000",
        db_session=_DbSessionStub({"session_id": "session-ctx", "plan_id": "00000000-0000-0000-0000-000000000001"}),
    )

    assert result.success is True
    assert result.data["effective_companion_state"]["candor_calibration"] == 0.7
    fake_service.get_effective_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_write_relationship_note_tool_returns_promotion_payload(monkeypatch):
    fake_service = SimpleNamespace(
        write_relationship_note=AsyncMock(
            return_value={
                "updated": True,
                "promotions": [{"layer": "profile"}],
            }
        )
    )
    monkeypatch.setattr("app.tools.companion_tools.CompanionStateService", lambda *args, **kwargs: fake_service)

    tool = WriteRelationshipNoteTool()
    result = await tool.execute(
        WriteRelationshipNoteParams(
            note="User trusts directness when it stays warm.",
            note_kind="boundary",
            reason="Repeated chats showed this clearly.",
            evidence={"source": "conversation", "snippet": "直接说但别冷", "measurable_effect": True},
            confidence=0.84,
        ),
        user_id="00000000-0000-0000-0000-000000000000",
        db_session=_DbSessionStub({"session_id": "session-1"}),
    )

    assert result.success is True
    assert result.data["promotions"][0]["layer"] == "profile"


@pytest.mark.asyncio
async def test_get_companion_state_tolerates_non_uuid_plan_id(monkeypatch):
    fake_service = SimpleNamespace(
        get_effective_state=AsyncMock(return_value={"warmth_calibration": 0.5}),
        get_relationship_profile=AsyncMock(return_value={}),
        get_self_revision_history=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr("app.tools.companion_tools.CompanionStateService", lambda *args, **kwargs: fake_service)

    tool = GetCompanionStateTool()
    result = await tool.execute(
        GetCompanionStateParams(),
        user_id="00000000-0000-0000-0000-000000000000",
        db_session=_DbSessionStub({"session_id": "session-ctx", "plan_id": "plan-deadbeef"}),
    )

    assert result.success is True
    _, kwargs = fake_service.get_effective_state.await_args
    assert kwargs["plan_id"] is None
