"""Regression tests for WorkingMemoryConsolidationService rejection handling (M2)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from app.services import working_memory_consolidation_service as mod
from app.services.working_memory_consolidation_service import WorkingMemoryConsolidationService
from app.working_memory.schema import WorkingMemoryEntry

NOW = datetime(2026, 4, 21, 10, 0, 0)
L1_STALE_ID = "00000000-0000-0000-0000-000000000001"
L1_RECENT_ID = "00000000-0000-0000-0000-000000000002"


def _entry(
    *,
    entry_id: str,
    salience: float,
    last_seen_at: datetime,
    consolidated_to_l1_id: str | None = None,
    rejected: bool = False,
) -> WorkingMemoryEntry:
    return WorkingMemoryEntry(
        entry_id=entry_id,
        user_id="user-1",
        session_id="sess-1",
        text="下周三要交英语作业",
        semantic_key="commitment:english",
        salience_score=salience,
        mention_count=3,
        first_seen_at=last_seen_at - timedelta(minutes=5),
        last_seen_at=last_seen_at,
        source_turn_ids=("turn-1",),
        subject_type="commitment",
        confidence=0.92,
        evidence_token="turn-1",
        occurred_at=NOW,
        due_at=NOW + timedelta(days=2),
        consolidated_to_l1_id=consolidated_to_l1_id,
        rejected=rejected,
    )


class _StubWorkingMemory:
    def __init__(self, entries: list[WorkingMemoryEntry]) -> None:
        self.entries = entries
        self.rejected_ids: list[str] = []

    async def list_entries(self, **kwargs) -> list[WorkingMemoryEntry]:
        return self.entries

    async def mark_rejected(self, *, user_id: str, session_id: str, entry_id: str) -> WorkingMemoryEntry:
        self.rejected_ids.append(entry_id)
        return next(entry for entry in self.entries if entry.entry_id == entry_id)


class _StubMemoryService:
    def __init__(self) -> None:
        self.retracted: list[tuple[str, str, str]] = []

    async def retract_memory(self, *, kind: str, memory_id, user_id, reason: str):
        self.retracted.append((kind, str(memory_id), reason))
        return None


def _make_service(entries: list[WorkingMemoryEntry]):
    service = WorkingMemoryConsolidationService(None, MagicMock(), now_fn=lambda: NOW)
    stub_wm = _StubWorkingMemory(entries)
    stub_memory = _StubMemoryService()
    service.working_memory = stub_wm
    mod_memory_factory = lambda db: stub_memory  # noqa: E731
    return service, stub_wm, stub_memory, mod_memory_factory


def test_plain_correction_is_not_rejection():
    """M2: 普通纠正（无记忆语境）不得触发记忆撤回判定。"""
    assert not WorkingMemoryConsolidationService.is_explicit_rejection("不对，这道题应该用换元法")
    assert not WorkingMemoryConsolidationService.is_explicit_rejection("不是这样，题目给的条件是 3")
    # 对照：记忆显式短语与宽泛短语+记忆语境仍可命中
    assert WorkingMemoryConsolidationService.is_explicit_rejection("别记这个")
    assert WorkingMemoryConsolidationService.is_explicit_rejection("不对，你记错了")
    assert WorkingMemoryConsolidationService.is_explicit_rejection("不对，不是这个记忆")


def test_rejection_targets_most_recent_consolidated_entry(monkeypatch):
    """M2: 撤回目标须取时间邻近的最近固化条目，而非 salience 最高的旧条目。"""
    stale = _entry(entry_id="e-stale", salience=0.99, last_seen_at=NOW - timedelta(hours=2), consolidated_to_l1_id=L1_STALE_ID)
    recent = _entry(entry_id="e-recent", salience=0.40, last_seen_at=NOW - timedelta(minutes=1), consolidated_to_l1_id=L1_RECENT_ID)
    service, stub_wm, stub_memory, memory_factory = _make_service([stale, recent])
    monkeypatch.setattr(mod, "MemoryService", memory_factory)

    import asyncio

    rejected = asyncio.run(
        service.handle_possible_rejection(
            user_id=uuid4(),
            session_id=uuid4(),
            user_message="不对，你记错了",
        )
    )

    assert rejected is not None
    assert rejected.entry_id == "e-recent"
    assert stub_memory.retracted and stub_memory.retracted[0][1] == L1_RECENT_ID
    assert stub_wm.rejected_ids == ["e-recent"]


def test_stale_consolidated_entry_is_not_revived_for_retraction(monkeypatch):
    """M2: 超出时间邻近窗口的固化条目不得被撤回。"""
    stale = _entry(entry_id="e-stale", salience=0.99, last_seen_at=NOW - timedelta(hours=2), consolidated_to_l1_id=L1_STALE_ID)
    service, stub_wm, stub_memory, memory_factory = _make_service([stale])
    monkeypatch.setattr(mod, "MemoryService", memory_factory)

    import asyncio

    rejected = asyncio.run(
        service.handle_possible_rejection(
            user_id=uuid4(),
            session_id=uuid4(),
            user_message="不对，你记错了",
        )
    )

    assert rejected is None
    assert stub_memory.retracted == []
    assert stub_wm.rejected_ids == []
