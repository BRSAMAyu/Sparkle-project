"""Regression tests for MemoryInferredWriteLaneService degraded queue (M1: unbounded growth)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.services.memory_inferred_write_lane import (
    InferredEpisodicCandidate,
    MemoryInferredWriteLaneService,
)

MAXLEN = 256


def _candidate() -> InferredEpisodicCandidate:
    return InferredEpisodicCandidate(
        candidate_text="今晚复习概率论",
        subject_type="commitment",
        confidence=0.9,
        evidence_token=f"turn-{uuid4().hex}",
        decay_policy="7d",
        source_lane="inferred_extraction",
        semantic_key="commitment:test",
        evidence_refs=[{"type": "chat_turn", "id": "turn"}],
        occurred_at=datetime.now(UTC).replace(tzinfo=None),
        due_at=None,
        mentioned_entity_hash=None,
        mentioned_entity_owner_user_id=None,
    )


def test_degraded_queue_is_bounded_with_drop_counter():
    """M1: _degraded_queue 无消费者，必须有 maxlen 防止进程内存无界增长。"""
    queue = MemoryInferredWriteLaneService._degraded_queue
    queue.clear()
    MemoryInferredWriteLaneService._degraded_queue_dropped_total = 0

    try:
        for _ in range(MAXLEN + 50):
            MemoryInferredWriteLaneService._enqueue_degraded_candidate(
                user_id=uuid4(),
                session_id=uuid4(),
                candidate=_candidate(),
            )

        assert len(queue) <= MAXLEN, f"degraded queue grew to {len(queue)} (> {MAXLEN})"
        assert (
            MemoryInferredWriteLaneService._degraded_queue_dropped_total == 50
        ), "drops beyond maxlen must be counted"
    finally:
        queue.clear()
        MemoryInferredWriteLaneService._degraded_queue_dropped_total = 0
