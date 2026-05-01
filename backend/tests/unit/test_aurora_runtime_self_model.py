from __future__ import annotations

import json

import pytest

from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.aurora.runtime_v1.self_model import (
    DEFAULT_STRATEGY_CONFIDENCE,
    SPARKLE_SELF_MODEL_TTL_SECONDS,
    SparkleSelfModelService,
)
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.kv[key] = value
        self.ttl[key] = ttl

    async def expire(self, key: str, ttl: int) -> None:
        self.ttl[key] = ttl


class _SpyDecisionLoop:
    def __init__(self) -> None:
        self.readout = None

    async def decide(self, readout):
        self.readout = readout
        return AuroraDecision(action="wait")


class _SilentChatAdapter:
    async def render(self, decision, readout) -> list[str]:
        return []

    async def _fallback_messages(self, decision, readout, *, reason: str | None = None) -> list[str]:
        return []


@pytest.mark.asyncio
async def test_plan_turn_bootstraps_self_model_in_redis_with_ttl_and_readout_summary() -> None:
    redis = _FakeRedis()
    spy = _SpyDecisionLoop()
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=spy,
        chat_adapter=_SilentChatAdapter(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_planning",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="按这个节奏继续吧。",
        request_extra_context={"task_state": {"daily_available_hours": 1.5}},
        conversation_context={},
        user_context_payload={"profile_context": {"preferences": {"cold_start_context": {"knowledge_baseline": "刚开始补基础"}}}},
    )

    key = "aurora:self_model:user-1"
    assert key in redis.kv
    assert redis.ttl[key] == SPARKLE_SELF_MODEL_TTL_SECONDS

    stored = json.loads(redis.kv[key])
    assert stored["strategy_confidence"] == pytest.approx(DEFAULT_STRATEGY_CONFIDENCE)
    assert stored["needs_recalibration"] is False
    assert set(stored.keys()) >= {
        "strategy_confidence",
        "known_assumptions",
        "harness_effectiveness",
        "needs_recalibration",
        "recalibration_reasons",
    }

    assert spy.readout is not None
    assert spy.readout.self_model["strategy_confidence"] == pytest.approx(DEFAULT_STRATEGY_CONFIDENCE)
    assert spy.readout.self_model["known_assumptions"][0]["statement"].endswith("90 分钟学习")


@pytest.mark.asyncio
async def test_task_timeouts_reduce_strategy_confidence_and_trigger_recalibration() -> None:
    redis = _FakeRedis()
    service = SparkleSelfModelService(redis)

    initial = await service.get_readout_summary(user_id="user-timeout")
    assert initial["strategy_confidence"] == pytest.approx(DEFAULT_STRATEGY_CONFIDENCE)

    for index in range(3):
        await service.record_task_outcome(
            user_id="user-timeout",
            signal_id=f"timeout-{index}",
            completed=False,
            timed_out=True,
            estimated_minutes=30,
            actual_minutes=55,
            difficulty=4,
            source="test",
            reason="连续做不完",
        )

    summary = await service.get_readout_summary(user_id="user-timeout")
    assert summary["strategy_confidence"] < DEFAULT_STRATEGY_CONFIDENCE
    assert summary["harness_effectiveness"]["task_completion_rate"] < 0.55
    assert summary["needs_recalibration"] is True
    assert summary["task_failure_streak"] == 3
    assert any("连续 3 次任务超时或未完成" in reason for reason in summary["recalibration_reasons"])
    assert redis.ttl["aurora:self_model:user-timeout"] == SPARKLE_SELF_MODEL_TTL_SECONDS


@pytest.mark.asyncio
async def test_user_correction_increments_counter_and_degrades_context_hit_rate() -> None:
    redis = _FakeRedis()
    service = SparkleSelfModelService(redis)

    await service.record_user_correction(
        user_id="user-correction",
        signal_id="correction-1",
        reason="不是每天 2 小时，我通常只有 40 分钟。",
        source="test",
    )

    summary = await service.get_readout_summary(user_id="user-correction")
    assert summary["harness_effectiveness"]["user_corrections_count"] == 1
    assert summary["harness_effectiveness"]["context_hit_rate"] < DEFAULT_STRATEGY_CONFIDENCE
    assert summary["strategy_confidence"] < DEFAULT_STRATEGY_CONFIDENCE


# ── F21: Sprint Self-Model Daily Recap ──────────────────────────────────────


