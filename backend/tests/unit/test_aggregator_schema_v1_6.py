from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.api.v1.accountability import _build_recent_reflections_summary
from app.models.memory import EpisodicMemory
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_aggregator_schema_v1_6_reports_recent_reflections(db_session) -> None:
    user_id = uuid4()
    now = datetime.utcnow()
    db_session.add(
        EpisodicMemory(
            user_id=user_id,
            summary="最近一段时间计划推进反复停住。",
            source_type="reflection",
            source_id="reflection-1",
            source_lane="inferred_extraction",
            subject_type="self",
            occurred_at=now,
            tags=["stage25:reflection", "reflection_category:plan_stall"],
            evidence_refs=[{"type": "summary", "id": "reflection-1"}],
        )
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("recent_reflections",),
    )

    assert state.schema_version == "user_state.v1.10"
    assert state.recent_reflections is not None
    assert state.recent_reflections.value.last_category == "plan_stall"


@pytest.mark.asyncio
async def test_accountability_summary_uses_recent_reflections_field(db_session) -> None:
    user_id = uuid4()
    now = datetime.utcnow()
    db_session.add(
        EpisodicMemory(
            user_id=user_id,
            summary="同一天连续失败说明当前负荷已经溢出。",
            source_type="reflection",
            source_id="reflection-2",
            source_lane="inferred_extraction",
            subject_type="self",
            occurred_at=now,
            tags=["stage25:reflection", "reflection_category:overload"],
            evidence_refs=[{"type": "summary", "id": "reflection-2"}],
        )
    )
    await db_session.commit()

    payload = await _build_recent_reflections_summary(db_session, user_id=user_id)

    assert payload["count"] == 1
    assert payload["last_category"] == "overload"
    assert payload["last_at"] is not None


@pytest.mark.asyncio
async def test_recent_reflections_summary_ignores_stale_records(db_session) -> None:
    user_id = uuid4()
    stale_time = datetime.utcnow() - timedelta(days=10)
    db_session.add(
        EpisodicMemory(
            user_id=user_id,
            summary="过旧反思",
            source_type="reflection",
            source_id="reflection-old",
            source_lane="inferred_extraction",
            subject_type="self",
            occurred_at=stale_time,
            tags=["stage25:reflection", "reflection_category:plan_stall"],
            evidence_refs=[{"type": "summary", "id": "reflection-old"}],
        )
    )
    await db_session.commit()

    payload = await _build_recent_reflections_summary(db_session, user_id=user_id)

    assert payload == {"count": 0, "last_category": None, "last_at": None}
