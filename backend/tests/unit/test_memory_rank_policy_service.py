from uuid import uuid4

import pytest

from app.services.memory_rank_policy_service import MemoryRankPolicyService


@pytest.mark.asyncio
async def test_policy_resolver_precedence(db_session):
    service = MemoryRankPolicyService(db_session)
    user_id = uuid4()

    await service.upsert_policy(
        scope_type="global",
        scope_key=None,
        weights={"evidence": 0.2, "freshness": 0.7, "correction": 0.1},
    )
    await service.upsert_policy(
        scope_type="intent",
        scope_key="chat",
        weights={"evidence": 0.5},
    )
    await service.upsert_policy(
        scope_type="user",
        scope_key=str(user_id),
        weights={"freshness": 0.1, "correction": 0.2},
    )

    weights = await service.get_policy("chat", user_id)

    assert weights["evidence"] > weights["correction"] > weights["freshness"]
    assert sum(weights.values()) == pytest.approx(1.0, rel=1e-6)


@pytest.mark.asyncio
async def test_policy_weight_normalization(db_session):
    service = MemoryRankPolicyService(db_session)
    user_id = uuid4()

    await service.upsert_policy(
        scope_type="user",
        scope_key=str(user_id),
        weights={"evidence": 2.0, "freshness": -1.0, "correction": 0.0},
    )

    weights = await service.get_policy("chat", user_id)

    assert weights["evidence"] == pytest.approx(1.0, rel=1e-3)
    assert weights["freshness"] == pytest.approx(0.0, rel=1e-3)
    assert weights["correction"] == pytest.approx(0.0, rel=1e-3)
