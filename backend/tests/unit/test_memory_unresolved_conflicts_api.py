from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.memory import router
from app.config import settings
from app.models.aurora_stage20 import UnresolvedConflict
from app.models.memory import EpisodicMemory
from app.models.user import User

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_memory_unresolved_conflicts_list_and_arbitrate(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    left = EpisodicMemory(
        user_id=user.id,
        summary="准备今晚复习概率论",
        source_type="chat",
        source_id="session-left",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.8,
        evidence_refs=[{"type": "chat_turn", "id": "turn-left"}],
        evidence_token="turn-left",
        semantic_key="commitment:probability",
    )
    right = EpisodicMemory(
        user_id=user.id,
        summary="今晚先刷概率论错题",
        source_type="chat",
        source_id="session-right",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.8,
        evidence_refs=[{"type": "chat_turn", "id": "turn-right"}],
        evidence_token="turn-right",
        semantic_key="commitment:probability",
    )
    db_session.add_all([user, left, right])
    await db_session.commit()

    unresolved = UnresolvedConflict(
        user_id=user.id,
        conflict_key="commitment:probability",
        left_record_id=left.id,
        right_record_id=right.id,
        left_summary=left.summary,
        right_summary=right.summary,
        left_lane=left.source_lane,
        right_lane=right.source_lane,
        left_evidence_token=left.evidence_token,
        right_evidence_token=right.evidence_token,
        left_payload={"record_id": str(left.id)},
        right_payload={"record_id": str(right.id)},
        surfaced_at=datetime(2026, 4, 21, 18, 5, 0),
    )
    db_session.add(unresolved)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_resp = await ac.get("/api/v1/memory/unresolved-conflicts")
        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["items"][0]["left_candidate"]["evidence_token"] == "turn-left"
        assert payload["items"][0]["right_candidate"]["evidence_token"] == "turn-right"

        arbitrate_resp = await ac.post(
            f"/api/v1/memory/unresolved-conflicts/{unresolved.id}/arbitrate",
            json={"selection": "right"},
        )
        assert arbitrate_resp.status_code == 200
        assert arbitrate_resp.json()["selected_side"] == "right"

    await db_session.refresh(left)
    await db_session.refresh(right)
    await db_session.refresh(unresolved)
    assert left.retracted_at is not None
    assert right.retracted_at is None
    assert unresolved.status == "resolved"
    app.dependency_overrides = {}
