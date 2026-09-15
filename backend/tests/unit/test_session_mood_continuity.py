from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import DashboardReadout, DashboardReadoutBuilder
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.orchestration.orchestrator import ChatOrchestrator
from app.services.memory_service import MemoryService, SESSION_MOOD_LAST_KEY_TEMPLATE


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        bucket = self.lists.get(key, [])
        if end == -1:
            return bucket[start:]
        return bucket[start : end + 1]


class _CapturingDecisionLoop:
    def __init__(self) -> None:
        self.readouts: list[DashboardReadout] = []

    async def decide(self, readout: DashboardReadout) -> AuroraDecision:
        self.readouts.append(readout)
        return AuroraDecision(action="wait")


class _StubSelfModelService:
    async def get_readout_summary(self, **kwargs) -> dict[str, Any]:
        return {}


def _readout(
    *,
    request_extra_context: dict[str, Any],
    conversation_summary: dict[str, Any],
) -> DashboardReadout:
    return DashboardReadout(
        surface="aurora_modeling",
        user_id="user-1",
        conversation_id="new-session",
        request_id="req-1",
        user_message="今天继续",
        activity_profile={"conversation_style": "warm"},
        hard_bounds=AuroraHardBounds(),
        candidate_affordances=AuroraSkillRegistry().load_candidate_affordances("aurora_modeling"),
        covered_domains=["goal"],
        missing_domains=["scope", "baseline", "time"],
        request_extra_context=dict(request_extra_context),
        conversation_summary=dict(conversation_summary),
    )


@pytest.mark.asyncio
async def test_orchestrator_records_stressed_mood_on_high_pressure_session_end() -> None:
    redis = _FakeRedis()
    orchestrator = ChatOrchestrator.__new__(ChatOrchestrator)
    orchestrator.redis = redis

    await orchestrator._maybe_upsert_session_mood(
        active_db=None,
        user_id="user-1",
        session_id="session-1",
        request_extra_context={"struggle_score": 0.72},
    )

    raw = await redis.get(SESSION_MOOD_LAST_KEY_TEMPLATE.format(user_id="user-1"))
    assert raw is not None
    payload = json.loads(raw)
    assert payload["session_id"] == "session-1"
    assert payload["mood_score"] == 0.7
    assert payload["mood_label"] == "stressed"


@pytest.mark.asyncio
async def test_plan_turn_injects_recent_stressed_session_mood_into_first_turn() -> None:
    redis = _FakeRedis()
    await MemoryService(None, redis_client=redis).upsert_session_mood(
        user_id="user-1",
        session_id="previous-session",
        mood_score=0.7,
        mood_label="stressed",
    )
    decision_loop = _CapturingDecisionLoop()
    service = AuroraRuntimeV1Service(
        redis,
        decision_loop=decision_loop,
        dashboard_builder=DashboardReadoutBuilder(None),
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="new-session",
        request_id="req-1",
        user_message="今天继续",
        request_extra_context={},
        conversation_context={"messages": []},
        user_context_payload={},
    )

    assert decision_loop.readouts[0].request_extra_context["last_session_mood"] == "stressed"


@pytest.mark.asyncio
async def test_plan_turn_ignores_stressed_session_mood_after_24h() -> None:
    redis = _FakeRedis()
    old_recorded_at = (datetime.now(UTC) - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    redis.store[SESSION_MOOD_LAST_KEY_TEMPLATE.format(user_id="user-1")] = json.dumps(
        {
            "user_id": "user-1",
            "session_id": "previous-session",
            "mood_score": 0.7,
            "mood_label": "stressed",
            "recorded_at": old_recorded_at,
        }
    )
    decision_loop = _CapturingDecisionLoop()
    service = AuroraRuntimeV1Service(
        redis,
        decision_loop=decision_loop,
        dashboard_builder=DashboardReadoutBuilder(None),
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="new-session",
        request_id="req-1",
        user_message="今天继续",
        request_extra_context={},
        conversation_context={"messages": []},
        user_context_payload={},
    )

    assert "last_session_mood" not in decision_loop.readouts[0].request_extra_context


def test_decision_loop_forces_empathy_check_in_for_stressed_new_session() -> None:
    loop = AuroraDecisionLoop()
    decision = AuroraDecision(
        action="wait",
        chat_directive={
            "intent": "ask_scope",
            "target_domain": "scope",
            "standard_layer_contract": {"response_type": "task_help"},
        },
    )

    validated = loop.validate_decision(
        decision,
        _readout(
            request_extra_context={"last_session_mood": "stressed"},
            conversation_summary={"message_count": 1, "recent_messages": []},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert validated.action == "emit_message"
    assert validated.chat_directive["intent"] == "empathy_check_in"
    assert "target_domain" not in validated.chat_directive
    assert contract["response_type"] == "emotional_support"


def test_decision_loop_does_not_force_empathy_check_in_after_first_turn() -> None:
    loop = AuroraDecisionLoop()
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "ask_scope"})

    validated = loop.validate_decision(
        decision,
        _readout(
            request_extra_context={"last_session_mood": "stressed"},
            conversation_summary={"message_count": 2, "recent_messages": []},
        ),
    )

    assert validated.chat_directive["intent"] != "empathy_check_in"
