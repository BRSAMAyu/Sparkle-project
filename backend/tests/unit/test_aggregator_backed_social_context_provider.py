from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.memory import EpisodicMemory
from app.routing.aggregator_backed_social_context_provider import AggregatorBackedSocialContextProvider
from app.routing.router_context_reader import RouterContextReader


def _scenario_payload(now: datetime, index: int) -> list[EpisodicMemory]:
    user_id = uuid4()
    records: list[EpisodicMemory] = []
    mention_count = (index % 3) + 1
    relationship_count = index % 4
    overdue_commitments = index % 2

    for offset in range(mention_count):
        records.append(
            EpisodicMemory(
                user_id=user_id,
                summary=f"你提到过一位学习相关人物 {index}-{offset}",
                source_type="chat",
                source_id=f"session_{index}",
                source_lane="inferred_extraction",
                subject_type="person_mention",
                occurred_at=now - timedelta(days=offset + 1),
                evidence_refs=[{"type": "chat_turn", "id": f"turn_m_{index}_{offset}"}],
            )
        )
    for offset in range(relationship_count):
        records.append(
            EpisodicMemory(
                user_id=user_id,
                summary=f"你提到过一段与他人的关系动态 {index}-{offset}",
                source_type="chat",
                source_id=f"session_{index}",
                source_lane="inferred_extraction",
                subject_type="relationship",
                occurred_at=now - timedelta(days=offset + 1),
                evidence_refs=[{"type": "chat_turn", "id": f"turn_r_{index}_{offset}"}],
            )
        )
    for offset in range(overdue_commitments):
        records.append(
            EpisodicMemory(
                user_id=user_id,
                summary=f"overdue commitment {index}-{offset}",
                source_type="chat",
                source_id=f"session_{index}",
                source_lane="inferred_extraction",
                subject_type="commitment",
                occurred_at=now - timedelta(days=offset + 2),
                due_at=now - timedelta(hours=offset + 2),
                evidence_refs=[{"type": "chat_turn", "id": f"turn_c_{index}_{offset}"}],
            )
        )
    return records


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_index", list(range(20)))
async def test_aggregator_backed_social_context_provider_matches_direct_reader(
    db_session,
    scenario_index: int,
) -> None:
    now = datetime.utcnow()
    records = _scenario_payload(now, scenario_index)
    user_id = records[0].user_id
    db_session.add_all(records)
    await db_session.commit()

    direct = await RouterContextReader(db_session).fetch_social_snapshot(user_id)
    aggregated = await AggregatorBackedSocialContextProvider(db_session).fetch_social_snapshot(user_id)

    assert [item.summary for item in aggregated.recent_person_mentions] == [
        item.summary for item in direct.recent_person_mentions
    ]
    assert aggregated.pending_commitments_count == direct.pending_commitments_count
    assert aggregated.relationship_count == direct.relationship_count
