from __future__ import annotations

import json
from unittest.mock import AsyncMock

from app.services.jpush_sender_service import JPushPayload, JPushSenderService


def test_jpush_payload_extras_include_goal_context_and_suggested_action() -> None:
    service = JPushSenderService(AsyncMock())
    payload = JPushPayload(
        title="继续推进 TCP 复习",
        body="你上次卡在三次握手，先做 5 分钟对比练习。",
        goal_context={"goal_id": "goal_1", "task_id": "task_1", "deadline_pressure": "medium"},
        suggested_action={"type": "open_task", "task_id": "task_1", "estimated_minutes": 5},
        deep_link="sparkle://task/task_1",
        notification_type="recall",
    )

    extras = service._prepare_extras(payload)

    assert json.loads(extras["goal_context"]) == {
        "goal_id": "goal_1",
        "task_id": "task_1",
        "deadline_pressure": "medium",
    }
    assert json.loads(extras["suggested_action"]) == {
        "type": "open_task",
        "task_id": "task_1",
        "estimated_minutes": 5,
    }
    assert extras["deep_link"] == "sparkle://task/task_1"
    assert extras["notification_type"] == "recall"
    assert "sent_at" in extras


def test_jpush_request_body_has_behavior_context_in_notification_and_message() -> None:
    service = JPushSenderService(AsyncMock())
    payload = JPushPayload(
        title="Sparkle 提醒",
        body="这里有一个低成本下一步。",
        goal_context={"goal_id": "goal_1"},
        suggested_action="start_next_step",
        notification_type="recall",
    )

    body = service._build_request_body(payload=payload, registration_ids=["rid_1"])

    android_extras = body["notification"]["android"]["extras"]
    ios_extras = body["notification"]["ios"]["extras"]
    message_extras = body["message"]["extras"]
    assert body["audience"]["registration_id"] == ["rid_1"]
    assert json.loads(android_extras["goal_context"]) == {"goal_id": "goal_1"}
    assert android_extras["suggested_action"] == "start_next_step"
    assert ios_extras["goal_context"] == android_extras["goal_context"]
    assert message_extras["suggested_action"] == "start_next_step"
