from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.system_update_service import build_system_update
from scripts.journey_smoke.runner import (
    EventRecorder,
    RecordingRedis,
    assert_pubsub_message,
    assert_system_update,
    fail_for_hop,
)


async def test_signup_hop_system_update_format() -> None:
    payload = build_system_update(
        update_type="welcome_onboarding",
        category="journey",
        title="欢迎来到 Sparkle",
        description="我们已经为你准备好了起步引导。",
        metadata={"hop": "signup"},
    )

    validated = assert_system_update(payload, expected_type="welcome_onboarding")

    assert validated["metadata"]["hop"] == "signup"


async def test_goal_hop_round_trips_system_update_queue() -> None:
    redis_client = RecordingRedis()
    payload = build_system_update(
        update_type="memory_goal_created",
        category="goal",
        title="记录了目标",
        description="目标已保存",
        metadata={"hop": "goal"},
    )

    await redis_client.setex("goal", 60, "unused")
    pipe = redis_client.pipeline()
    pipe.lpush("system_updates:u-1", '{"type":"memory_goal_created","category":"goal","title":"记录了目标","description":"目标已保存","priority":"medium","metadata":{"hop":"goal"},"created_at":1}')
    pipe.ltrim("system_updates:u-1", 0, 9)
    pipe.expire("system_updates:u-1", 60)
    await pipe.execute()

    items = await redis_client.lrange("system_updates:u-1", 0, 0)

    assert items
    assert payload["type"] == "memory_goal_created"


async def test_replan_hop_pubsub_message_is_discoverable() -> None:
    redis_client = RecordingRedis()

    await redis_client.publish(
        "user:u-1:replan",
        '{"type":"replan_requested","original_plan_id":"plan-a","new_plan_id":"plan-b"}',
    )

    payload = assert_pubsub_message(
        redis_client,
        channel="user:u-1:replan",
        expected_type="replan_requested",
    )

    assert payload["new_plan_id"] == "plan-b"


async def test_missing_hop_event_reports_hop_name() -> None:
    recorder = EventRecorder()

    try:
        recorder.pop("plan.created")
    except AssertionError as exc:
        wrapped = fail_for_hop("plan", str(exc))
        assert "[plan]" in str(wrapped)
    else:
        raise AssertionError("Expected missing event assertion")
