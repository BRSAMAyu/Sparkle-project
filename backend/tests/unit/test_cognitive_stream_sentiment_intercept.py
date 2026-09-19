"""V3-FIX-11 T3 red/green: telemetry sentiment must not reach the aggregator's
emotional_block trigger set through plaintext cognitive_fragments.sentiment.

D-01 R2 evidence (F3): ``cognitive_stream_worker`` intercepts only
{anxious, depressed, burnout} into the encrypted sensitive channel, while the
state aggregator's ``emotional_block`` trigger set is {anxious, frustrated,
overwhelmed} — ``frustrated``/``overwhelmed`` from a telemetry payload passed
through as plaintext sentiment and dominated the aggregator's emotion_hint
(second-hop telemetry -> business truth).
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.telemetry_boundary import (
    EMOTIONAL_BLOCK_SENTIMENTS,
    TELEMETRY_SENSITIVE_SENTIMENTS,
)
from app.services.analytics.cognitive_stream_worker import CognitiveStreamWorker

_UUID = uuid4()


class _FragmentCollector:
    """Stand-in session that records db.add() calls."""

    def __init__(self, worker):
        self.worker = worker

    def add(self, fragment):
        self.worker.db_fragments.append(fragment)


def _worker_with_collector() -> tuple[CognitiveStreamWorker, list]:
    worker = CognitiveStreamWorker.__new__(CognitiveStreamWorker)
    worker.db_fragments = []
    worker.db = _FragmentCollector(worker)
    worker.redis = None
    worker.crypto_erase = AsyncMock()
    worker.crypto_erase.encrypt_payload = AsyncMock(return_value=("enc-payload", "key-1"))
    return worker, worker.db_fragments


async def _create(worker: CognitiveStreamWorker, sentiment: str | None):
    await worker._create_fragment(
        user_id=_UUID,
        event={"event_id": f"evt-{sentiment}", "event_name": "note", "task_id": None},
        payload={"sentiment": sentiment, "tags": [], "severity": 1},
        allow_sensitive=True,
    )


async def test_frustrated_sentiment_is_intercepted():
    """telemetry payload sentiment=frustrated must NOT land in plaintext
    sentiment (it is an emotional_block trigger in the aggregator)."""
    worker, fragments = _worker_with_collector()
    await _create(worker, "frustrated")

    fragment = fragments[0]
    assert fragment.sentiment is None, (
        "frustrated passed through as plaintext sentiment — the aggregator's "
        "emotional_block trigger set is reachable from client telemetry (T3)"
    )
    # intercepted into the encrypted sensitive channel instead
    assert fragment.sensitive_tags_encrypted == "enc-payload"


async def test_overwhelmed_sentiment_is_intercepted():
    worker, fragments = _worker_with_collector()
    await _create(worker, "overwhelmed")
    assert fragments[0].sentiment is None


async def test_anxious_sentiment_stays_intercepted():
    """Regression: the historical trio must remain intercepted."""
    worker, fragments = _worker_with_collector()
    await _create(worker, "anxious")
    assert fragments[0].sentiment is None


async def test_neutral_sentiment_flows_through():
    worker, fragments = _worker_with_collector()
    await _create(worker, "neutral")
    assert fragments[0].sentiment == "neutral"


def test_emotional_block_triggers_are_all_intercepted():
    """Single-source-of-truth invariant: every sentiment that can trip
    emotional_block in the aggregator must be in the telemetry intercept set
    (prevents the two sets from drifting apart again)."""
    assert EMOTIONAL_BLOCK_SENTIMENTS <= TELEMETRY_SENSITIVE_SENTIMENTS
    assert CognitiveStreamWorker.SENSITIVE_SENTIMENTS == TELEMETRY_SENSITIVE_SENTIMENTS
