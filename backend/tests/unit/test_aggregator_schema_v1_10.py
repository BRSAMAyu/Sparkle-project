from __future__ import annotations

from datetime import datetime

import pytest

from app.models.srl_phase_state import SRLPhaseStateRecord
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_aggregator_schema_v1_10_exposes_srl_phase(db_session, test_user) -> None:
    db_session.add(
        SRLPhaseStateRecord(
            user_id=test_user.id,
            current_phase="PERFORMANCE",
            phase_started_at=datetime(2026, 4, 21, 10, 0, 0),
            previous_phase="FORETHOUGHT",
            transition_evidence_ids=["task-1"],
            confidence=0.82,
            source="event_triggered",
        )
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(test_user.id, required_fields=("srl_phase",))

    assert state.schema_version == "user_state.v1.13"
    assert state.srl_phase is not None
    assert state.srl_phase.value.current_phase == "PERFORMANCE"


@pytest.mark.asyncio
async def test_aggregator_srl_phase_uses_fifteen_second_ttl(db_session, test_user) -> None:
    state = await StateAggregatorService(db_session).get_user_state(test_user.id, required_fields=("srl_phase",))
    assert state.srl_phase is not None
    assert StateAggregatorService.FIELD_TTLS_SECONDS["srl_phase"] == 15


@pytest.mark.asyncio
async def test_aggregator_srl_phase_defaults_to_unknown(db_session, test_user) -> None:
    state = await StateAggregatorService(db_session).get_user_state(test_user.id, required_fields=("srl_phase",))
    assert state.srl_phase is not None
    assert state.srl_phase.value.current_phase == "UNKNOWN"
