from uuid import uuid4

import pytest

from app.models.user import User
from app.services.route_history_service import RouteHistoryService
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
async def test_rule_aj_requires_user_id_for_recent_decisions(db_session) -> None:
    with pytest.raises(ValueError):
        await RouteHistoryService(db_session).read_recent_decisions(user_id=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_rule_aj_requires_user_id_for_decision_chain(db_session) -> None:
    with pytest.raises(ValueError):
        await RouteHistoryService(db_session).read_decision_chain(  # type: ignore[arg-type]
            user_id=None,
            decision_id=uuid4(),
            depth=2,
        )


@pytest.mark.asyncio
async def test_rule_aj_blocks_cross_user_decision_chain_reads(db_session) -> None:
    owner = await _create_user(db_session, "owner_rule_aj")
    other = await _create_user(db_session, "other_rule_aj")
    history = RouteHistoryService(db_session)
    decision_id = await history.record_decision(
        user_id=owner.id,
        input_aggregator_snapshot_id="agg:secure",
        decision_type="execution_first",
        decision_payload={"route_execution_mode": "execution_first"},
    )

    rows = await history.read_decision_chain(user_id=other.id, decision_id=decision_id, depth=3)

    assert rows == []


@pytest.mark.asyncio
async def test_rule_aj_reflection_context_builder_keeps_other_users_out(db_session) -> None:
    owner = await _create_user(db_session, "owner_ctx")
    other = await _create_user(db_session, "other_ctx")
    history = RouteHistoryService(db_session)
    await history.record_decision(
        user_id=owner.id,
        input_aggregator_snapshot_id="agg:owner",
        decision_type="owner_only",
        decision_payload={"route_execution_mode": "execution_first"},
    )
    await history.record_decision(
        user_id=other.id,
        input_aggregator_snapshot_id="agg:other",
        decision_type="other_only",
        decision_payload={"route_execution_mode": "execution_first"},
    )

    context = await TaskReflectionService(db_session)._build_reflection_context(
        user_id=owner.id,
        trigger="plan_stall",
        trigger_payload={},
    )

    assert "decision=owner_only" in context["route_history_context"]
    assert "decision=other_only" not in context["route_history_context"]
