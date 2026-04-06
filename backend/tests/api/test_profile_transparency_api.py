from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.api.v1 import profile_transparency as profile_api
from app.api.v1.profile_transparency import router as profile_router
from app.core.cache import cache_service
from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext
from app.core.user_insight_state import InsightSignalEvidence, UserInsightState
from app.db.session import get_db
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionTriggerType,
)
from app.models.chat import ChatMessage
from app.models.chat import ChatSession as ChatSessionModel
from app.models.memory import MemoryCorrection
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.intervention_record_service import InterventionRecordService
from app.services.memory_service import MemoryService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService
from app.services.profile_write_service import ProfileWriteService


@pytest.fixture
def profile_client(db_session):
    app = FastAPI()
    app.include_router(profile_router)

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


def test_override_inferred_rejects_non_adjustable_key(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.post(
        "/profile/override-inferred",
        json={"key": "community_engagement_level", "value": "high"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "key is not adjustable"


def test_reset_override_requires_key(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.post("/profile/reset-override", json={"key": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "key required"


def test_inferred_preferences_returns_behavioral_baseline_for_sparse_user(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.get("/profile/inferred-preferences")

    assert response.status_code == 200
    payload = response.json()
    keys = {item["key"] for item in payload}
    assert "avg_question_complexity" in keys
    assert "community_engagement_level" in keys
    assert "social_learning_preference" in keys


@pytest.mark.asyncio
async def test_preference_rollback_restores_inferred_backup(profile_client, db_session):
    client, state = profile_client
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    state["current_user"] = type("UserStub", (), {"id": user_id})()

    class _RedisStub:
        def __init__(self) -> None:
            self._store: dict[str, dict[str, str]] = {}
            self._ttl: dict[str, int] = {}

        async def hset(self, key: str, field: str, value: str) -> None:
            self._store.setdefault(key, {})[field] = value

        async def hget(self, key: str, field: str) -> str | None:
            return self._store.get(key, {}).get(field)

        async def hgetall(self, key: str) -> dict[str, str]:
            return dict(self._store.get(key, {}))

        async def hdel(self, key: str, field: str) -> None:
            if key in self._store:
                self._store[key].pop(field, None)

        async def expire(self, key: str, ttl: int) -> None:
            self._ttl[key] = ttl

        async def get(self, key: str) -> str | None:
            return None

        async def setex(self, key: str, ttl: int, value: str) -> None:
            self._ttl[key] = ttl

        async def delete(self, *keys: str) -> None:
            return None

    redis = _RedisStub()
    original_redis = cache_service.redis
    cache_service.redis = redis
    profile_api.cache_service.redis = redis

    try:
        pref_service = PreferenceService(db_session, redis=redis)
        await pref_service.update_explicit(user_id, {"community_engagement_level": "low"})
        await pref_service.update_inferred(user_id, {"community_engagement_level": "moderate"})

        service = ProfileWriteService(db_session, redis=redis)
        await service.override_inferred_preference(
            user_id=user_id,
            pref_key="community_engagement_level",
            pref_value={"value": "high"},
            evidence_refs=[{"type": "user_state", "id": "override", "schema_version": "test.v1"}],
            source="override_test",
        )
        memory_service = MemoryService(db_session)
        await memory_service.upsert_preference(
            user_id=user_id,
            pref_key="community_engagement_level",
            pref_value={"value": "low"},
            evidence_refs=[{"type": "user_state", "id": "history-low"}],
            source_type="user_state",
        )
        await memory_service.upsert_preference(
            user_id=user_id,
            pref_key="community_engagement_level",
            pref_value={"value": "high"},
            evidence_refs=[{"type": "user_state", "id": "history-high"}],
            source_type="user_state",
        )

        response = client.post(
            "/profile/preferences/rollback",
            json={"pref_key": "community_engagement_level"},
        )

        assert response.status_code == 200

        prefs = await pref_service.get_preferences(user_id)
        backups = await service.list_inferred_backups(user_id)

        assert prefs.explicit["community_engagement_level"] == "low"
        assert prefs.inferred["community_engagement_level"] == "moderate"
        assert "community_engagement_level" not in backups
    finally:
        cache_service.redis = original_redis
        profile_api.cache_service.redis = original_redis


@pytest.mark.asyncio
async def test_chat_opening_creates_visible_assistant_message(profile_client, db_session):
    client, state = profile_client
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    state["current_user"] = type("UserStub", (), {"id": user_id})()
    record = await InterventionRecordService(db_session).create_record(
        user_id=user_id,
        trigger_type=InterventionTriggerType.CONCEPT_GAP,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
    )
    await db_session.commit()

    drained_updates = [
        {
            "type": "plan_adjusted_from_error",
            "description": "我注意到你最近总在条件句上卡住，所以已经把相关练习提前了。",
            "metadata": {
                "evolution_kind": "adjustment",
                "node_name": "条件句",
                "intervention_id": str(record.id),
            },
        }
    ]

    class _FakeSystemUpdateService:
        def __init__(self, _redis) -> None:
            self.enqueued: list[dict] = []

        async def drain(self, _user_id, limit: int = 20):
            _ = limit
            return list(drained_updates)

        async def enqueue(self, _user_id, payload):
            self.enqueued.append(payload)
            return True

    fake_service = _FakeSystemUpdateService(None)
    original_factory = profile_api.SystemUpdateService
    profile_api.SystemUpdateService = lambda _redis=None: fake_service

    try:
        conversation_id = uuid4()
        response = client.post(
            "/profile/chat-opening",
            json={"conversation_id": str(conversation_id)},
        )
    finally:
        profile_api.SystemUpdateService = original_factory

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert payload["conversation_id"] == str(conversation_id)
    assert "条件句" in payload["content"]

    session = await db_session.get(ChatSessionModel, conversation_id)
    assert session is not None
    message = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.session_id == conversation_id)
        )
    ).scalar_one()
    assert "条件句" in message.content
    assert message.actions[0]["type"] == "next_actions"
    await db_session.refresh(record)
    assert record.acceptance_status == InterventionAcceptanceStatus.SEEN


@pytest.mark.asyncio
async def test_profile_insights_returns_claims_predictions_and_unknowns(profile_client, db_session, monkeypatch):
    client, state = profile_client
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            version=1,
            explicit={},
            inferred={"achievement_motivation_response": "progress_praise"},
        )
    )
    await db_session.commit()
    state["current_user"] = type("UserStub", (), {"id": user_id})()

    async def _fake_profile_context(self, _user_id):
        return ProfileContext(
            preferences={"achievement_motivation_response": "progress_praise"},
            preference_version=1,
            knowledge_summary=KnowledgeSummary(),
            cognitive_summary=CognitiveSummary(),
            user_insight_state=UserInsightState(
                signal_evidence=[
                    InsightSignalEvidence(
                        signal_id="achievement_motivation_response",
                        family="achievement",
                        label="成就激励响应",
                        source="preferences",
                        value="progress_praise",
                        confidence=0.8,
                        freshness="medium",
                    )
                ],
                prediction_summaries={
                    "planning_readiness": {
                        "kind": "guidance",
                        "level": "medium",
                        "confidence": 0.7,
                        "recommended_action": "provisional",
                        "explanation": "Need a little more clarity before a full plan.",
                    }
                },
                calibration_summary={"calibration_posture": "uncalibrated"},
                uncertainty_markers=[{"id": "uncertainty:capacity_hours", "description": "Capacity is still unclear."}],
            ),
        )

    monkeypatch.setattr(ProfileContextService, "get_profile_context", _fake_profile_context)

    response = client.get("/profile/insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["claims"][0]["id"] == "achievement_motivation_response"
    assert payload["predictions"][0]["id"] == "planning_readiness"
    assert payload["unknowns"][0]["id"] == "uncertainty:capacity_hours"


@pytest.mark.asyncio
async def test_profile_insight_control_removes_inferred_signal_and_logs_correction(profile_client, db_session):
    client, state = profile_client
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            version=1,
            explicit={},
            inferred={"achievement_motivation_response": "progress_praise"},
        )
    )
    await db_session.commit()
    state["current_user"] = type("UserStub", (), {"id": user_id})()

    response = client.post(
        "/profile/insights/control",
        json={
            "target_id": "achievement_motivation_response",
            "action": "wrong",
            "reason": "This changed recently",
        },
    )

    assert response.status_code == 200
    prefs = await PreferenceService(db_session, cache_service.redis).get_preferences(user_id)
    assert "achievement_motivation_response" not in (prefs.inferred or {})

    corrections = (
        await db_session.execute(
            select(MemoryCorrection).where(MemoryCorrection.user_id == user_id)
        )
    ).scalars().all()
    assert corrections
    assert corrections[0].action == "wrong"