@pytest.mark.asyncio
async def test_daily_recap_working_tier_resets_failure_streak() -> None:
    """completion_rate >= 0.8 → task_shape='working', failure_streak reset to 0."""
    redis = _FakeRedis()
    service = SparkleSelfModelService(redis)

    # Pre-set a failure streak so we can verify it resets.
    await service.record_task_outcome(
        user_id="user-recap-working",
        signal_id="pre-fail-1",
        completed=False,
        timed_out=True,
    )
    await service.record_task_outcome(
        user_id="user-recap-working",
        signal_id="pre-fail-2",
        completed=False,
        timed_out=True,
    )
    before = await service.get_readout_summary(user_id="user-recap-working")
    assert before["task_failure_streak"] >= 2

    await service.update_daily_recap(
        user_id="user-recap-working",
        completion_rate=0.85,
    )

    summary = await service.get_readout_summary(user_id="user-recap-working")
    assert summary["harness_effectiveness"]["task_shape"] == "working"
    assert summary["task_failure_streak"] == 0


@pytest.mark.asyncio
async def test_daily_recap_partial_tier_leaves_streak_unchanged() -> None:
    """0.4 <= completion_rate < 0.8 → task_shape='partial', streak unchanged."""
    redis = _FakeRedis()
    service = SparkleSelfModelService(redis)

    await service.update_daily_recap(
        user_id="user-recap-partial",
        completion_rate=0.55,
    )

    summary = await service.get_readout_summary(user_id="user-recap-partial")
    assert summary["harness_effectiveness"]["task_shape"] == "partial"
    assert summary["task_failure_streak"] == 0


@pytest.mark.asyncio
async def test_daily_recap_struggling_tier_increments_failure_streak() -> None:
    """completion_rate < 0.4 → task_shape='struggling', failure_streak += 1."""
    redis = _FakeRedis()
    service = SparkleSelfModelService(redis)

    await service.update_daily_recap(
        user_id="user-recap-struggling",
        completion_rate=0.3,
    )

    summary = await service.get_readout_summary(user_id="user-recap-struggling")
    assert summary["harness_effectiveness"]["task_shape"] == "struggling"
    assert summary["task_failure_streak"] == 1

    # Second struggling day increments again.
    await service.update_daily_recap(
        user_id="user-recap-struggling",
        completion_rate=0.2,
    )
    summary2 = await service.get_readout_summary(user_id="user-recap-struggling")
    assert summary2["task_failure_streak"] == 2


@pytest.mark.asyncio
async def test_daily_recap_not_triggered_when_day_completed_false() -> None:
    """When day_completed is False/absent, plan_turn must not alter self_model."""
    redis = _FakeRedis()
    spy = _SpyDecisionLoop()
    svc = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=spy,
        chat_adapter=_SilentChatAdapter(),
    )

    await svc.plan_turn(
        active_db=None,
        user_id="user-no-recap",
        surface="aurora_planning",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="继续复习",
        request_extra_context={"task_state": {"day_completed": False, "completion_rate": 0.3}},
        conversation_context={},
        user_context_payload={},
    )

    stored = json.loads(redis.kv["aurora:self_model:user-no-recap"])
    assert stored["harness_effectiveness"]["task_shape"] == "partial"  # default, not "struggling"
    assert stored["failure_streak"] == 0


@pytest.mark.asyncio
async def test_plan_turn_applies_daily_recap_on_day_completed() -> None:
    """plan_turn with day_completed=True updates self_model via daily recap."""
    redis = _FakeRedis()
    spy = _SpyDecisionLoop()
    svc = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=spy,
        chat_adapter=_SilentChatAdapter(),
    )

    await svc.plan_turn(
        active_db=None,
        user_id="user-day-done",
        surface="aurora_planning",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="今天复习完了",
        request_extra_context={"task_state": {"day_completed": True, "completion_rate": 0.85}},
        conversation_context={},
        user_context_payload={},
    )

    stored = json.loads(redis.kv["aurora:self_model:user-day-done"])
    assert stored["harness_effectiveness"]["task_shape"] == "working"
    assert stored["failure_streak"] == 0


@pytest.mark.asyncio
async def test_plan_turn_daily_recap_struggling_increments_streak() -> None:
    """plan_turn with day_completed=True and low rate increments failure_streak."""
    redis = _FakeRedis()
    spy = _SpyDecisionLoop()
    svc = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=spy,
        chat_adapter=_SilentChatAdapter(),
    )

    await svc.plan_turn(
        active_db=None,
        user_id="user-day-struggle",
        surface="aurora_planning",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="今天没做完",
        request_extra_context={"task_state": {"day_completed": True, "completion_rate": 0.3}},
        conversation_context={},
        user_context_payload={},
    )

    stored = json.loads(redis.kv["aurora:self_model:user-day-struggle"])
    assert stored["harness_effectiveness"]["task_shape"] == "struggling"
    assert stored["failure_streak"] == 1
