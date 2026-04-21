from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.chat import ChatSession
from app.state_aggregator.service import StateAggregatorService
from app.working_memory.service import WorkingMemoryService


@pytest.mark.asyncio
async def test_state_aggregator_returns_working_memory_snapshot(db_session) -> None:
    user_id = uuid4()
    session_id = uuid4()
    now = datetime.utcnow()
    db_session.add(
        ChatSession(
            id=session_id,
            user_id=user_id,
            is_active=True,
            last_message_at=now,
        )
    )
    await db_session.commit()

    wm = WorkingMemoryService()
    await wm.upsert_entry(
        user_id=str(user_id),
        session_id=str(session_id),
        text="准备本周末补完高数真题",
        semantic_key="commitment:math",
        salience_score=0.9,
        subject_type="commitment",
        confidence=0.91,
        evidence_token="turn-1",
        occurred_at=now,
        source_turn_id="turn-1",
        due_at=now + timedelta(days=2),
    )

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("working_memory_snapshot",),
        now=now,
    )

    assert state.schema_version == "user_state.v1.10"
    assert state.working_memory_snapshot is not None
    assert state.working_memory_snapshot.value.active_session_id == str(session_id)
    assert len(state.working_memory_snapshot.value.items) == 1
    assert state.working_memory_snapshot.value.items[0].subject_type == "commitment"
