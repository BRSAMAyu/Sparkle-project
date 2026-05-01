from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import select

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.decision_loop import AuroraDecisionLoop
from app.aurora.runtime_v1.models import AuroraDecisionTelemetry
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService


class _FakeJsonLLM:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    async def chat_json(self, messages, **kwargs):
        del messages, kwargs
        return self.payload


class _FakeRedis:
    def __init__(self) -> None:
        self._lists: dict[str, list[str]] = {}

    async def lpush(self, key: str, value: str) -> None:
        bucket = self._lists.setdefault(key, [])
        bucket.insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        bucket = self._lists.setdefault(key, [])
        self._lists[key] = bucket[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        bucket = self._lists.get(key, [])
        if end == -1:
            return bucket[start:]
        return bucket[start : end + 1]

    async def expire(self, key: str, seconds: int) -> None:
        del key, seconds


def _strategy(
    *,
    concept_first: bool = True,
    problem_first: bool = False,
    worked_example_first: bool = True,
    retrieval_practice: bool = False,
    interleaving: bool = False,
    spaced_review: bool = False,
    error_analysis_required: bool = False,
) -> dict[str, bool]:
    return {
        "concept_first": concept_first,
        "problem_first": problem_first,
        "worked_example_first": worked_example_first,
        "retrieval_practice": retrieval_practice,
        "interleaving": interleaving,
        "spaced_review": spaced_review,
        "error_analysis_required": error_analysis_required,
    }


@pytest.mark.asyncio
async def test_plan_turn_writes_aurora_telemetry_record(db_session, test_user) -> None:
    service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(
            llm_factory=lambda: _FakeJsonLLM(
                {
                    "action": "emit_message",
                    "chat_directive": {"intent": "ask_scope", "target_domain": "scope"},
                    "harness_updates": {
                        "strategy": _strategy(
                            concept_first=True,
                            worked_example_first=True,
                            retrieval_practice=True,
                        ),
                        "expression": {
                            "directness": 0.88,
                            "brevity": 0.81,
                        },
                    },
                }
            )
        ),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["先把考试范围告诉我。"]})),
    )

    await service.plan_turn(
        active_db=db_session,
        user_id=str(test_user.id),
        surface="aurora_modeling",
        conversation_id="conv-telemetry-write",
        request_id="req-telemetry-1",
        user_message="7天后考计网，我想先梳理一下。",
        request_extra_context={
            "exam_sprint_policy": {"days_remaining": 7, "mode": "seven_day_survival"},
            "task_state": {
                "goal_raw": "7天后通过计网考试",
                "daily_available_hours": 3,
            },
            "informational_tensions": [{"domain": "scope", "status": "open"}],
            "standard_layer_contract": {
                "response_type": "task_help",
                "must_include": ["one worked example"],
                "must_not_include": ["long motivational speech"],
            },
        },
        conversation_context={},
        user_context_payload={},
    )

    stored = (
        await db_session.execute(
            select(AuroraDecisionTelemetry).where(AuroraDecisionTelemetry.conversation_id == "conv-telemetry-write")
        )
    ).scalar_one()

    assert stored.user_id == test_user.id
    assert stored.request_id == "req-telemetry-1"
    assert stored.action == "emit_message"
    assert stored.outcome is None
    assert stored.strategy_payload["concept_first"] is True
    assert stored.strategy_payload["retrieval_practice"] is True
    assert stored.expression_payload["directness"] == pytest.approx(0.88)
    assert stored.expression_payload["brevity"] == pytest.approx(0.81)
    assert "user_message" in stored.context_mask
    assert "wake_policy" in stored.context_mask
    assert stored.wake_score >= 0.0
    assert stored.strategy_confidence == pytest.approx(0.7)
    assert stored.chat_directive_core["target_domain"] == "scope"
    assert stored.standard_layer_contract["response_type"] == "task_help"


@pytest.mark.asyncio
async def test_detect_stale_strategy_flags_repeated_task_help_on_same_domain() -> None:
    redis = _FakeRedis()
    service = AuroraDecisionTelemetryService(None, redis_client=redis)
    key = service.recent_telemetry_key(user_id="user-stale", conversation_id="conv-stale")
    for request_id in ("req-1", "req-2", "req-3"):
        await redis.lpush(
            key,
            json.dumps(
                {
                    "request_id": request_id,
                    "response_type": "task_help",
                    "target_domain": "tcp",
                    "covered_domains": ["goal"],
                },
                ensure_ascii=False,
            ),
        )

    signal = await service.detect_stale_strategy(user_id="user-stale", conversation_id="conv-stale")

    assert signal == {
        "stale": True,
        "stuck_on": "tcp",
        "suggestion": "switch_to_concept_first",
    }


@pytest.mark.asyncio
async def test_detect_stale_strategy_ignores_repetition_when_coverage_grows() -> None:
    redis = _FakeRedis()
    service = AuroraDecisionTelemetryService(None, redis_client=redis)
    key = service.recent_telemetry_key(user_id="user-moving", conversation_id="conv-moving")
    for covered_domains in (["goal"], ["goal", "scope"], ["goal", "scope", "tcp"]):
        await redis.lpush(
            key,
            json.dumps(
                {
                    "response_type": "task_help",
                    "target_domain": "tcp",
                    "covered_domains": covered_domains,
                },
                ensure_ascii=False,
            ),
        )

    signal = await service.detect_stale_strategy(user_id="user-moving", conversation_id="conv-moving")

    assert signal is None


@pytest.mark.asyncio
async def test_next_turn_backfills_previous_aurora_outcome(db_session, test_user) -> None:
    first_service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(
            llm_factory=lambda: _FakeJsonLLM(
                {
                    "action": "emit_message",
                    "chat_directive": {"intent": "ask_scope", "target_domain": "scope"},
                    "harness_updates": {"strategy": _strategy()},
                }
            )
        ),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["考试范围主要考哪些章节？"]})),
    )

    await first_service.plan_turn(
        active_db=db_session,
        user_id=str(test_user.id),
        surface="aurora_modeling",
        conversation_id="conv-telemetry-backfill",
        request_id="req-backfill-1",
        user_message="我想开始准备计网考试。",
        request_extra_context={"informational_tensions": [{"domain": "scope", "status": "open"}]},
        conversation_context={},
        user_context_payload={},
    )

    second_service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(
            llm_factory=lambda: _FakeJsonLLM(
                {
                    "action": "emit_message",
                    "chat_directive": {"intent": "ask_baseline", "target_domain": "baseline"},
                    "harness_updates": {"strategy": _strategy(retrieval_practice=True)},
                }
            )
        ),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["你目前基础大概怎么样？"]})),
    )

    await second_service.plan_turn(
        active_db=db_session,
        user_id=str(test_user.id),
        surface="aurora_modeling",
        conversation_id="conv-telemetry-backfill",
        request_id="req-backfill-2",
        user_message="考试范围主要是传输层和网络层。",
        request_extra_context={"informational_tensions": [{"domain": "baseline", "status": "open"}]},
        conversation_context={},
        user_context_payload={},
    )

    rows = list(
        (
            await db_session.execute(
                select(AuroraDecisionTelemetry)
                .where(AuroraDecisionTelemetry.conversation_id == "conv-telemetry-backfill")
                .order_by(AuroraDecisionTelemetry.decided_at.asc(), AuroraDecisionTelemetry.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 2
    assert rows[0].outcome == "task_completed"
    assert rows[0].outcome_reason == "user_supplied_scope_signal"
    assert rows[0].outcome_filled_at is not None
    assert rows[1].outcome is None
