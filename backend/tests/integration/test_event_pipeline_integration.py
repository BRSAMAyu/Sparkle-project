import json
import os
from datetime import timezone, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")
import redis.asyncio as redis
from sqlalchemy import delete

from app.config import settings
from app.core.redis_utils import resolve_redis_password
from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.event import TrackingEvent
from app.models.cognitive import CognitiveFragment
from app.models.user_state import UserStateSnapshot
from app.schemas.events import EvidenceResolveRequest
from app.schemas.intervention import EvidenceRef
from app.services.event_service import EventService
from app.services.state_estimator_service import StateEstimatorService
from app.services.analytics.cognitive_stream_worker import CognitiveStreamWorker
from app.api.v1 import events as events_api


def _integration_enabled() -> bool:
    return os.getenv("SPARKLE_INTEGRATION", "").lower() in {"1", "true", "yes"}


async def test_ingest_stream_worker_state_summary():
    if not _integration_enabled():
        pytest.skip("SPARKLE_INTEGRATION not enabled")

    async with AsyncSessionLocal() as db:
        user_id = uuid4()
        user = User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
        db.add(user)
        await db.commit()

        event_id = uuid4().hex

        # Create consumer group BEFORE publishing so xreadgroup with ">" can
        # see the event — Redis consumer groups only track messages arriving
        # after group creation.
        resolved_password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, password=resolved_password)
        stream = "stream:tracking_events"
        group = f"test_group_{uuid4().hex[:6]}"
        consumer = f"consumer_{uuid4().hex[:6]}"
        await redis_client.xgroup_create(stream, group, id="0", mkstream=True)

        event_bus = EventBus()
        service = EventService(db, event_bus)
        result = await service.ingest_events(
            user_id,
            [
                {
                    "event_id": event_id,
                    "event_type": "question_submit",
                    "schema_version": "event.v1",
                    "source": "test",
                    "ts_ms": int(_utcnow().timestamp() * 1000),
                    "entities": {"question_id": "q1"},
                    "payload": {"correct": False},
                }
            ],
        )
        assert result["accepted"] == 1

        # Duplicate ingest with different idempotency key should dedupe by event_id.
        result_dupe = await service.ingest_events(
            user_id,
            [
                {
                    "event_id": event_id,
                    "event_type": "question_submit",
                    "schema_version": "event.v1",
                    "source": "test",
                    "ts_ms": int(_utcnow().timestamp() * 1000),
                    "entities": {"question_id": "q1"},
                    "payload": {"correct": False},
                }
            ],
        )
        assert result_dupe["deduped"] == 1
        parsed = None
        message_id = None
        for _ in range(5):
            entries = await redis_client.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=1,
                block=2000,
            )
            if not entries:
                continue
            message_id, data = entries[0][1][0]
            candidate = {}
            for key, value in data.items():
                try:
                    candidate[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    candidate[key] = value
            if candidate.get("event_id") == event_id:
                parsed = candidate
                break
            await redis_client.xack(stream, group, message_id)

        assert parsed is not None, "Expected event not found in stream"

        worker = CognitiveStreamWorker(db, redis_client)
        await worker.handle_event(parsed)
        await redis_client.xack(stream, group, message_id)

        estimator = StateEstimatorService(db)
        snapshot = await estimator.get_latest_snapshot(user_id)
        assert snapshot is not None

        evidence_request = EvidenceResolveRequest(
            items=[EvidenceRef(type="user_state", id=str(snapshot.id))]
        )
        resolved = await events_api.resolve_evidence(evidence_request, db=db, current_user=user)
        assert resolved.resolved[0].status == "ok"

        # Cleanup
        await db.execute(delete(CognitiveFragment).where(CognitiveFragment.user_id == user_id))
        await db.execute(delete(UserStateSnapshot).where(UserStateSnapshot.user_id == user_id))
        await db.execute(delete(TrackingEvent).where(TrackingEvent.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()

        if event_bus.redis:
            await event_bus.redis.aclose()
        await redis_client.aclose()


async def test_delete_then_resolve_redacted():
    if not _integration_enabled():
        pytest.skip("SPARKLE_INTEGRATION not enabled")

    async with AsyncSessionLocal() as db:
        user_id = uuid4()
        user = User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
        db.add(user)
        await db.commit()

        event_id = uuid4().hex
        event = TrackingEvent(
            event_id=event_id,
            user_id=user_id,
            event_type="quiz_wrong",
            schema_version="event.v1",
            source="test",
            ts_ms=int(_utcnow().timestamp() * 1000),
            entities={"concept_id": "c1"},
            payload={"detail": "wrong"},
            received_at=_utcnow(),
        )
        db.add(event)
        await db.commit()

        # EventBus default constructor creates loop conflicts; soft_delete_event doesn't need it
        service = EventService(db)
        service.event_bus = None  # type: ignore[assignment]
        deleted = await service.soft_delete_event(user_id, event_id)
        assert deleted is True

        evidence_request = EvidenceResolveRequest(
            items=[EvidenceRef(type="event", id=event_id)]
        )
        resolved = await events_api.resolve_evidence(evidence_request, db=db, current_user=user)
        assert resolved.resolved[0].status == "redacted"

        await db.execute(delete(TrackingEvent).where(TrackingEvent.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
