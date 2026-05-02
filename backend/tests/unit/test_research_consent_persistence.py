from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.research_consent import ResearchConsent
from app.signals.research_mode import ConsentTracker


class _ScalarResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return [] if self._value is None else [self._value]


class _FakeSession:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.added = []
        self.flushed = False

    async def execute(self, _statement):
        return _ScalarResult(self.rows.pop(0) if self.rows else None)

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_consent_tracker_grant_persists_to_db_session():
    user_id = uuid4()
    db = _FakeSession([None])
    tracker = ConsentTracker(db)

    record = await tracker.grant_consent_db(
        user_id=str(user_id),
        consent_type="research_analytics",
        source="settings_page",
        version="2.0",
    )

    assert record.granted is True
    assert record.user_id == str(user_id)
    assert record.version == "2.0"
    assert isinstance(db.added[0], ResearchConsent)
    assert db.flushed is True


@pytest.mark.asyncio
async def test_consent_tracker_revoke_marks_existing_record_false():
    user_id = uuid4()
    row = ResearchConsent(
        user_id=user_id,
        consent_type="anonymized_export",
        granted=True,
        source="api",
        version="1.0",
    )
    db = _FakeSession([row])
    tracker = ConsentTracker(db)

    record = await tracker.revoke_consent_db(
        user_id=str(user_id),
        consent_type="anonymized_export",
        source="settings_page",
    )

    assert record is not None
    assert record.granted is False
    assert row.revoked_at is not None
    assert db.flushed is True


def test_sync_consent_tracker_still_supports_existing_unit_contract():
    tracker = ConsentTracker()
    for consent_type in ConsentTracker.REQUIRED_CONSENTS:
        tracker.grant_consent(user_id="u1", consent_type=consent_type)

    assert tracker.can_include_in_research("u1") is True
    tracker.revoke_consent(user_id="u1", consent_type="cohort_comparison")
    assert tracker.can_include_in_research("u1") is False
