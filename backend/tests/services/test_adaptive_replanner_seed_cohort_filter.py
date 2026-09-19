"""V3-FIX-11 T2 red/green: the adaptive replanner's high-confidence
BehaviorPattern pool must exclude guest/seed cohort accounts.

D-01 R2 evidence (F5): ``adaptive_replanner.CognitivePatternTrigger`` reads
BehaviorPattern with confidence >= 0.7 into plan adjustments; the dev DB holds
166 seed-injected "计划谬误" patterns at 0.84 (all owned by
registration_source='guest' users, guest_seed_service.py:2215) sitting inside
that gate. Same registration_source口径 as the V3-FIX-01 leaderboard fix.

Statement-capture pattern (no DB needed): the pattern query is compiled and
inspected, because cohort exclusion is a SQL predicate.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.orchestration.adaptive_replanner import CognitivePatternTrigger

EXCLUDED_SOURCES = {"guest", "seed"}


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _StatementCaptureDB:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _ScalarResult([])


def _make_trigger(db) -> CognitivePatternTrigger:
    trigger = CognitivePatternTrigger(db, redis=None)
    trigger.preference_service.get_preferences = AsyncMock(return_value=SimpleNamespace(explicit={}))
    return trigger


def _bound_scalars(compiled) -> set:
    values: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            values.update(value)
        else:
            values.add(value)
    return values


async def test_pattern_pool_query_excludes_guest_and_seed_cohorts():
    """The replanner's pattern query must filter registration_source."""
    db = _StatementCaptureDB()
    trigger = _make_trigger(db)

    await trigger.build_adjustments(user_id=uuid4(), existing_constraints={})

    assert len(db.statements) >= 1
    pattern_sql = str(db.statements[0].compile()).upper()

    assert "REGISTRATION_SOURCE" in pattern_sql, (
        "adaptive replanner pattern pool has no registration_source predicate — "
        "166 seed-injected 计划谬误 patterns at confidence 0.84 sit inside the "
        "0.7 decision gate (D-01 R2 F5 / V3-FIX-11 T2)"
    )
    compiled = db.statements[0].compile()
    assert (
        _bound_scalars(compiled) >= EXCLUDED_SOURCES
    ), f"cohort exclusion bind params missing guest/seed: {_bound_scalars(compiled)}"


async def test_existing_pattern_filters_are_preserved():
    """Cohort filter is additive: confidence gate + archived filter stay."""
    db = _StatementCaptureDB()
    trigger = _make_trigger(db)

    await trigger.build_adjustments(user_id=uuid4(), existing_constraints={})

    pattern_sql = str(db.statements[0].compile()).upper()
    assert "CONFIDENCE_SCORE" in pattern_sql
    assert "IS_ARCHIVED" in pattern_sql
