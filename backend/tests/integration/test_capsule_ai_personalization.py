from __future__ import annotations

import pytest

from app.core.context_manager import ContextOrchestrator
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.orchestration.dual_core_router import DualCoreRoutingInput, dual_core_router
from app.orchestration.prompts import build_system_prompt
from app.services.capsule_favorite_service import CapsuleFavoriteService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_event_consumer import ProfileEventConsumer


class _FakeRedis:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    async def delete(self, *keys: str) -> None:
        self.deleted_keys.extend(keys)

    async def get(self, key: str):
        return None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        return None


class _FakeBehaviorSignalCollector:
    def __init__(self, db, redis_client, event_bus):
        self.db = db

    async def handle_capsule_favorite_event(self, event):
        return None


@pytest.mark.asyncio
async def test_favorited_pomodoro_capsule_reaches_prompt_and_router(monkeypatch, db_session, test_user) -> None:
    redis = _FakeRedis()
    published_events: list[tuple[str, dict]] = []

    async def fake_publish(event_type, payload):
        published_events.append((event_type, payload))

    monkeypatch.setattr("app.services.capsule_favorite_service.event_bus.publish", fake_publish)
    monkeypatch.setattr("app.services.profile_event_consumer.BehaviorSignalCollector", _FakeBehaviorSignalCollector)
    monkeypatch.setattr("app.services.profile_event_consumer.invalidate_personalization_cache", lambda _user_id: None)

    class _SessionLocal:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.services.profile_event_consumer.AsyncSessionLocal", _SessionLocal())

    capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="番茄钟工作法",
        content="用 25 分钟专注 + 5 分钟休息来降低启动阻力，适合复习和写作。",
        related_subject="time_management",
        depth_level=DepthLevel.MEDIUM,
    )
    db_session.add(capsule)
    await db_session.commit()
    await db_session.refresh(capsule)

    await CapsuleFavoriteService().add_favorite(test_user.id, capsule.id, db_session)
    event = published_events[-1][1]

    await ProfileEventConsumer(event_bus=object(), redis_client=redis).handle_event(event)

    stored = await PreferenceService(db_session, redis).get_preferences(test_user.id)
    assert stored.inferred["capsule_preferences"]["method_preference_summary"] == ["用户偏好番茄钟方法"]

    context_manager = ContextOrchestrator(db_session, redis)
    capsule_preferences = await context_manager._get_capsule_preferences(test_user.id, db_session)
    prompt = build_system_prompt(
        user_context={"capsule_preferences": capsule_preferences},
        conversation_history={"messages": [{"role": "user", "content": "帮我安排今晚复习。"}]},
    )

    assert "用户偏好番茄钟方法" in prompt

    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 2},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            capsule_preferences=capsule_preferences,
        )
    )

    assert decision.routing_debug["capsule_preferences"]["method_preference_summary"] == ["用户偏好番茄钟方法"]
    assert decision.routing_debug["capsule_method_preferences"][0]["key"] == "pomodoro"
