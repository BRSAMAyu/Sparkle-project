from datetime import datetime
from uuid import uuid4

import pytest

from app.models.memory import EpisodicMemory
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_social_kill_switch_can_target_subject_type_only(db_session):
    user_id = uuid4()
    person_record = EpisodicMemory(
        user_id=user_id,
        summary="你提到过一位学习相关人物",
        source_type="chat",
        source_id="session_1",
        source_lane="inferred_extraction",
        subject_type="person_mention",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        evidence_refs=[{"type": "chat_turn", "id": "turn_person"}],
    )
    commitment_record = EpisodicMemory(
        user_id=user_id,
        summary="我明天要把提纲补完",
        source_type="chat",
        source_id="session_1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=datetime(2026, 4, 21, 18, 0, 0),
        evidence_refs=[{"type": "chat_turn", "id": "turn_commitment"}],
    )
    db_session.add_all([person_record, commitment_record])
    await db_session.commit()

    revoked = await MemoryService(db_session).revoke_inferred_memories(
        user_id=user_id,
        reason="stage17_social_kill",
        subject_types=["person_mention"],
    )

    await db_session.refresh(person_record)
    await db_session.refresh(commitment_record)
    assert revoked == 1
    assert person_record.revoked_at is not None
    assert commitment_record.revoked_at is None
