"""V3-FIX-11 T3 red/green: the state aggregator's emotion_hint must not count
telemetry-derived fragment sentiment.

D-01 R2 evidence (F3): ``state_aggregator/service.py`` reads
``cognitive_fragments.sentiment`` (24h window) into UserStateV1's emotion_hint;
``cognitive_stream_worker`` writes telemetry payloads into that column with
``source_type='behavior'``, and the seed service fills the same channel.
Behavior-source sentiment is client-asserted, so the aggregator must filter it
(user-authored capsule / interceptor fragments and the server-side chat
classifier remain legitimate channels).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.chat import ChatMessage
from app.models.cognitive import CognitiveFragment
from app.state_aggregator.service import StateAggregatorService


def _fragment(
    user_id,
    sentiment: str,
    source_type: str = "behavior",
    created_at: datetime | None = None,
) -> CognitiveFragment:
    return CognitiveFragment(
        user_id=user_id,
        source_type=source_type,
        resource_type="event" if source_type == "behavior" else "text",
        content="fragment",
        sentiment=sentiment,
        tags=[],
        severity=1,
        created_at=created_at or datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_behavior_fragment_sentiment_cannot_trip_emotional_block(db_session):
    """frustrated telemetry fragments alone must NOT trigger emotional_block.

    RED pre-fix: dominant='frustrated' -> emotional_block_detected=True.
    """
    user_id = uuid4()
    now = datetime.utcnow()
    for i in range(5):
        db_session.add(_fragment(user_id, "frustrated", source_type="behavior", created_at=now - timedelta(minutes=i)))
    await db_session.commit()

    service = StateAggregatorService(db_session)
    envelope = await service._build_emotion_hint_summary(user_id, now)

    assert envelope.value.emotional_block_detected is False, (
        "telemetry-derived (behavior-source) sentiment reached the aggregator's "
        "emotional_block trigger (T3 second hop)"
    )
    assert "frustrated" not in (envelope.value.sentiment_distribution or {})


@pytest.mark.asyncio
async def test_overwhelmed_behavior_fragment_sentiment_ignored(db_session):
    user_id = uuid4()
    now = datetime.utcnow()
    db_session.add(_fragment(user_id, "overwhelmed", created_at=now))
    await db_session.commit()

    service = StateAggregatorService(db_session)
    envelope = await service._build_emotion_hint_summary(user_id, now)

    assert envelope.value.emotional_block_detected is False


@pytest.mark.asyncio
async def test_capsule_fragment_sentiment_still_counts(db_session):
    """User-authored capsule sentiment (self-report, not telemetry) keeps its
    voice — including a negative one."""
    user_id = uuid4()
    now = datetime.utcnow()
    for i in range(3):
        db_session.add(_fragment(user_id, "frustrated", source_type="capsule", created_at=now - timedelta(minutes=i)))
    await db_session.commit()

    service = StateAggregatorService(db_session)
    envelope = await service._build_emotion_hint_summary(user_id, now)

    assert envelope.value.dominant_sentiment == "frustrated"
    assert envelope.value.emotional_block_detected is True


@pytest.mark.asyncio
async def test_chat_derived_frustration_still_trips_block(db_session):
    """The server-side chat classifier (user's own words) is a legitimate
    channel and must keep triggering emotional_block."""
    user_id = uuid4()
    now = datetime.utcnow()
    db_session.add(
        ChatMessage(
            id=uuid4(),
            session_id=uuid4(),
            user_id=user_id,
            role="user",
            content="太难了，做不到，烦死了",
            created_at=now - timedelta(minutes=5),
        )
    )
    # telemetry noise must not be able to bury the real signal either
    db_session.add(_fragment(user_id, "happy", source_type="behavior", created_at=now))
    await db_session.commit()

    service = StateAggregatorService(db_session)
    envelope = await service._build_emotion_hint_summary(user_id, now)

    assert envelope.value.dominant_sentiment == "frustrated"
    assert envelope.value.emotional_block_detected is True
