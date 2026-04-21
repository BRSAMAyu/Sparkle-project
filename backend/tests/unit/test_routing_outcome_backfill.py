from __future__ import annotations

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
async def test_routing_outcome_backfill_writes_stage23_columns(db_session, monkeypatch) -> None:
    user = await _create_user(db_session)
    service = RouteHistoryService(db_session)
    monkeypatch.setattr("app.services.route_history_service.cache_service.redis", None)

    decision_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="aggregator:u1:s1",
        decision_type="balanced",
        decision_payload={"route_execution_mode": "direct", "route_reason": "chat"},
        skills_injected=[],
        source_state_v2={"tool_category": "chat"},
        source_state_v2_key="tool_category=chat|sufficiency_level=medium|conflict_outcome=clear|skill_domain=none|achievement_tier=none|calendar_pressure=none|cohort_segment=general",
    )

    updated = await service.record_plan_success(
        decision_id=decision_id,
        outcome_signal_id="outcome:1",
        collected_at=datetime(2026, 4, 21, 14, 30, 0),
    )

    assert updated is not None
    assert updated.outcome == "plan_success"
    assert updated.outcome_timestamp == datetime(2026, 4, 21, 14, 30, 0)

    stored = (
        await db_session.execute(select(RoutingDecisionLog).where(RoutingDecisionLog.decision_id == decision_id))
    ).scalar_one()
    assert stored.outcome == "plan_success"
    assert stored.outcome_type == "plan_success"


@pytest.mark.asyncio
async def test_routing_outcome_backfill_preserves_legacy_columns(db_session, monkeypatch) -> None:
    user = await _create_user(db_session)
    service = RouteHistoryService(db_session)
    monkeypatch.setattr("app.services.route_history_service.cache_service.redis", None)

    decision_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="aggregator:u2:s1",
        decision_type="balanced",
        decision_payload={"route_execution_mode": "langgraph", "route_reason": "plan"},
        skills_injected=[],
    )

    updated = await service.record_user_correction(
        decision_id=decision_id,
        outcome_signal_id="feedback:down",
    )

    assert updated is not None
    assert updated.outcome == "user_correction"
    assert updated.outcome_collected_at is not None
    assert updated.outcome_type == "user_correction"
