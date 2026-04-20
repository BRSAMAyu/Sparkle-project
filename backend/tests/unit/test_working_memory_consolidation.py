from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.memory import EpisodicMemory
from app.services.working_memory_consolidation_service import WorkingMemoryConsolidationService
from app.working_memory.service import WorkingMemoryService


class _Clock:
    def __init__(self, start: datetime):
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@pytest.mark.asyncio
async def test_consolidation_promotes_repeated_entry_to_l1(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_CONSOLIDATION_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    monkeypatch.setattr(settings, "MEMORY_INFERRED_MIN_CONFIDENCE", 0.5, raising=False)
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    wm = WorkingMemoryService(now_fn=clock.now)
    user_id = uuid4()
    session_id = uuid4()

    for index in range(3):
        if index:
            clock.advance(timedelta(seconds=40))
        await wm.upsert_entry(
            user_id=str(user_id),
            session_id=str(session_id),
            text="这周要复习高数真题",
            semantic_key="commitment:math",
            salience_score=0.8,
            subject_type="self",
            confidence=0.86,
            evidence_token=f"turn-{index}",
            occurred_at=clock.now(),
            source_turn_id=f"turn-{index}",
        )

    service = WorkingMemoryConsolidationService(db_session, now_fn=clock.now)
    consolidated = await service.maybe_consolidate_recent_entries(user_id=user_id, session_id=session_id)

    assert len(consolidated) == 1
    result = await db_session.execute(
        select(EpisodicMemory).where(EpisodicMemory.user_id == user_id, EpisodicMemory.semantic_key == "commitment:math")
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_consolidation_accepts_strong_confirmation_but_not_generic_yes(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_CONSOLIDATION_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    monkeypatch.setattr(settings, "MEMORY_INFERRED_MIN_CONFIDENCE", 0.5, raising=False)
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    wm = WorkingMemoryService(now_fn=clock.now)
    user_id = uuid4()
    session_id = uuid4()

    entry = await wm.upsert_entry(
        user_id=str(user_id),
        session_id=str(session_id),
        text="下周三要交英语作业",
        semantic_key="commitment:english",
        salience_score=0.8,
        subject_type="commitment",
        confidence=0.92,
        evidence_token="turn-1",
        occurred_at=clock.now(),
        source_turn_id="turn-1",
        due_at=clock.now() + timedelta(days=2),
    )
    service = WorkingMemoryConsolidationService(db_session, now_fn=clock.now)

    assert service.is_explicit_confirmation("对") is False
    assert service.is_explicit_confirmation("帮我记住这个") is True

    await wm.mark_correct(user_id=str(user_id), session_id=str(session_id), entry_id=entry.entry_id)
    consolidated = await service.maybe_consolidate_recent_entries(
        user_id=user_id,
        session_id=session_id,
        explicit_confirmation=True,
    )

    assert len(consolidated) == 1


@pytest.mark.asyncio
async def test_consolidation_rejection_retracts_l1(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_CONSOLIDATION_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    monkeypatch.setattr(settings, "MEMORY_INFERRED_MIN_CONFIDENCE", 0.5, raising=False)
    clock = _Clock(datetime(2026, 4, 21, 10, 0, 0))
    wm = WorkingMemoryService(now_fn=clock.now)
    user_id = uuid4()
    session_id = uuid4()

    entry = await wm.upsert_entry(
        user_id=str(user_id),
        session_id=str(session_id),
        text="下周三要交英语作业",
        semantic_key="commitment:english",
        salience_score=0.8,
        subject_type="commitment",
        confidence=0.92,
        evidence_token="turn-1",
        occurred_at=clock.now(),
        source_turn_id="turn-1",
        due_at=clock.now() + timedelta(days=2),
    )
    service = WorkingMemoryConsolidationService(db_session, now_fn=clock.now)
    consolidated = await service.maybe_consolidate_recent_entries(
        user_id=user_id,
        session_id=session_id,
        explicit_confirmation=True,
    )
    assert consolidated

    rejected = await service.handle_possible_rejection(
        user_id=user_id,
        session_id=session_id,
        user_message="不是这样，别记这个",
    )

    assert rejected is not None
    updated = await wm.get_entry(user_id=str(user_id), session_id=str(session_id), entry_id=entry.entry_id)
    assert updated is not None
    assert updated.rejected is True
