from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.learning_event_service import LearningEventService, _MEM_EVENT_DEDUP, _MEM_EVENTS


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_learning_event_emit_and_query(monkeypatch):
    monkeypatch.setattr("app.services.learning_event_service.settings.ENABLE_LEARNING_CONTROL_PLANE", True)
    _MEM_EVENTS.clear()
    _MEM_EVENT_DEDUP.clear()

    service = LearningEventService(redis_client=None)
    await service.emit(
        event_type="route_decision",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        trace_id="trace-1",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        complexity_tier="medium",
        task_type="expert_auto",
        data={
            "message": "very long text should be redacted",
            "latency_ms": 1234,
        },
    )

    rows = await service.list_events_since(since=_utcnow() - timedelta(minutes=10), limit=20)
    assert rows
    row = rows[-1]
    assert row["event_type"] == "route_decision"
    assert row["strategy_pack"] == "general_v2"
    assert row["data"]["latency_ms"] == 1234
    assert "message" not in row["data"]
    assert "message_sha1" in row["data"]


@pytest.mark.asyncio
async def test_learning_event_dedup_for_trace_and_response(monkeypatch):
    monkeypatch.setattr("app.services.learning_event_service.settings.ENABLE_LEARNING_CONTROL_PLANE", True)
    _MEM_EVENTS.clear()
    _MEM_EVENT_DEDUP.clear()

    service = LearningEventService(redis_client=None)
    payload1 = await service.emit(
        event_type="prompt_applied",
        user_id="u1",
        session_id="s1",
        workflow_id="standard_chat",
        trace_id="trace-x",
        response_id="resp-x",
        data={"prompt_version": "v2"},
    )
    payload2 = await service.emit(
        event_type="prompt_applied",
        user_id="u1",
        session_id="s1",
        workflow_id="standard_chat",
        trace_id="trace-x",
        response_id="resp-x",
        data={"prompt_version": "v2"},
    )

    assert payload1
    assert payload2 == {}
