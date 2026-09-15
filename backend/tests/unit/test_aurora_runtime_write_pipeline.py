from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.write_pipeline import AURORA_CLAIM_KEY_TEMPLATE, get_claim


class _FakeRedis:
    def __init__(self) -> None:
        self.now = datetime(2026, 4, 25, 8, 0, tzinfo=UTC).replace(tzinfo=None)
        self.store: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self.expires_at: dict[str, datetime] = {}

    async def get(self, key: str) -> str | None:
        expires_at = self.expires_at.get(key)
        if expires_at is not None and self.now >= expires_at:
            self.store.pop(key, None)
            self.ttl.pop(key, None)
            self.expires_at.pop(key, None)
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttl[key] = ttl
        self.expires_at[key] = self.now + timedelta(seconds=ttl)

    async def expire(self, key: str, ttl: int) -> None:
        if key not in self.store:
            return
        self.ttl[key] = ttl
        self.expires_at[key] = self.now + timedelta(seconds=ttl)


class _StaticDecisionLoop:
    def __init__(self, decision: AuroraDecision) -> None:
        self.decision = decision

    async def decide(self, _readout):
        return self.decision


class _StaticChatAdapter:
    async def render(self, _decision, _readout):
        return ["信息够用了，我会按这个状态继续。"]


@pytest.mark.asyncio
async def test_plan_turn_submits_modeling_and_resolved_claims_to_redis() -> None:
    redis = _FakeRedis()
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=_StaticDecisionLoop(
            AuroraDecision(
                action="emit_message",
                surface_complete=True,
                modeling_complete=True,
                state_updates={
                    "informational_tensions": [
                        {"domain": "knowledge_baseline", "status": "resolved", "description": "基础已确认"}
                    ]
                },
                harness_updates={"strategy": {"concept_first": True}},
            )
        ),
        chat_adapter=_StaticChatAdapter(),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="我是零基础，每天 2 小时。",
        request_extra_context={
            "task_state": {
                "goal_raw": "7天后通过计网考试",
                "knowledge_baseline": "零基础",
                "daily_available_hours": 2,
            }
        },
        conversation_context={},
        user_context_payload={},
    )

    assert plan.modeling_complete is True
    assert AURORA_CLAIM_KEY_TEMPLATE.format(user_id="user-1", domain="modeling_complete") in redis.store

    modeling_claim = await get_claim("modeling_complete", user_id="user-1", redis=redis)
    baseline_claim = await get_claim("baseline", user_id="user-1", redis=redis)
    learning_style_claim = await get_claim("learning_style", user_id="user-1", redis=redis)

    assert modeling_claim is not None and modeling_claim.value is True
    assert baseline_claim is not None and baseline_claim.value == "零基础"
    assert learning_style_claim is not None and learning_style_claim.value == "concept_first"
