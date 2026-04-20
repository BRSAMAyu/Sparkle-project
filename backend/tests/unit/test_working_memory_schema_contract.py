from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from app.working_memory.schema import WorkingMemoryEntry


def test_working_memory_entry_is_frozen() -> None:
    entry = WorkingMemoryEntry(
        entry_id="entry-1",
        user_id="user-1",
        session_id="session-1",
        text="准备周末复习高数",
        semantic_key="commitment:math",
        salience_score=0.7,
        mention_count=1,
        first_seen_at=datetime(2026, 4, 21, 10, 0, 0),
        last_seen_at=datetime(2026, 4, 21, 10, 0, 0),
        source_turn_ids=("turn-1",),
        subject_type="commitment",
        confidence=0.84,
        evidence_token="turn-1",
        occurred_at=datetime(2026, 4, 21, 10, 0, 0),
    )

    with pytest.raises(FrozenInstanceError):
        entry.mention_count = 2
