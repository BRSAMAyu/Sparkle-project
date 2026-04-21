from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.config import settings
from app.models.memory import EpisodicMemory
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_user_state_v1_5_exposes_pending_policies_field(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    user_id = uuid4()
    db_session.add(
        EpisodicMemory(
            user_id=user_id,
            summary="准备周末复盘",
            source_type="chat",
            source_id="session-1",
            source_lane="inferred_extraction",
            subject_type="commitment",
            occurred_at=datetime(2026, 4, 20, 9, 0, 0),
            due_at=datetime(2026, 4, 24, 18, 0, 0),
            evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
        )
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("pending_policies",),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert state.schema_version == "user_state.v1.8"
    assert state.pending_policies is not None
    assert state.pending_policies.value.count >= 1


@pytest.mark.asyncio
async def test_pending_policies_summary_reports_next_trigger(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    user_id = uuid4()
    db_session.add(
        EpisodicMemory(
            user_id=user_id,
            summary="准备周末复盘",
            source_type="chat",
            source_id="session-1",
            source_lane="inferred_extraction",
            subject_type="commitment",
            occurred_at=datetime(2026, 4, 20, 9, 0, 0),
            due_at=datetime(2026, 4, 24, 18, 0, 0),
            evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
        )
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("pending_policies",),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert state.pending_policies is not None
    assert state.pending_policies.value.next_trigger_at == datetime(2026, 4, 21, 18, 0, 0)


def test_pending_policies_field_name_is_allowed() -> None:
    service_fields = StateAggregatorService.FIELD_TTLS_SECONDS

    assert "pending_policies" in service_fields
