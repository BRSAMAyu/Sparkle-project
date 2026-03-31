from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_write_service import ProfileWriteService


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, dict[str, str]] = {}
        self._ttl: dict[str, int] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self._kv.setdefault(key, {})[field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._kv.get(key, {}))

    async def hget(self, key: str, field: str) -> str | None:
        return self._kv.get(key, {}).get(field)

    async def hdel(self, key: str, field: str) -> None:
        if key in self._kv:
            self._kv[key].pop(field, None)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._kv.pop(key, None)

    async def expire(self, key: str, ttl: int) -> None:
        self._ttl[key] = ttl


@pytest.mark.asyncio
async def test_override_inferred_preference_moves_value_to_explicit_and_preserves_backup(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    redis = _FakeRedis()
    pref_service = PreferenceService(db_session, redis=redis)
    await pref_service.update_inferred(user_id, {"community_engagement_level": "moderate"})

    service = ProfileWriteService(db_session, redis=redis)
    await service.override_inferred_preference(
        user_id=user_id,
        pref_key="community_engagement_level",
        pref_value={"value": "high"},
        evidence_refs=[{"type": "user_state", "id": "test", "schema_version": "test.v1"}],
        source="test_override",
    )

    prefs = await pref_service.get_preferences(user_id)
    backups = await service.list_inferred_backups(user_id)

    assert prefs.explicit["community_engagement_level"] == "high"
    assert "community_engagement_level" not in (prefs.inferred or {})
    assert backups["community_engagement_level"]["value"] == "moderate"

    await service.reset_override_preference(user_id=user_id, pref_key="community_engagement_level")
    restored = await pref_service.get_preferences(user_id)
    restored_backups = await service.list_inferred_backups(user_id)

    assert "community_engagement_level" not in (restored.explicit or {})
    assert restored.inferred["community_engagement_level"] == "moderate"
    assert "community_engagement_level" not in restored_backups
    assert redis._ttl[service._override_backup_key(user_id)] == 30 * 24 * 3600


@pytest.mark.asyncio
async def test_update_inferred_preference_respects_non_default_explicit_override(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    pref_service = PreferenceService(db_session)
    await pref_service.update_explicit(user_id, {"depth_preference": 0.3})

    service = ProfileWriteService(db_session)
    await service.update_inferred_preference(
        user_id=user_id,
        updates={
            "depth_preference": 0.9,
            "ai_delegate_preference": 0.65,
        },
        source="unit_test",
    )

    prefs = await pref_service.get_preferences(user_id)

    assert prefs.explicit["depth_preference"] == 0.3
    assert "depth_preference" not in (prefs.inferred or {})
    assert prefs.inferred["ai_delegate_preference"] == 0.65
