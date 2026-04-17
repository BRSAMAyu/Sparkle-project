from __future__ import annotations

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
        {"event_type": CAPSULE_FAVORITE_UPDATED, "user_id": "u-favorite"},
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
        "user:profile_context:u-favorite",
        "user:profile_context:u-content",
        "user:profile_context:u-tool",
        "user:profile_context:u-accountability-a",
        "user:profile_context:u-accountability-b",
        "user:profile_context:u-checkin",
    }
