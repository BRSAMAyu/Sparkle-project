from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.aurora.core_session import AuroraCoreSessionService
from app.models.base import _utcnow
from app.models.intervention_adaptive import BehavioralOutcome, ScaffoldingState
from app.services.routing_outcome_service import RoutingOutcomeEvaluator, RoutingOutcomeRecorder


class _RedisDict:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.data:
                self.data.pop(key, None)
                removed += 1
        return removed


@pytest.mark.asyncio
async def test_routing_decision_records_passive_signal_and_sgw_outcome(db_session, test_user) -> None:
    signal = await RoutingOutcomeRecorder(db_session).record(
        user_id=test_user.id,
        decision={
            "mode": "cognitive_first",
            "reason": "emotional support first",
            "routing_trace_id": "dcr_test",
            "signal_scores": {"emotional_block": 0.8, "goal_clarity": 0.2},
            "routing_debug": {"dominant_signal": "emotional_block"},
            "scaffolding_zone": "frustration",
            "cognitive_adjustments": ["support"],
            "execution_constraints": [],
        },
        route_execution_mode="direct",
        source_state_key="state:test",
        request_id="req-1",
        session_id="sess-1",
    )

    assert signal.signal_type == "routing_decision"
    assert signal.context["routing_trace_id"] == "dcr_test"
    assert signal.intervention_id is not None

    signal.timestamp = _utcnow() - timedelta(hours=49)
    signal.context = {**signal.context, "evaluation_due_at": (_utcnow() - timedelta(minutes=1)).isoformat()}
    flag_modified(signal, "context")
    await db_session.flush()

    evaluated = await RoutingOutcomeEvaluator(db_session).evaluate_due()

    assert evaluated == 1
    outcome = (
        await db_session.execute(
            select(BehavioralOutcome).where(BehavioralOutcome.outcome_type == "routing_effectiveness")
        )
    ).scalar_one()
    assert outcome.success is True
    state = (await db_session.execute(select(ScaffoldingState))).scalar_one()
    assert state.history[-1]["feedback"] == "cognitive_first_matched_emotional_block"


@pytest.mark.asyncio
async def test_core_session_case_file_agenda_survive_redis_miss(db_session) -> None:
    redis = _RedisDict()
    service = AuroraCoreSessionService(redis, db=db_session)
    supplied_case_file = {
        "goal_summary": "两周内通过考试",
        "recent_user_corrections": [{"semantic_value": "content_too_hard"}],
        "conflicts_to_resolve": ["用户说没时间，但自由纠正表明是不会做"],
        "source_receipt": {"sources": ["status_band", "chat_correction"]},
    }

    session = await service.start_session(
        user_id="user-aurora",
        conversation_id="conv-1",
        scope="考试冲刺策略",
        wake_reasons=["state_conflict"],
        case_file=supplied_case_file,
    )

    assert session.case_file["goal_summary"] == "两周内通过考试"
    assert session.case_file["recent_user_corrections"][0]["semantic_value"] == "content_too_hard"
    assert session.to_dict()["agenda"]["items"][-1]["id"] == "close_session"

    redis.data.clear()
    recovered = await service.get_session(session.session_id)

    assert recovered is not None
    assert recovered.case_file["conflicts_to_resolve"] == ["用户说没时间，但自由纠正表明是不会做"]
    assert recovered.to_dict()["agenda"]["interruption_policy"] == "answer_then_resume"
