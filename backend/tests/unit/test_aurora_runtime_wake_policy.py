from __future__ import annotations

import json

import pytest

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import DashboardReadout
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.wake_policy import AuroraWakePolicyService


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.kv[key] = value
        self.ttl[key] = ttl_seconds

    async def expire(self, key: str, ttl_seconds: int) -> None:
        self.ttl[key] = ttl_seconds


class _FakeJsonLLM:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls: list[list[dict[str, str]]] = []

    async def chat_json(self, messages, **kwargs):
        self.calls.append(messages)
        return self.payload


class _StubSelfModelService:
    def __init__(self, summary: dict) -> None:
        self.summary = dict(summary)

    async def get_readout_summary(self, **kwargs) -> dict:
        return dict(self.summary)


class _SilentChatAdapter:
    async def render(self, decision, readout) -> list[str]:
        return []

    async def _fallback_messages(self, decision, readout, *, reason: str | None = None) -> list[str]:
        return []


def _readout(*, wake_policy: dict | None = None) -> DashboardReadout:
    return DashboardReadout(
        surface="aurora_planning",
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="帮我看看这个计划。",
        activity_profile={
            "conversation_style": "structured",
            "expression": {
                "tone_warmth": 0.44,
                "directness": 0.62,
                "brevity": 0.74,
                "friendliness": 0.48,
                "challenge_intensity": 0.56,
            },
        },
        hard_bounds=AuroraHardBounds(),
        covered_domains=["goal", "scope"],
        missing_domains=["baseline", "time"],
        cold_start_context={"goal_type": "exam"},
        wake_policy=dict(wake_policy or {}),
    )


@pytest.mark.asyncio
async def test_wake_policy_keeps_low_risk_turn_in_silent_band() -> None:
    service = AuroraWakePolicyService(redis_client=_FakeRedis())

    decision = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="继续吧。",
        request_extra_context={
            "days_left": 14,
            "plan_completion_rate": 0.9,
            "expected_plan_completion_rate": 0.9,
            "struggle_score": 0.05,
            "standard_layer_uncertainty": 0.05,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.9, "task_failure_streak": 0},
    )

    assert decision.energy == "silent"
    assert decision.wake_score < 0.45
    for value in decision.components.to_dict().values():
        assert 0.0 <= float(value) <= 1.0


@pytest.mark.asyncio
async def test_wake_policy_enters_moderate_band_for_repeated_errors_and_quiz_drop() -> None:
    service = AuroraWakePolicyService(redis_client=_FakeRedis())

    decision = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="我还是卡住了。",
        request_extra_context={
            "days_left": 7,
            "plan_completion_rate": 0.55,
            "expected_plan_completion_rate": 0.75,
            "same_cause_error_streak": 3,
            "quiz_accuracy_history": [0.78, 0.58],
            "wake_reminder_topic": "TCP 状态变化",
            "struggle_score": 0.55,
            "standard_layer_uncertainty": 0.25,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.42, "task_failure_streak": 1},
    )

    assert decision.energy == "moderate"
    assert 0.45 <= decision.wake_score < 0.72
    assert decision.diagnostic_signal.triggered is True
    assert decision.diagnostic_signal.same_cause_error_streak == 3
    assert decision.diagnostic_signal.reminder_topic == "TCP 状态变化"


@pytest.mark.asyncio
async def test_wake_policy_full_candidate_respects_cooldown() -> None:
    redis = _FakeRedis()
    service = AuroraWakePolicyService(redis_client=redis)

    initial = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="继续。",
        request_extra_context={
            "days_left": 2,
            "plan_completion_rate": 0.48,
            "expected_plan_completion_rate": 0.85,
            "same_cause_error_streak": 4,
            "quiz_accuracy_history": [0.82, 0.60],
            "pass_probability": 0.4,
            "struggle_score": 0.65,
            "standard_layer_uncertainty": 0.45,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.2, "task_failure_streak": 3},
    )

    assert initial.full_candidate is True
    assert initial.full_allowed is True
    assert initial.energy == "full"
    assert initial.wake_score >= 0.72

    await service.record_full_wake(
        user_id="user-1",
        policy=initial.cooldown_policy,
    )

    blocked = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="继续。",
        request_extra_context={
            "days_left": 2,
            "plan_completion_rate": 0.48,
            "expected_plan_completion_rate": 0.85,
            "same_cause_error_streak": 4,
            "quiz_accuracy_history": [0.82, 0.60],
            "pass_probability": 0.4,
            "struggle_score": 0.65,
            "standard_layer_uncertainty": 0.45,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.2, "task_failure_streak": 3},
    )

    assert blocked.full_candidate is True
    assert blocked.full_allowed is False
    assert blocked.energy == "moderate"
    assert blocked.cooldown_status.remaining_seconds > 0
    assert blocked.cooldown_status.day_count == 1


