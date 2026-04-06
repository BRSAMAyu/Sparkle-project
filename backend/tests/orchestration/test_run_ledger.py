from __future__ import annotations

import pytest

from app.orchestration.run_ledger import RunLedgerRecorder, RunLedgerStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value

    async def rpush(self, key: str, value: str):
        self.lists.setdefault(key, []).append(value)

    async def expire(self, key: str, ttl: int):
        return True

    async def lrange(self, key: str, start: int, end: int):
        items = self.lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start : end + 1]


@pytest.mark.asyncio
async def test_run_ledger_recorder_updates_summary_and_persists_events():
    redis = FakeRedis()
    recorder = RunLedgerRecorder(
        trace_id="trace-1",
        session_id="session-1",
        workflow_id="workflow-1",
        response_id="response-1",
        prompt_version="v2",
        request_id="request-1",
        redis_client=redis,
    )

    await recorder.record_event(
        event_type="route_selected",
        label="路由完成",
        workflow_stage="routing",
        metadata={"execution_mode": "multi_agent", "reason": "complex request"},
        emit_snapshot=False,
    )
    await recorder.record_event(
        event_type="review_completed",
        label="审查完成",
        workflow_stage="review",
        metadata={
            "decision": "passed",
            "overall_score": 0.91,
            "model_key": "deepseek_reason",
            "provider": "deepseek",
            "target_type": "llm_response",
        },
        emit_snapshot=False,
    )

    summary = await RunLedgerStore.load_summary(redis, "trace-1")
    events = await RunLedgerStore.load_events(redis, "trace-1")

    assert summary is not None
    assert summary["route"]["execution_mode"] == "multi_agent"
    assert summary["quality"]["reviewed"] is True
    assert summary["quality"]["review_score"] == pytest.approx(0.91)
    assert len(events) == 2
    assert events[0]["event_type"] == "route_selected"
    assert events[1]["event_type"] == "review_completed"


@pytest.mark.asyncio
async def test_append_external_event_enriches_feedback_effects():
    redis = FakeRedis()
    await RunLedgerStore.persist(
        redis,
        summary=RunLedgerStore.build_empty_summary(trace_id="trace-2"),
        event={
            "event_id": "boot",
            "event_type": "run_started",
            "label": "开始",
            "workflow_stage": "orchestration",
            "timestamp": "2026-01-01T00:00:00",
            "status": "completed",
            "metadata": {},
        },
    )

    await RunLedgerStore.append_external_event(
        redis,
        trace_id="trace-2",
        event_type="feedback_received",
        label="收到反馈",
        workflow_stage="feedback",
        metadata={"feedback_type": "down", "reasons": ["incomplete"]},
    )
    updated = await RunLedgerStore.append_external_event(
        redis,
        trace_id="trace-2",
        event_type="strategy_effect_applied",
        label="策略已更新",
        workflow_stage="feedback",
        metadata={
            "effect_target": "prompt_bandit",
            "status": "applied",
            "detail": "standard_chat:v2",
            "effect_latency_seconds": 12,
        },
    )

    assert updated is not None
    assert updated["feedback"]["received"] is True
    assert updated["feedback"]["feedback_type"] == "down"
    assert updated["feedback"]["effect_latency_seconds"] == 12
    assert updated["feedback"]["strategy_effects"][0]["target"] == "prompt_bandit"


@pytest.mark.asyncio
async def test_run_ledger_tracks_semantic_control_summary():
    redis = FakeRedis()
    recorder = RunLedgerRecorder(
        trace_id="trace-semantic",
        session_id="session-semantic",
        workflow_id="workflow-semantic",
        response_id="response-semantic",
        prompt_version="v1",
        request_id="request-semantic",
        redis_client=redis,
    )

    await recorder.record_event(
        event_type="semantic_control_attached",
        label="语义控制附着",
        workflow_stage="orchestration",
        metadata={
            "selected_terms": [{"term": "experience_mode", "value": "clarify"}],
            "response_contract": {"should_ask_high_value_question_first": True},
            "observed_compliance_flags": {"clarify_question_first": True},
        },
        emit_snapshot=False,
    )

    summary = await RunLedgerStore.load_summary(redis, "trace-semantic")

    assert summary is not None
    assert summary["semantic_control"]["selected_terms"][0]["value"] == "clarify"
    assert summary["semantic_control"]["response_contract"]["should_ask_high_value_question_first"] is True
