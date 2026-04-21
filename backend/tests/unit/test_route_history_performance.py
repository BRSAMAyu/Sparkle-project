import time
from uuid import uuid4

import pytest

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
async def test_route_history_average_write_stays_under_five_ms(db_session):
    user = await _create_user(db_session)
    service = RouteHistoryService(db_session)

    samples = 1000
    started_at = time.perf_counter()
    for index in range(samples):
        await service.record_decision(
            user_id=user.id,
            input_aggregator_snapshot_id=f"aggregator:{index}",
            decision_type="balanced",
            decision_payload={"sample": index},
        )
    elapsed = time.perf_counter() - started_at
    average_ms = (elapsed / samples) * 1000

    assert average_ms < 5.0
