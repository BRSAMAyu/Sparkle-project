from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.services.route_history_service import RouteHistoryService
from app.models.user import User
from app.services.task_reflection_service import TaskReflectionService


async def _create_user(db_session, suffix: str) -> User:
    user = User(
        id=uuid4(),
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_build_reflection_context_includes_rule_y_evidence_markers(db_session) -> None:
    user = await _create_user(db_session, "ctx_markers")
    service = TaskReflectionService(db_session)
    now = datetime(2026, 4, 21, 12, 0, 0)

    history = RouteHistoryService(db_session)
    await history.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:1",
        decision_type="execution_first",
        decision_payload={"route_execution_mode": "execution_first"},
        decided_at=now,
    )

    context = await service._build_reflection_context(
        user_id=user.id,
        trigger="plan_stall",
        trigger_payload={"window_days": 7},
    )

    assert "source=route_history" in context["route_history_context"]
    assert "user_correction_eligible=true" in context["route_history_context"]
    assert context["route_history_context_tokens"] <= 800


@pytest.mark.asyncio
async def test_build_reflection_context_respects_token_budget(db_session, monkeypatch) -> None:
    user = await _create_user(db_session, "ctx_budget")
    service = TaskReflectionService(db_session)
    monkeypatch.setattr(settings, "AURORA_REFLECTION_CONTEXT_MAX_TOKENS", 24)
    history = RouteHistoryService(db_session)

    for index in range(5):
        await history.record_decision(
            user_id=user.id,
            input_aggregator_snapshot_id=f"agg:{index}",
            decision_type=f"decision_{index}",
            decision_payload={"route_execution_mode": "execution_first", "note": "x" * 60},
            decided_at=datetime(2026, 4, 21, 12, index, 0),
        )

    context = await service._build_reflection_context(
        user_id=user.id,
        trigger="overload",
        trigger_payload={},
    )

    assert context["route_history_context_truncated"] is True
    assert context["route_history_context_tokens"] <= 24


@pytest.mark.asyncio
async def test_build_reflection_context_uses_decision_chain_when_present(db_session) -> None:
    user = await _create_user(db_session, "ctx_chain")
    service = TaskReflectionService(db_session)
    history = RouteHistoryService(db_session)

    root_id = await history.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:root",
        decision_type="root",
        decision_payload={"route_execution_mode": "execution_first"},
    )
    await history.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:child",
        decision_type="child",
        decision_payload={"route_execution_mode": "execution_first", "parent_decision_id": str(root_id)},
    )

    context = await service._build_reflection_context(
        user_id=user.id,
        trigger="plan_stall",
        trigger_payload={"decision_id": str(root_id)},
    )

    assert "decision=child" in context["route_history_context"]


@pytest.mark.asyncio
async def test_build_reflection_context_is_user_isolated(db_session) -> None:
    owner = await _create_user(db_session, "ctx_owner")
    other = await _create_user(db_session, "ctx_other")
    service = TaskReflectionService(db_session)
    history = RouteHistoryService(db_session)

    await history.record_decision(
        user_id=owner.id,
        input_aggregator_snapshot_id="agg:owner",
        decision_type="owner_decision",
        decision_payload={"route_execution_mode": "execution_first"},
    )
    await history.record_decision(
        user_id=other.id,
        input_aggregator_snapshot_id="agg:other",
        decision_type="other_decision",
        decision_payload={"route_execution_mode": "execution_first"},
    )

    context = await service._build_reflection_context(
        user_id=owner.id,
        trigger="plan_stall",
        trigger_payload={},
    )

    assert "decision=owner_decision" in context["route_history_context"]
    assert "decision=other_decision" not in context["route_history_context"]


@pytest.mark.asyncio
async def test_build_reflection_context_returns_fallback_when_empty(db_session) -> None:
    user = await _create_user(db_session, "ctx_empty")
    service = TaskReflectionService(db_session)

    context = await service._build_reflection_context(
        user_id=user.id,
        trigger="overload",
        trigger_payload={},
    )

    assert "no recent decisions found" in context["route_history_context"]
    assert context["route_history_context_tokens"] > 0


@pytest.mark.asyncio
async def test_build_reflection_context_caps_recent_decisions_to_twenty(db_session, monkeypatch) -> None:
    user = await _create_user(db_session, "ctx_limit")
    service = TaskReflectionService(db_session)
    monkeypatch.setattr(settings, "AURORA_REFLECTION_CONTEXT_MAX_TOKENS", 2000)
    history = RouteHistoryService(db_session)

    for index in range(30):
        await history.record_decision(
            user_id=user.id,
            input_aggregator_snapshot_id=f"agg:{index}",
            decision_type=f"d{index}",
            decision_payload={"route_execution_mode": "execution_first"},
            decided_at=datetime(2026, 4, 21, 12, 0, 0) + timedelta(minutes=index),
        )

    context = await service._build_reflection_context(
        user_id=user.id,
        trigger="plan_stall",
        trigger_payload={},
    )

    assert context["route_history_context_entry_count"] <= 20
