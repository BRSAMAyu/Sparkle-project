from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.aurora_stage20 import RoutingDecisionLog
from app.models.user import User
from app.services.route_history_service import RouteHistoryService


async def _create_user(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_route_history_records_and_backfills_by_decision_id(db_session):
    user = await _create_user(db_session)
    service = RouteHistoryService(db_session)

    decision_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="aggregator:user-1:snap-1",
        decision_type="cognitive_first",
        decision_payload={"mode": "cognitive_first", "reason": "need clarification"},
        decided_at=datetime(2026, 4, 21, 12, 0, 0),
    )
    updated = await service.record_follow_up_input(
        decision_id=decision_id,
        outcome_signal_id="turn:follow-up",
        collected_at=datetime(2026, 4, 21, 12, 3, 0),
    )

    assert updated is not None
    assert updated.outcome_type == "implicit_follow_up"
    stored = (
        await db_session.execute(
            select(RoutingDecisionLog).where(RoutingDecisionLog.decision_id == decision_id)
        )
    ).scalar_one()
    assert stored.outcome_signal_id == "turn:follow-up"
    assert stored.input_aggregator_snapshot_id == "aggregator:user-1:snap-1"


@pytest.mark.asyncio
async def test_route_history_records_explicit_feedback_and_timeout(db_session):
    user = await _create_user(db_session)
    service = RouteHistoryService(db_session)

    thumbs_up_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="aggregator:user-2:snap-1",
        decision_type="execution_first",
        decision_payload={"mode": "execution_first"},
    )
    timeout_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="aggregator:user-2:snap-2",
        decision_type="follow_up_question",
        decision_payload={"question": "你最想推进什么？"},
    )

    thumbs_up = await service.record_explicit_feedback(
        decision_id=thumbs_up_id,
        outcome_signal_id="feedback:1",
        positive=True,
    )
    timeout = await service.mark_timeout(decision_id=timeout_id)

    assert thumbs_up is not None
    assert thumbs_up.outcome_type == "thumbs_up"
    assert timeout is not None
    assert timeout.outcome_type == "timeout"
