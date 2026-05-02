from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.aurora.correction_types import AuroraCorrectionPayload
from app.aurora.core_session import AuroraCoreSessionService
from app.aurora.runtime_v1.correction_feedback import CorrectionFeedbackProcessor
from app.models.base import _utcnow
from app.models.aurora_stage20 import RoutingDecisionLog
from app.models.intervention_adaptive import BehavioralOutcome, PassiveSignal, ScaffoldingState
from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput
from app.services.route_history_service import RouteHistoryService
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


def _base_routing_input(**overrides) -> DualCoreRoutingInput:
    defaults = {
        "intent": "task",
        "intent_confidence": 0.88,
        "information_sufficient": True,
        "primary_challenge_area": None,
        "recent_sentiment_distribution": {},
        "has_active_plan": True,
        "plan_health_status": "on_track",
        "recent_task_feedback_distribution": {},
    }
    defaults.update(overrides)
    return DualCoreRoutingInput(**defaults)


def test_recent_route_failures_change_next_dual_core_decision() -> None:
    router = DualCoreRouter()

    baseline = router.route(_base_routing_input())
    adapted = router.route(
        _base_routing_input(
            recent_route_outcomes=[
                {"mode": "execution_first", "outcome": "user_correction"},
                {"mode": "execution_first", "outcome": "timeout"},
                {"mode": "cognitive_first", "outcome": "task_completion"},
            ]
        )
    )

    assert baseline.mode == "execution_first"
    assert adapted.mode == "cognitive_first"
    assert adapted.signal_scores["route_outcome_failure"] > 0
    assert adapted.routing_debug["dominant_signal"] == "route_outcome_failure"
    assert adapted.routing_debug["recent_route_outcome_summary"]["support_needed"] is True


@pytest.mark.asyncio
async def test_correction_feedback_backfills_route_history_and_sgw(db_session, test_user) -> None:
    decision_id = await RouteHistoryService(db_session).record_decision(
        user_id=test_user.id,
        input_aggregator_snapshot_id="aggregator:user-cxp4:snap-1",
        decision_type="execution_first",
        decision_payload={
            "mode": "execution_first",
            "reason": "goal clear",
            "signal_scores": {"goal_clarity": 0.9},
            "routing_debug": {"dominant_signal": "goal_clarity"},
        },
        skills_injected=[],
    )
    signal = await RoutingOutcomeRecorder(db_session).record(
        user_id=test_user.id,
        decision={
            "mode": "execution_first",
            "reason": "goal clear",
            "routing_trace_id": "dcr_cxp4",
            "signal_scores": {"goal_clarity": 0.9},
            "routing_debug": {"dominant_signal": "goal_clarity"},
            "cognitive_adjustments": [],
            "execution_constraints": [],
        },
        route_execution_mode="direct",
        request_id="req-cxp4",
        session_id="sess-cxp4",
        route_history_decision_id=str(decision_id),
    )

    @asynccontextmanager
    async def _db_session():
        yield db_session

    payload = AuroraCorrectionPayload.normalize(
        {
            "surface": "chat",
            "source": "predicted_chip",
            "semantic_value": "strategy_too_aggressive",
            "label": "太急了",
            "is_disconfirming": True,
            "telemetry_id": "telemetry-cxp4",
            "route_history_decision_id": str(decision_id),
            "routing_outcome_signal_id": str(signal.id),
            "routing_trace_id": "dcr_cxp4",
        }
    )
    result = await CorrectionFeedbackProcessor(_RedisDict(), _db_session).process(
        user_id=str(test_user.id),
        correction_payload=payload,
    )

    assert result.routing_feedback_recorded is True
    stored = (
        await db_session.execute(select(RoutingDecisionLog).where(RoutingDecisionLog.decision_id == decision_id))
    ).scalar_one()
    assert stored.outcome == "user_correction"
    assert stored.outcome_signal_id == "telemetry-cxp4"

    stored_signal = (await db_session.execute(select(PassiveSignal).where(PassiveSignal.id == signal.id))).scalar_one()
    assert stored_signal.context["outcome_recorded"] is True
    assert stored_signal.context["outcome_success"] is False
    state = (await db_session.execute(select(ScaffoldingState))).scalar_one()
    assert state.history[-1]["feedback"] == "explicit_user_correction_after_routing"


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
