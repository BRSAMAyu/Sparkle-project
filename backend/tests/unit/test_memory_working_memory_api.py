from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.memory import router
from app.config import settings
from app.models.chat import ChatSession
from app.models.user import User
from app.working_memory.service import WorkingMemoryService

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_working_memory_session_api_round_trip(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)
    user_id = uuid4()
    session_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add_all(
        [
            user,
            ChatSession(
                id=session_id,
                user_id=user_id,
                is_active=True,
                last_message_at=datetime.utcnow(),
            ),
        ]
    )
    await db_session.commit()

    wm = WorkingMemoryService()
    entry = await wm.upsert_entry(
        user_id=str(user_id),
        session_id=str(session_id),
        text="准备周末补完高数真题",
        semantic_key="commitment:math",
        salience_score=0.8,
        subject_type="commitment",
        confidence=0.9,
        evidence_token="turn-1",
        occurred_at=datetime.utcnow(),
        source_turn_id="turn-1",
    )

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/memory/working-memory/session")
        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == str(session_id)
        assert len(payload["items"]) == 1

        marked = await ac.post(f"/api/v1/memory/working-memory/{entry.entry_id}/mark-correct")
        assert marked.status_code == 200
        assert marked.json()["confirmation_status"] == "confirmed"

        deleted = await ac.post(f"/api/v1/memory/working-memory/{entry.entry_id}/forget")
        assert deleted.status_code == 200

    app.dependency_overrides = {}
