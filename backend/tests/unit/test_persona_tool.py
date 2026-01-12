import pytest
from unittest.mock import MagicMock

from app.tools.persona_tools import PersonaTool, PersonaRequest
from app.services.persona_service import PersonaService


@pytest.mark.asyncio
async def test_persona_tool_returns_snapshot(monkeypatch):
    snapshot = {
        "persona_version": "v3.1",
        "audit_token": "token",
        "purpose": "chat_style",
        "tags": ["focused"],
        "capabilities": {"mastery_avg": 75.0},
        "last_update_event_id": "evt-1"
    }

    async def fake_get_snapshot(self, user_id, purpose):
        return snapshot

    monkeypatch.setattr(PersonaService, "get_snapshot", fake_get_snapshot)

    tool = PersonaTool()
    result = await tool.execute(
        PersonaRequest(purpose="chat_style"),
        user_id="00000000-0000-0000-0000-000000000000",
        db_session=MagicMock()
    )

    assert result.success is True
    assert result.data == snapshot
