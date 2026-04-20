from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.working_memory.service import WorkingMemoryService


class _Clock:
    def __init__(self, start: datetime):
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@pytest.mark.asyncio
async def test_working_memory_upsert_merges_by_semantic_key() -> None:
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    service = WorkingMemoryService(now_fn=clock.now)

    first = await service.upsert_entry(
        user_id="user-1",
        session_id="session-1",
        text="周末要复习高数",
        semantic_key="commitment:math",
        salience_score=0.62,
        subject_type="commitment",
        confidence=0.81,
        evidence_token="turn-1",
        occurred_at=clock.now(),
        source_turn_id="turn-1",
    )
    clock.advance(timedelta(minutes=2))
    second = await service.upsert_entry(
        user_id="user-1",
        session_id="session-1",
        text="这周末要复习高数真题",
        semantic_key="commitment:math",
        salience_score=0.71,
        subject_type="commitment",
        confidence=0.85,
        evidence_token="turn-2",
        occurred_at=clock.now(),
        source_turn_id="turn-2",
    )

    assert first.entry_id == second.entry_id
    entries = await service.list_entries(user_id="user-1", session_id="session-1", limit=None)
    assert len(entries) == 1
    assert entries[0].mention_count == 2
    assert entries[0].source_turn_ids == ("turn-1", "turn-2")


@pytest.mark.asyncio
async def test_working_memory_isolated_by_session() -> None:
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    service = WorkingMemoryService(now_fn=clock.now)

    await service.upsert_entry(
        user_id="user-1",
        session_id="session-a",
        text="A",
        semantic_key="k1",
        salience_score=0.5,
        subject_type="self",
        confidence=0.7,
        evidence_token="turn-a",
        occurred_at=clock.now(),
        source_turn_id="turn-a",
    )
    await service.upsert_entry(
        user_id="user-1",
        session_id="session-b",
        text="B",
        semantic_key="k1",
        salience_score=0.6,
        subject_type="self",
        confidence=0.7,
        evidence_token="turn-b",
        occurred_at=clock.now(),
        source_turn_id="turn-b",
    )

    session_a = await service.list_entries(user_id="user-1", session_id="session-a", limit=None)
    session_b = await service.list_entries(user_id="user-1", session_id="session-b", limit=None)
    assert len(session_a) == 1
    assert len(session_b) == 1
    assert session_a[0].text == "A"
    assert session_b[0].text == "B"


@pytest.mark.asyncio
async def test_working_memory_evicts_low_salience_lru_entries() -> None:
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    service = WorkingMemoryService(now_fn=clock.now)

    for index in range(45):
        clock.advance(timedelta(seconds=1))
        await service.upsert_entry(
            user_id="user-1",
            session_id="session-1",
            text=f"entry-{index}",
            semantic_key=f"k-{index}",
            salience_score=0.1 + (index / 100),
            subject_type="self",
            confidence=0.6,
            evidence_token=f"turn-{index}",
            occurred_at=clock.now(),
            source_turn_id=f"turn-{index}",
        )

    entries = await service.list_entries(user_id="user-1", session_id="session-1", limit=None)
    assert len(entries) == WorkingMemoryService.MAX_ENTRIES_PER_SESSION
    assert all(item.text != "entry-0" for item in entries)
    assert any(item.text == "entry-44" for item in entries)


@pytest.mark.asyncio
async def test_working_memory_close_session_applies_short_ttl() -> None:
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    service = WorkingMemoryService(now_fn=clock.now)

    entry = await service.upsert_entry(
        user_id="user-1",
        session_id="session-1",
        text="need follow-up",
        semantic_key="k-1",
        salience_score=0.8,
        subject_type="commitment",
        confidence=0.9,
        evidence_token="turn-1",
        occurred_at=clock.now(),
        source_turn_id="turn-1",
    )
    await service.close_session(user_id="user-1", session_id="session-1")

    assert await service.get_entry(user_id="user-1", session_id="session-1", entry_id=entry.entry_id) is not None
    clock.advance(timedelta(seconds=WorkingMemoryService.SESSION_END_GRACE_SECONDS + 1))
    assert await service.get_entry(user_id="user-1", session_id="session-1", entry_id=entry.entry_id) is None


@pytest.mark.asyncio
async def test_working_memory_orphan_cleanup_deletes_dead_sessions() -> None:
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    service = WorkingMemoryService(now_fn=clock.now)

    await service.upsert_entry(
        user_id="user-1",
        session_id="live-session",
        text="keep me",
        semantic_key="live",
        salience_score=0.6,
        subject_type="self",
        confidence=0.7,
        evidence_token="turn-live",
        occurred_at=clock.now(),
        source_turn_id="turn-live",
    )
    await service.upsert_entry(
        user_id="user-1",
        session_id="orphan-session",
        text="drop me",
        semantic_key="orphan",
        salience_score=0.4,
        subject_type="self",
        confidence=0.7,
        evidence_token="turn-orphan",
        occurred_at=clock.now(),
        source_turn_id="turn-orphan",
    )

    deleted = await service.cleanup_orphaned_namespaces(active_session_ids={"live-session"})

    assert deleted >= 2
    assert len(await service.list_entries(user_id="user-1", session_id="live-session", limit=None)) == 1
    assert len(await service.list_entries(user_id="user-1", session_id="orphan-session", limit=None)) == 0
