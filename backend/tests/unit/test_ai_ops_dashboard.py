from __future__ import annotations

import fnmatch
import uuid
from datetime import datetime

import pytest

import app.orchestration.token_tracker as token_tracker_module
from app.models.response_feedback import ResponseFeedback
from app.orchestration.token_tracker import TokenTracker
from app.services.user_settings_service import UserSettingsService


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, int | str] = {}
        self.hashes: dict[str, dict[str, int]] = {}
        self.lists: dict[str, list[str]] = {}

    async def rpush(self, key: str, value: str):
        self.lists.setdefault(key, []).append(value)

    async def incrby(self, key: str, value: int):
        current = int(self.kv.get(key, 0))
        self.kv[key] = current + value

    async def incr(self, key: str):
        await self.incrby(key, 1)

    async def expire(self, key: str, _seconds: int):
        return True

    async def get(self, key: str):
        return self.kv.get(key)

    async def mget(self, *keys: str):
        return [self.kv.get(key) for key in keys]

    async def hincrby(self, key: str, field: str, value: int):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = int(bucket.get(field, 0)) + value

    async def hgetall(self, key: str):
        return self.hashes.get(key, {})

    async def scan_iter(self, match: str | None = None):
        keys = list(self.kv.keys()) + list(self.hashes.keys()) + list(self.lists.keys())
        for key in keys:
            if match is None or fnmatch.fnmatch(key, match):
                yield key


@pytest.mark.asyncio
async def test_token_tracker_ai_ops_summary_aggregates_success_fallback_and_outcomes():
    redis = FakeRedis()
    tracker = TokenTracker(redis)

    await tracker.record_usage(
        user_id="user-1",
        session_id="session-1",
        request_id="req-success",
        prompt_tokens=100,
        completion_tokens=150,
        model="qwen3.5-flash",
        cost=0.0025,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="study_plan",
        timing_stats={
            "total_duration_ms": 5000,
            "first_token_ms": 900,
            "stream_duration_ms": 3200,
        },
        success=True,
        fallback_used=True,
        outcome_stats={
            "task_count": 3,
            "plan_count": 1,
            "execution_count": 1,
        },
    )
    await tracker.record_usage(
        user_id="user-1",
        session_id="session-1",
        request_id="req-failed",
        prompt_tokens=0,
        completion_tokens=0,
        model="qwen3.5-flash",
        cost=0.0,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="study_plan",
        timing_stats={"total_duration_ms": 1200},
        success=False,
        fallback_used=False,
        outcome_stats={},
    )

    summary = await tracker.get_ai_ops_summary("user-1", days=1)

    assert len(summary) == 1
    item = summary[0]
    assert item["chat_mode"] == "study_plan"
    assert item["requests_total"] == 2
    assert item["requests_success"] == 1
    assert item["requests_failed"] == 1
    assert item["fallback_rate_percent"] == 50.0
    assert item["task_count"] == 3
    assert item["plan_count"] == 1
    assert item["execution_count"] == 1
    assert item["task_conversion_rate_percent"] == 50.0


