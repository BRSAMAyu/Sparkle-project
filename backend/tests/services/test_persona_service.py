from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.compliance import PersonaSnapshot
from app.models.user import User
from app.services.persona_service import ProfileSnapshotService


@pytest.mark.asyncio
async def test_collect_tags_ignores_archived_patterns_in_query():
    db = AsyncMock()
    service = ProfileSnapshotService(db)
    user_id = uuid4()

    pattern_result = MagicMock()
    pattern_result.all.return_value = [("Perfectionism Loop",)]
    fragment_result = MagicMock()
    fragment_result.all.return_value = [(["deep_work", "reflection"],)]

    seen_queries: list[str] = []

    async def execute_side_effect(query):
        seen_queries.append(str(query).lower())
        return [pattern_result, fragment_result][len(seen_queries) - 1]

    db.execute.side_effect = execute_side_effect

    tags = await service._collect_tags(user_id)

    assert tags[:3] == ["Perfectionism Loop", "deep_work", "reflection"]
    assert "is_archived is false" in seen_queries[0]


def test_verify_integrity_rejects_tampered_snapshot():
    db = AsyncMock()
    service = ProfileSnapshotService(db)
    user_id = uuid4()

    snapshot = {
        "persona_version": "v3.1",
        "purpose": "chat_style",
        "tags": ["focused"],
        "capabilities": {"mastery_avg": 0.7},
        "last_update_event_id": "evt-1",
    }
    snapshot["audit_token"] = service._sign_snapshot_payload(user_id, snapshot)
    snapshot["tags"] = ["tampered"]

    assert service.verify_integrity(user_id, snapshot) == "invalid"


@pytest.mark.asyncio
async def test_get_snapshot_rebuilds_legacy_signed_record(db_session):
    user = User(username="persona_legacy", email="persona_legacy@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = ProfileSnapshotService(db_session)
    legacy_snapshot = {
        "persona_version": service.persona_version,
        "purpose": "chat_style",
        "tags": ["legacy"],
        "capabilities": {"mastery_avg": 0.2},
        "last_update_event_id": "evt-legacy",
    }
    legacy_snapshot["audit_token"] = service._sign_legacy_audit_token(user.id, legacy_snapshot["last_update_event_id"])

    db_session.add(
        PersonaSnapshot(
            user_id=user.id,
            persona_version=service.persona_version,
            audit_token=legacy_snapshot["audit_token"],
            source_event_id=legacy_snapshot["last_update_event_id"],
            snapshot_data=legacy_snapshot,
        )
    )
    await db_session.commit()

    rebuilt = await service.get_snapshot(user.id, "chat_style")

    assert rebuilt["purpose"] == "chat_style"
    assert service.verify_integrity(user.id, rebuilt) == "valid"
    assert rebuilt["audit_token"] != legacy_snapshot["audit_token"]