@pytest.mark.asyncio
async def test_active_user_wake_phrase_enters_full_candidate_but_still_respects_cooldown() -> None:
    redis = _FakeRedis()
    service = AuroraWakePolicyService(redis_client=redis)

    first = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="你理解错我了，进入深度模式。",
        request_extra_context={
            "days_left": 14,
            "plan_completion_rate": 0.9,
            "expected_plan_completion_rate": 0.9,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.92, "task_failure_streak": 0},
    )

    assert first.user_requested_full_wake is True
    assert first.full_candidate is True
    assert first.full_allowed is True
    assert first.energy == "full"

    await service.record_full_wake(user_id="user-1", policy=first.cooldown_policy)

    second = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="重新校准一下。",
        request_extra_context={
            "days_left": 14,
            "plan_completion_rate": 0.9,
            "expected_plan_completion_rate": 0.9,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.92, "task_failure_streak": 0},
    )

    assert second.user_requested_full_wake is True
    assert second.full_candidate is True
    assert second.full_allowed is False
    assert second.energy == "moderate"


@pytest.mark.asyncio
async def test_chat_adapter_limits_messages_unless_full_mode() -> None:
    llm = _FakeJsonLLM({"messages": ["第一句。", "第二句。", "第三句。"]})
    adapter = ChatLayerAdapter(llm_factory=lambda: llm)
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "nudge"})

    moderate_messages = await adapter.render(
        decision,
        _readout(wake_policy={"multimessage_allowed": False, "context_budget": "compact"}),
    )
    full_messages = await adapter.render(
        decision,
        _readout(wake_policy={"multimessage_allowed": True, "context_budget": "extended"}),
    )

    assert moderate_messages == ["第一句。"]
    assert full_messages == ["第一句。", "第二句。", "第三句。"]


@pytest.mark.asyncio
async def test_plan_turn_injects_moderate_wake_policy_into_decision_prompt() -> None:
    decision_llm = _FakeJsonLLM({"action": "wait"})
    service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(llm_factory=lambda: decision_llm),
        chat_adapter=_SilentChatAdapter(),
        self_model_service=_StubSelfModelService(
            {
                "strategy_confidence": 0.42,
                "task_failure_streak": 1,
                "harness_effectiveness": {"task_completion_rate": 0.55},
            }
        ),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_planning",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="我这几天一直卡在 TCP 状态变化。",
        request_extra_context={
            "days_left": 7,
            "plan_completion_rate": 0.55,
            "expected_plan_completion_rate": 0.75,
            "same_cause_error_streak": 3,
            "quiz_accuracy_history": [0.78, 0.58],
            "wake_reminder_topic": "TCP 状态变化",
            "struggle_score": 0.55,
            "standard_layer_uncertainty": 0.25,
        },
        conversation_context={},
        user_context_payload={},
    )

    assert plan.wake_policy["energy"] == "moderate"
    prompt_payload = json.loads(decision_llm.calls[0][1]["content"])
    assert "wake_policy" in prompt_payload
    assert prompt_payload["wake_policy"]["energy"] == "moderate"
    assert "Moderate wake means a lightweight diagnostic nudge" in prompt_payload["rules"][-1]


@pytest.mark.asyncio
async def test_wake_policy_suppresses_risk_override_on_exam_day() -> None:
    """days_left == 0 means exam day itself — risk_override must not fire.

    On the day of the exam the user needs stabilisation, not aggressive calibration.
    The risk override window is 1–3 days before the exam, not on exam day.
    """
    service = AuroraWakePolicyService(redis_client=_FakeRedis())

    decision = await service.evaluate(
        active_db=None,
        user_id="user-1",
        user_message="考试今天，紧张。",
        request_extra_context={
            "days_left": 0,
            "plan_completion_rate": 0.3,   # very low — would normally trigger risk override
            "expected_plan_completion_rate": 0.75,
            "pass_probability": 0.35,       # below 0.45 threshold
            "struggle_score": 0.7,
            "standard_layer_uncertainty": 0.4,
        },
        user_context_payload={},
        self_model={"strategy_confidence": 0.2, "task_failure_streak": 3},
    )

    # On exam day risk_override must be suppressed — user needs calm, not calibration.
    assert decision.risk_override_triggered is False


@pytest.mark.asyncio
async def test_wake_policy_triggers_risk_override_for_days_left_one_to_three() -> None:
    """Risk override should fire for days_left in [1, 3] when other thresholds are met."""
    service = AuroraWakePolicyService(redis_client=_FakeRedis())

    for days_left in (1, 2, 3):
        decision = await service.evaluate(
            active_db=None,
            user_id="user-1",
            user_message="我还差很多没复习到。",
            request_extra_context={
                "days_left": days_left,
                "plan_completion_rate": 0.3,
                "expected_plan_completion_rate": 0.75,
                "pass_probability": 0.35,
                "struggle_score": 0.7,
                "standard_layer_uncertainty": 0.4,
            },
            user_context_payload={},
            self_model={"strategy_confidence": 0.2, "task_failure_streak": 3},
        )
        assert decision.risk_override_triggered is True, f"expected risk_override for days_left={days_left}"
