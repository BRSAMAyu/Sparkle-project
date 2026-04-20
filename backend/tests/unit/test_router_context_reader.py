from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.memory import EpisodicMemory
from app.routing.router_context_reader import RouterContextReader


@pytest.mark.asyncio
async def test_router_context_reader_builds_bounded_snapshot(db_session):
    user_id = uuid4()
    now = datetime.utcnow()

    rows = [
        EpisodicMemory(
            user_id=user_id,
            summary="你提到过一位学习相关人物",
            source_type="chat",
            source_id="session_1",
            source_lane="inferred_extraction",
            subject_type="person_mention",
            occurred_at=now - timedelta(days=1),
            evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
        ),
        EpisodicMemory(
            user_id=user_id,
            summary="你提到过一位学习相关人物",
            source_type="chat",
            source_id="session_1",
            source_lane="inferred_extraction",
            subject_type="person_mention",
            occurred_at=now - timedelta(days=2),
            evidence_refs=[{"type": "chat_turn", "id": "turn_2"}],
        ),
        EpisodicMemory(
            user_id=user_id,
            summary="你提到过一位学习相关人物",
            source_type="chat",
            source_id="session_1",
            source_lane="inferred_extraction",
            subject_type="person_mention",
            occurred_at=now - timedelta(days=3),
            evidence_refs=[{"type": "chat_turn", "id": "turn_3"}],
        ),
        EpisodicMemory(
            user_id=user_id,
            summary="你提到过一段与他人的关系动态",
            source_type="chat",
            source_id="session_1",
            source_lane="inferred_extraction",
            subject_type="relationship",
            occurred_at=now - timedelta(days=1),
            evidence_refs=[{"type": "chat_turn", "id": "turn_4"}],
        ),
        EpisodicMemory(
            user_id=user_id,
            summary="overdue commitment",
            source_type="chat",
            source_id="session_1",
            source_lane="inferred_extraction",
            subject_type="commitment",
            occurred_at=now - timedelta(days=2),
            due_at=now - timedelta(hours=2),
            evidence_refs=[{"type": "chat_turn", "id": "turn_5"}],
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    snapshot = await RouterContextReader(db_session).fetch_social_snapshot(user_id)

    assert len(snapshot.recent_person_mentions) == 3
    assert snapshot.pending_commitments_count == 1
    assert snapshot.relationship_count == 1
