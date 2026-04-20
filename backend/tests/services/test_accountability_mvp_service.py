from datetime import datetime
from uuid import uuid4

import pytest

from app.models.memory import EpisodicMemory
from app.services.accountability_mvp_service import AccountabilityMvpService


@pytest.mark.asyncio
async def test_accountability_mvp_service_only_returns_overdue_unresolved_commitments(db_session):
    user_id = uuid4()
    db_session.add_all(
        [
            EpisodicMemory(
                user_id=user_id,
                summary="overdue",
                source_type="chat",
                source_id="session_1",
                source_lane="inferred_extraction",
                subject_type="commitment",
                occurred_at=datetime(2026, 4, 19, 9, 0, 0),
                due_at=datetime(2026, 4, 20, 9, 0, 0),
                evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
            ),
            EpisodicMemory(
                user_id=user_id,
                summary="future",
                source_type="chat",
                source_id="session_1",
                source_lane="inferred_extraction",
                subject_type="commitment",
                occurred_at=datetime(2026, 4, 20, 9, 0, 0),
                due_at=datetime(2026, 4, 22, 9, 0, 0),
                evidence_refs=[{"type": "chat_turn", "id": "turn_2"}],
            ),
            EpisodicMemory(
                user_id=user_id,
                summary="resolved",
                source_type="chat",
                source_id="session_1",
                source_lane="inferred_extraction",
                subject_type="commitment",
                occurred_at=datetime(2026, 4, 19, 9, 0, 0),
                due_at=datetime(2026, 4, 20, 9, 0, 0),
                resolved_at=datetime(2026, 4, 20, 12, 0, 0),
                evidence_refs=[{"type": "chat_turn", "id": "turn_3"}],
            ),
        ]
    )
    await db_session.commit()

    service = AccountabilityMvpService(db_session)
    items = await service.list_pending_commitments(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert [item.summary for item in items] == ["overdue"]


@pytest.mark.asyncio
async def test_accountability_mvp_service_can_resolve_commitment(db_session):
    user_id = uuid4()
    record = EpisodicMemory(
        user_id=user_id,
        summary="resolve me",
        source_type="chat",
        source_id="session_2",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=datetime(2026, 4, 20, 18, 0, 0),
        evidence_refs=[{"type": "chat_turn", "id": "turn_4"}],
    )
    db_session.add(record)
    await db_session.commit()

    service = AccountabilityMvpService(db_session)
    resolved = await service.resolve_commitment(user_id=user_id, memory_id=record.id)

    assert resolved is not None
    assert resolved.resolved_at is not None
