from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.route_history_service import RouteHistoryService


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
async def test_read_recent_decisions_requires_user_id(db_session) -> None:
    service = RouteHistoryService(db_session)

    with pytest.raises(ValueError):
        await service.read_recent_decisions(user_id=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_read_recent_decisions_returns_user_scoped_history(db_session) -> None:
    user = await _create_user(db_session, "history")
    other = await _create_user(db_session, "other")
    service = RouteHistoryService(db_session)
    now = datetime(2026, 4, 21, 12, 0, 0)

    await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:user:1",
        decision_type="clarify",
        decision_payload={"route_execution_mode": "clarify"},
        decided_at=now - timedelta(minutes=5),
    )
    latest = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:user:2",
        decision_type="execution_first",
        decision_payload={"route_execution_mode": "execution_first"},
        decided_at=now,
    )
    await service.record_decision(
        user_id=other.id,
        input_aggregator_snapshot_id="agg:other:1",
        decision_type="other",
        decision_payload={"route_execution_mode": "other"},
        decided_at=now + timedelta(minutes=1),
    )
    await service.record_task_completion(decision_id=latest, outcome_signal_id="outcome:1")

    rows = await service.read_recent_decisions(user_id=user.id, limit=10)

    assert [row.decision_type for row in rows] == ["execution_first", "clarify"]
    assert all(row.user_id == str(user.id) for row in rows)


@pytest.mark.asyncio
async def test_read_recent_decisions_applies_outcome_filter(db_session) -> None:
    user = await _create_user(db_session, "filter")
    service = RouteHistoryService(db_session)

    success_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:1",
        decision_type="execution_first",
        decision_payload={"route_execution_mode": "execution_first"},
    )
    timeout_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:2",
        decision_type="follow_up_question",
        decision_payload={"route_execution_mode": "follow_up_question"},
    )
    await service.record_plan_success(decision_id=success_id, outcome_signal_id="success:1")
    await service.mark_timeout(decision_id=timeout_id)

    rows = await service.read_recent_decisions(
        user_id=user.id,
        outcome_filter="plan_success",
    )

    assert len(rows) == 1
    assert rows[0].outcome == "plan_success"


@pytest.mark.asyncio
async def test_read_decision_chain_follows_related_payload_ids(db_session) -> None:
    user = await _create_user(db_session, "chain")
    service = RouteHistoryService(db_session)
    root_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:root",
        decision_type="execution_first",
        decision_payload={"route_execution_mode": "execution_first"},
    )
    child_id = await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:child",
        decision_type="follow_up_question",
        decision_payload={
            "route_execution_mode": "follow_up_question",
            "parent_decision_id": str(root_id),
        },
    )
    await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:grandchild",
        decision_type="cognitive_first",
        decision_payload={
            "route_execution_mode": "cognitive_first",
            "previous_decision_id": str(child_id),
        },
    )

    rows = await service.read_decision_chain(user_id=user.id, decision_id=root_id, depth=3)

    assert len(rows) == 3
    assert [row.decision_id for row in rows[:2]] == [str(root_id), str(child_id)]
    assert rows[1].decision_payload["parent_decision_id"] == str(root_id)


@pytest.mark.asyncio
async def test_read_decision_chain_blocks_cross_user_access(db_session) -> None:
    owner = await _create_user(db_session, "owner")
    attacker = await _create_user(db_session, "attacker")
    service = RouteHistoryService(db_session)
    decision_id = await service.record_decision(
        user_id=owner.id,
        input_aggregator_snapshot_id="agg:secure",
        decision_type="execution_first",
        decision_payload={"route_execution_mode": "execution_first"},
    )

    rows = await service.read_decision_chain(user_id=attacker.id, decision_id=decision_id, depth=3)

    assert rows == []


@pytest.mark.asyncio
async def test_read_recent_decisions_respects_since_cutoff(db_session) -> None:
    user = await _create_user(db_session, "since")
    service = RouteHistoryService(db_session)
    now = datetime(2026, 4, 21, 12, 0, 0)
    await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:old",
        decision_type="old",
        decision_payload={"route_execution_mode": "old"},
        decided_at=now - timedelta(days=5),
    )
    await service.record_decision(
        user_id=user.id,
        input_aggregator_snapshot_id="agg:new",
        decision_type="new",
        decision_payload={"route_execution_mode": "new"},
        decided_at=now,
    )

    rows = await service.read_recent_decisions(
        user_id=user.id,
        since=now - timedelta(days=1),
    )

    assert [row.decision_type for row in rows] == ["new"]