@pytest.mark.asyncio
async def test_user_settings_service_ai_ops_dashboard_enriches_feedback(db_session):
    redis = FakeRedis()
    token_tracker_module._token_tracker_instance = None
    tracker = TokenTracker(redis)
    token_tracker_module._token_tracker_instance = tracker

    user_id = uuid.uuid4()
    await tracker.record_usage(
        user_id=str(user_id),
        session_id="session-2",
        request_id="req-ops",
        prompt_tokens=120,
        completion_tokens=80,
        model="mimo-v2-flash",
        cost=0.003,
        reasoning_mode="deep",
        model_tier="pro",
        chat_mode="error_diagnosis",
        timing_stats={
            "total_duration_ms": 4200,
            "first_token_ms": 700,
            "stream_duration_ms": 2400,
        },
        success=True,
        fallback_used=False,
        outcome_stats={"execution_count": 1},
    )

    db_session.add(
        ResponseFeedback(
            user_id=user_id,
            response_id=uuid.uuid4(),
            trace_id="trace-up",
            workflow_id="error_diagnosis",
            prompt_version="v1",
            feedback_type=ResponseFeedback.FEEDBACK_UP,
            meta={"chat_mode": "error_diagnosis"},
            created_at=datetime.utcnow(),
        )
    )
    db_session.add(
        ResponseFeedback(
            user_id=user_id,
            response_id=uuid.uuid4(),
            trace_id="trace-down",
            workflow_id="error_diagnosis",
            prompt_version="v1",
            feedback_type=ResponseFeedback.FEEDBACK_DOWN,
            meta={"chat_mode": "error_diagnosis"},
            created_at=datetime.utcnow(),
        )
    )
    await db_session.commit()

    service = UserSettingsService(db_session, redis=redis)
    payload = await service.get_ai_ops_dashboard(user_id, days=7)

    assert payload["items"]
    item = payload["items"][0]
    assert item["chat_mode"] == "error_diagnosis"
    assert item["positive_feedback_count"] == 1
    assert item["negative_feedback_count"] == 1
    assert item["positive_feedback_rate_percent"] == 50.0
    assert item["feedback_coverage_percent"] == 100.0
    assert item["avg_prompt_utilization_percent"] == 0.0
    assert item["avg_inference_utilization_percent"] == 0.0

    token_tracker_module._token_tracker_instance = None


@pytest.mark.asyncio
async def test_user_settings_service_ai_ops_export_returns_overview_and_trends(db_session):
    redis = FakeRedis()
    token_tracker_module._token_tracker_instance = None
    tracker = TokenTracker(redis)
    token_tracker_module._token_tracker_instance = tracker

    user_id = uuid.uuid4()
    await tracker.record_usage(
        user_id=str(user_id),
        session_id="session-3",
        request_id="req-standard",
        prompt_tokens=100,
        completion_tokens=60,
        model="mimo-v2-flash",
        cost=0.0018,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="standard",
        timing_stats={
            "total_duration_ms": 3100,
            "first_token_ms": 680,
            "stream_duration_ms": 1800,
        },
        success=True,
        fallback_used=False,
        outcome_stats={"execution_count": 1},
    )
    await tracker.record_usage(
        user_id=str(user_id),
        session_id="session-3",
        request_id="req-study",
        prompt_tokens=140,
        completion_tokens=120,
        model="qwen3.5-plus",
        cost=0.0032,
        reasoning_mode="deep",
        model_tier="plus",
        chat_mode="study_plan",
        timing_stats={
            "total_duration_ms": 8400,
            "first_token_ms": 1100,
            "stream_duration_ms": 5900,
        },
        success=True,
        fallback_used=True,
        outcome_stats={"task_count": 2, "plan_count": 1, "execution_count": 1},
    )

    service = UserSettingsService(db_session, redis=redis)
    payload = await service.get_ai_ops_export(user_id, days=7)

    assert payload["overview"]["requests_total"] == 2
    assert payload["overview"]["success_rate_percent"] == 100.0
    assert payload["overview"]["fallback_rate_percent"] == 50.0
    assert payload["overview"]["execution_count"] == 2
    assert payload["overview"]["avg_prompt_utilization_percent"] == 0.0
    assert payload["overview"]["avg_inference_utilization_percent"] == 0.0
    assert len(payload["trend_series"]) == 2
    study_series = next(item for item in payload["trend_series"] if item["chat_mode"] == "study_plan")
    assert study_series["points"][0]["execution_conversion_rate_percent"] == 100.0

    token_tracker_module._token_tracker_instance = None


