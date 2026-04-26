from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.event_types import (
    ACCOUNTABILITY_CHECKIN_CREATED,
    ACCOUNTABILITY_PARTNERSHIP_UPDATED,
    CAPSULE_CONTENT_UPDATED,
    CAPSULE_FAVORITE_UPDATED,
    CAPSULE_FEEDBACK_SUBMITTED,
    CAPSULE_REGENERATE_REQUESTED,
    TOOL_HISTORY_RECORDED,
)
from app.services.profile_event_consumer import ProfileEventConsumer


class _FakeRedis:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    async def delete(self, *keys: str) -> None:
        self.deleted_keys.extend(keys)


@pytest.mark.asyncio
async def test_profile_event_consumer_invalidates_profile_context_for_stage2_signal_family_events() -> None:
    redis = _FakeRedis()
    consumer = ProfileEventConsumer(event_bus=object(), redis_client=redis)

    events = [
        {"event_type": "achievement.unlocked", "user_id": "u-achievement"},
        {"event_type": "calendar.event.updated", "user_id": "u-calendar"},
        {"event_type": CAPSULE_FEEDBACK_SUBMITTED, "user_id": "u-feedback"},
        {"event_type": CAPSULE_REGENERATE_REQUESTED, "user_id": "u-regen"},
        {"event_type": CAPSULE_CONTENT_UPDATED, "user_id": "u-content"},
        {"event_type": TOOL_HISTORY_RECORDED, "user_id": "u-tool"},
        {
            "event_type": ACCOUNTABILITY_PARTNERSHIP_UPDATED,
            "user_ids": ["u-accountability-a", "u-accountability-b"],
        },
        {
            "event_type": ACCOUNTABILITY_CHECKIN_CREATED,
            "user_ids": ["u-checkin"],
        },
    ]

    for event in events:
        await consumer.handle_event(event)

    assert set(redis.deleted_keys) == {
        "user:profile_context:u-achievement",
        "user:profile_context:u-calendar",
        "user:profile_context:u-feedback",
        "user:profile_context:u-regen",
        "user:profile_context:u-content",
        "user:profile_context:u-tool",
        "user:profile_context:u-accountability-a",
        "user:profile_context:u-accountability-b",
        "user:profile_context:u-checkin",
    }


@pytest.mark.asyncio
async def test_profile_event_consumer_writes_capsule_preferences_after_favorite_event(monkeypatch) -> None:
    user_id = uuid4()
    capsule_id = uuid4()
    redis = _FakeRedis()
    handled_events: list[dict] = []
    written_updates: list[dict] = []

    class _FakeSessionLocal:
        def __call__(self):
            return self

        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeBehaviorSignalCollector:
        def __init__(self, db, redis_client, event_bus):
            pass

        async def handle_capsule_favorite_event(self, event):
            handled_events.append(event)

    class _FakeCapsuleFavoriteService:
        async def get_preferences(self, user_uuid, db):
            assert user_uuid == user_id
            return {
                "favorite_count": 3,
                "content_depth_preference": "deep",
                "subject_affinity": ["computer_networks"],
                "recent_notes": ["keep rigorous examples"],
            }

    class _FakeProfileWriteService:
        def __init__(self, db, redis_client):
            pass

        async def update_inferred_preference(self, *, user_id, updates, source):
            written_updates.append({"user_id": user_id, "updates": updates, "source": source})
            return 9

    monkeypatch.setattr("app.services.profile_event_consumer.AsyncSessionLocal", _FakeSessionLocal())
    monkeypatch.setattr("app.services.profile_event_consumer.BehaviorSignalCollector", _FakeBehaviorSignalCollector)
    monkeypatch.setattr("app.services.profile_event_consumer.CapsuleFavoriteService", _FakeCapsuleFavoriteService)
    monkeypatch.setattr("app.services.profile_event_consumer.ProfileWriteService", _FakeProfileWriteService)
    monkeypatch.setattr("app.services.profile_event_consumer.invalidate_personalization_cache", lambda _user_id: None)

    consumer = ProfileEventConsumer(event_bus=object(), redis_client=redis)
    event = {
        "event_type": CAPSULE_FAVORITE_UPDATED,
        "user_id": str(user_id),
        "capsule_id": str(capsule_id),
        "action": "favorited",
    }

    await consumer.handle_event(event)

    assert handled_events == [event]
    assert {
        f"user:context:{user_id}",
        f"user:context:snapshot:{user_id}",
        f"user:profile_context:{user_id}",
    }.issubset(set(redis.deleted_keys))
    assert written_updates == [
        {
            "user_id": user_id,
            "updates": {
                "capsule_preferences": {
                    "favorite_count": 3,
                    "content_depth_preference": "deep",
                    "subject_affinity": ["computer_networks"],
                    "recent_notes": ["keep rigorous examples"],
                },
                "content_depth_preference": "deep",
                "content_subject_affinities": ["computer_networks"],
                "capsule_favorite_count": 3,
            },
            "source": "capsule_favorite",
        }
    ]


@pytest.mark.asyncio
async def test_profile_event_consumer_writes_seed_library_signal(monkeypatch) -> None:
    user_id = uuid4()
    library_id = uuid4()
    redis = _FakeRedis()
    written_updates: list[dict] = []

    class _FakeSession:
        async def get(self, model, primary_key):
            assert str(primary_key) == str(library_id)
            return type(
                "Library",
                (),
                {
                    "name": "DSA Few Shot",
                    "category": "few_shot",
                    "visibility": "official",
                    "language": "zh",
                    "tags": ["ds.quicksort", "ds.heap"],
                },
            )()

    class _FakeSessionLocal:
        def __call__(self):
            return self

        async def __aenter__(self):
            return _FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeProfileWriteService:
        def __init__(self, db, redis_client):
            pass

        async def update_inferred_preference(self, *, user_id, updates, source):
            written_updates.append({"user_id": user_id, "updates": updates, "source": source})
            return 10

    monkeypatch.setattr("app.services.profile_event_consumer.AsyncSessionLocal", _FakeSessionLocal())
    monkeypatch.setattr("app.services.profile_event_consumer.ProfileWriteService", _FakeProfileWriteService)
    monkeypatch.setattr("app.services.profile_event_consumer.invalidate_personalization_cache", lambda _user_id: None)

    consumer = ProfileEventConsumer(event_bus=object(), redis_client=redis)
    await consumer.handle_event(
        {
            "event_type": "seed.consumed",
            "user_id": str(user_id),
            "library_id": str(library_id),
            "priority": 8,
            "timestamp": "2026-04-26T00:00:00",
        }
    )

    assert {
        f"user:context:{user_id}",
        f"user:context:snapshot:{user_id}",
        f"user:profile_context:{user_id}",
    }.issubset(set(redis.deleted_keys))
    assert written_updates == [
        {
            "user_id": user_id,
            "updates": {
                "seed_library_signal": {
                    "last_event": "seed.consumed",
                    "last_library_id": str(library_id),
                    "last_library_name": "DSA Few Shot",
                    "category": "few_shot",
                    "visibility": "official",
                    "language": "zh",
                    "tags": ["ds.quicksort", "ds.heap"],
                    "priority": 8,
                    "timestamp": "2026-04-26T00:00:00",
                },
                "seed_library_affinities": ["ds.quicksort", "ds.heap"],
                "seed_library_category_preference": "few_shot",
                "uses_seed_libraries": True,
            },
            "source": "seed.consumed",
        }
    ]
