"""V3-FIX-35 regression: preference supersede counter-kill chain.

M-09 evaluation exposed a three-ring failure (20 red cases, REGISTERED_BUG_
CASE_IDS in ``tests/memory_eval/test_memory_eval_gate.py``):

1. ``MemoryService.upsert_preference`` bumps the SUPERSEDED row's
   ``updated_at`` to ``utcnow()`` at supersede time — strictly newer than the
   new chain head created microseconds earlier.
2. ``ContextPackBuilder.build`` hands ``MemoryConflictResolver.resolve_
   preferences`` the full unfiltered version history (legitimate — the
   resolver is the one place that understands the chain).
3. ``_pick_preference_winner`` ranks by ``(evidence_score, updated_at,
   confidence)`` ignoring ``replaced_by_id`` — so the superseded row
   outranks its own head by timestamp AND, independently, whenever the old
   row accumulated more evidence refs.

Net effect (the "反杀"): every same-evidence-channel preference update
returned the OLD value in ``pack.preferences`` — the user's correction never
reached the prompt face.

These tests pin the corrected invariants:

- chain head wins with the resolver ON and OFF (R2's A/B probe);
- a superseded row with MORE evidence does not out-rank the head;
- the head's ``updated_at`` is never older than a row it superseded
  (precise bump semantics — M-07 cache-invalidation intent preserved);
- resolver conflict notes attribute suppression to the supersede chain;
- a fully-superseded (no head) group still resolves to a deterministic
  winner (legacy-data fallback, never crashes).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.memory_conflict_resolver import MemoryConflictResolver, _pick_preference_winner
from app.services.memory_service import MemoryService

PREF_KEY = "preferred_expansion_depth"
OLD_VALUE = "练习题只要基础难度"
NEW_VALUE = "现在要竞赛难度的题，基础的没挑战"


def _ref(n: int) -> list[dict[str, str]]:
    return [{"type": "user_state", "id": f"evt_{n}", "schema_version": "fix35.v1"}]


async def _seed_user_with_chain(db_session) -> UUID:
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    service = MemoryService(db_session)
    old = await service.upsert_preference(
        user_id=user_id,
        pref_key=PREF_KEY,
        pref_value={"value": OLD_VALUE},
        evidence_refs=_ref(1),
        confidence=0.92,
        source_type="user_state",
    )
    new = await service.upsert_preference(
        user_id=user_id,
        pref_key=PREF_KEY,
        pref_value={"value": NEW_VALUE},
        evidence_refs=_ref(2),
        confidence=0.92,
        source_type="user_state",
    )
    assert old is not None and new is not None
    return user_id


async def _build_pack(db_session, user_id: UUID, *, conflict_resolution: bool):
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 600, "goals": 300, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    return await builder.build(user_id, intent="chat", query_text="给我出几道统计学习的练习题")


# ---------------------------------------------------------------------------
# R2 A/B minimal probe: resolver ON vs OFF must agree — chain head wins.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_ab_supersede_chain_head_wins(db_session, monkeypatch):
    """R2's A/B probe, isolated to the resolver ring (selfcheck off so the
    second failure mode — relevance downgrade — cannot mask the resolver
    result). The composed end-to-end face is pinned separately below."""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    user_id = await _seed_user_with_chain(db_session)

    for resolver_on in (True, False):
        monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", resolver_on, raising=False)
        pack = await _build_pack(db_session, user_id, conflict_resolution=resolver_on)
        surfaced = pack.preferences.get(PREF_KEY)
        assert surfaced is not None, f"resolver_on={resolver_on}: preference dropped from pack"
        assert surfaced == {"value": NEW_VALUE}, (
            f"resolver_on={resolver_on}: superseded value resurrected: {surfaced!r}"
        )


@pytest.mark.asyncio
async def test_superseded_row_with_more_evidence_does_not_revive(db_session, monkeypatch):
    """Old row carries 3 evidence refs vs the head's 1 — evidence_score must
    not out-rank chain position (this is the pre-existing 'direct beats soft'
    counter-kill, independent of the updated_at bump)."""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user_id,
        pref_key="feedback_tone",
        pref_value={"value": "direct"},
        evidence_refs=_ref(1) + _ref(2) + _ref(3),
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="feedback_tone",
        pref_value={"value": "soft"},
        evidence_refs=_ref(4),
    )
    pack = await _build_pack(db_session, user_id, conflict_resolution=True)
    assert pack.preferences["feedback_tone"] == {"value": "soft"}


@pytest.mark.asyncio
async def test_head_updated_at_never_older_than_superseded_row(db_session):
    """Precise bump semantics: the supersede transition may touch the old
    row's updated_at (M-07 invalidation intent), but must never leave the
    chain head looking older than the row it superseded."""
    user_id = await _seed_user_with_chain(db_session)
    service = MemoryService(db_session)
    history = await service.list_preference_history(user_id)
    rows = [r for r in history if r.pref_key == PREF_KEY]
    head = next(r for r in rows if r.replaced_by_id is None)
    superseded = [r for r in rows if r.replaced_by_id is not None]
    assert superseded, "chain did not supersede the old row"
    for old in superseded:
        assert head.updated_at is not None and old.updated_at is not None
        assert head.updated_at >= old.updated_at, (
            f"head updated_at {head.updated_at} older than superseded {old.updated_at}"
        )


# ---------------------------------------------------------------------------
# Resolver-level unit invariants (pure, no DB).
# ---------------------------------------------------------------------------


def _record(
    record_id: str,
    *,
    replaced_by: str | None = None,
    evidence_score: float = 0.5,
    updated_at: datetime | None = None,
    confidence: float = 0.9,
    value: str = "v",
) -> MemoryPreference:
    record = MemoryPreference(
        user_id=UUID(int=1),
        pref_key=PREF_KEY,
        pref_value={"value": value},
        version=1,
        replaced_by_id=UUID(replaced_by) if replaced_by else None,
        confidence=confidence,
        evidence_score=evidence_score,
    )
    record.id = UUID(record_id)
    record.updated_at = updated_at or datetime(2026, 9, 1, 12, 0, 0)
    return record


HEAD = "00000000-0000-0000-0000-000000000001"
MID = "00000000-0000-0000-0000-000000000002"
OLD = "00000000-0000-0000-0000-000000000003"


def test_pick_winner_supersede_chain_head_beats_ranking():
    """Superseded row wins every legacy ranking axis (newer timestamp, higher
    evidence, higher confidence) — chain position must still own the pick."""
    head = _record(HEAD, evidence_score=0.5, updated_at=datetime(2026, 9, 1), value="new")
    zombie = _record(
        OLD,
        replaced_by=HEAD,
        evidence_score=0.9,
        updated_at=datetime(2026, 9, 2),
        confidence=0.99,
        value="old",
    )
    winner, reason = _pick_preference_winner([zombie, head])
    assert winner is head
    assert reason == "supersede_chain_head"


def test_pick_winner_multi_version_chain_resolves_to_final_head():
    head = _record(HEAD, value="v3")
    mid = _record(MID, replaced_by=HEAD, value="v2")
    old = _record(OLD, replaced_by=MID, value="v1")
    winner, reason = _pick_preference_winner([old, mid, head])
    assert winner is head
    assert reason == "supersede_chain_head"


def test_pick_winner_single_record_and_headless_fallback():
    solo = _record(HEAD)
    winner, reason = _pick_preference_winner([solo])
    assert winner is solo
    assert reason == "single"

    # Legacy anomaly: every row claims to be superseded (dangling chain).
    # Resolution must stay deterministic — fall back to the ranking axes.
    a = _record(HEAD, replaced_by=MID, evidence_score=0.9, value="a")
    b = _record(MID, replaced_by=HEAD, evidence_score=0.4, value="b")
    winner, reason = _pick_preference_winner([a, b])
    assert winner is a
    assert reason == "evidence_score"


def test_resolver_conflict_note_attributes_supersede_chain():
    head = _record(HEAD, value="new")
    zombie = _record(OLD, replaced_by=HEAD, evidence_score=0.99, updated_at=datetime(2026, 9, 2))
    resolved, winners, conflicts = MemoryConflictResolver().resolve_preferences(
        {PREF_KEY: {"value": "new"}},
        [zombie, head],
    )
    assert resolved[PREF_KEY] == {"value": "new"}
    assert [w.id for w in winners] == [head.id]
    assert conflicts and conflicts[0]["reason"] == "supersede_chain_head"
    assert conflicts[0]["suppressed"] == [str(zombie.id)]


def test_resolver_distinct_keys_without_chain_keep_ranking():
    """Keys that never had a supersede (single-row or parallel heads) keep the
    legacy ranking semantics — the fix is scoped to chain resolution."""
    older = _record(OLD, evidence_score=0.6, updated_at=datetime(2026, 9, 1))
    newer_head = _record(
        HEAD,
        evidence_score=0.6,
        updated_at=datetime(2026, 9, 2),
        confidence=0.9,
    )
    winner, reason = _pick_preference_winner([older, newer_head])
    assert winner is newer_head
    assert reason == "updated_at"


# ---------------------------------------------------------------------------
# End-to-end: the pack face must carry the corrected value through the full
# chain (resolver -> rank -> selfcheck-survival on a topically-matching query).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pack_face_carries_chain_head_after_multiple_supersedes(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    service = MemoryService(db_session)
    for value in ("基础难度", "进阶难度", "竞赛难度"):
        await service.upsert_preference(
            user_id=user_id,
            pref_key=PREF_KEY,
            pref_value={"value": value},
            evidence_refs=_ref(value.__len__()),
            confidence=0.92,
            source_type="user_state",
        )
    pack = await _build_pack(db_session, user_id, conflict_resolution=True)
    assert pack.preferences.get(PREF_KEY) == {"value": "竞赛难度"}


def _timedelta_later(base: datetime, seconds: float) -> datetime:
    return base + timedelta(seconds=seconds)