@pytest.mark.asyncio
async def test_token_tracker_ai_ops_summary_surfaces_stage9_utilization_metrics():
    redis = FakeRedis()
    tracker = TokenTracker(redis)

    await tracker.record_usage(
        user_id="user-util",
        session_id="session-util",
        request_id="req-util",
        prompt_tokens=80,
        completion_tokens=120,
        model="qwen3.5-flash",
        cost=0.0019,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="standard",
        success=True,
        fallback_used=False,
        utilization_metrics={
            "prompt_utilization": {
                "status": "known",
                "numerator": 4,
                "denominator": 5,
                "ratio": 0.8,
            },
            "inference_utilization": {
                "status": "known",
                "numerator": 3,
                "denominator": 4,
                "ratio": 0.75,
            },
        },
    )
    await tracker.record_usage(
        user_id="user-util",
        session_id="session-util",
        request_id="req-util-2",
        prompt_tokens=20,
        completion_tokens=10,
        model="qwen3.5-flash",
        cost=0.0002,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="standard",
        success=True,
        fallback_used=False,
        utilization_metrics={
            "prompt_utilization": {
                "status": "not_applicable",
                "numerator": 0,
                "denominator": 0,
                "ratio": None,
            },
            "inference_utilization": {
                "status": "unknown",
                "numerator": 0,
                "denominator": 0,
                "ratio": None,
            },
        },
    )

    summary = await tracker.get_ai_ops_summary("user-util", days=1)

    assert len(summary) == 1
    item = summary[0]
    assert item["avg_prompt_utilization_percent"] == 80.0
    assert item["avg_inference_utilization_percent"] == 75.0
    assert item["prompt_utilization_known_count"] == 1
    assert item["prompt_utilization_not_applicable_count"] == 1
    assert item["inference_utilization_known_count"] == 1
    assert item["inference_utilization_unknown_count"] == 1


@pytest.mark.asyncio
async def test_user_settings_service_ai_ops_export_rolls_up_utilization_metrics(db_session):
    redis = FakeRedis()
    token_tracker_module._token_tracker_instance = None
    tracker = TokenTracker(redis)
    token_tracker_module._token_tracker_instance = tracker

    user_id = uuid.uuid4()
    await tracker.record_usage(
        user_id=str(user_id),
        session_id="session-util-rollup",
        request_id="req-ops-util-1",
        prompt_tokens=60,
        completion_tokens=90,
        model="qwen3.5-flash",
        cost=0.0012,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="standard",
        success=True,
        fallback_used=False,
        utilization_metrics={
            "prompt_utilization": {
                "status": "known",
                "numerator": 4,
                "denominator": 5,
                "ratio": 0.8,
            },
            "inference_utilization": {
                "status": "known",
                "numerator": 3,
                "denominator": 4,
                "ratio": 0.75,
            },
        },
    )
    await tracker.record_usage(
        user_id=str(user_id),
        session_id="session-util-rollup",
        request_id="req-ops-util-2",
        prompt_tokens=30,
        completion_tokens=20,
        model="qwen3.5-flash",
        cost=0.0004,
        reasoning_mode="balanced",
        model_tier="standard",
        chat_mode="standard",
        success=True,
        fallback_used=False,
        utilization_metrics={
            "prompt_utilization": {
                "status": "unknown",
                "numerator": 0,
                "denominator": 0,
                "ratio": None,
            },
            "inference_utilization": {
                "status": "not_applicable",
                "numerator": 0,
                "denominator": 0,
                "ratio": None,
            },
        },
    )

    service = UserSettingsService(db_session, redis=redis)
    payload = await service.get_ai_ops_export(user_id, days=7)

    assert payload["overview"]["avg_prompt_utilization_percent"] == 80.0
    assert payload["overview"]["avg_inference_utilization_percent"] == 75.0
    assert payload["overview"]["prompt_utilization_known_count"] == 1
    assert payload["overview"]["prompt_utilization_unknown_count"] == 1
    assert payload["overview"]["inference_utilization_known_count"] == 1
    assert payload["overview"]["inference_utilization_not_applicable_count"] == 1

    token_tracker_module._token_tracker_instance = None
